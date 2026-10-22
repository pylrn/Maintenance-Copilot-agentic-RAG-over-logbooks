"""Explicit and bounded hypothesis exploration branch."""

import hashlib
import json
from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import UUID, uuid4

from maintenance.contracts import (
    AnswerEnvelope,
    HypothesisEnvelope,
)


class HypothesisService:
    def __init__(self, pool: Any):
        self.pool = pool

    async def authorize_hypothesis_request(
        self,
        session_id: UUID,
        owner_id: UUID,
        parent_answer_id: UUID,
        expected_revision: int,
    ) -> UUID:
        """Verifies session ownership, parent answer, and state revision, creating a one-time request authorization."""
        async with self.pool.acquire() as conn:
            async with conn.transaction():
                # Check session & revision
                s = await conn.fetchrow(
                    "SELECT state_revision FROM sessions WHERE session_id = $1 AND owner_id = $2",
                    session_id,
                    owner_id,
                )
                if not s:
                    raise LookupError("session_not_found")
                if s["state_revision"] != expected_revision:
                    raise ValueError(f"revision_conflict: expected {expected_revision} got {s['state_revision']}")

                # Check parent answer
                ans = await conn.fetchrow(
                    "SELECT answer_id, envelope FROM answers WHERE answer_id = $1",
                    parent_answer_id,
                )
                if not ans:
                    raise LookupError("parent_answer_not_found")

                parent_json = ans["envelope"]
                if isinstance(parent_json, dict):
                    parent_json = json.dumps(parent_json)
                parent_hash = hashlib.sha256(parent_json.encode("utf-8")).hexdigest()

                req_id = uuid4()
                expires_at = datetime.now(timezone.utc) + timedelta(minutes=5)
                await conn.execute(
                    """
                    INSERT INTO hypothesis_requests (
                        request_id, owner_id, session_id, parent_answer_id, parent_hash,
                        state_revision, requested_at, expires_at
                    ) VALUES ($1, $2, $3, $4, $5, $6, now(), $7)
                    """,
                    req_id,
                    owner_id,
                    session_id,
                    parent_answer_id,
                    parent_hash,
                    expected_revision,
                    expires_at,
                )
                return req_id

    @classmethod
    async def generate_hypothesis_with_lm(
        cls,
        provider: Any,
        parent_answer: AnswerEnvelope,
        query_raw: str,
        run_id: UUID,
        state_revision: int,
    ) -> HypothesisEnvelope:
        """Generates grounded troubleshooting hypotheses citing official FAA technical manuals via LM."""
        parent_claims = getattr(parent_answer, "claims", []) or []
        parent_claims_text = "\n".join(f"- {c.text}" for c in parent_claims[:6])
        if not parent_claims_text:
            parent_claims_text = parent_answer.headline

        if provider and getattr(provider, "is_configured", False):
            prompt = (
                f"Complaint / Fault Context: {query_raw}\n"
                f"Historical Log Context:\n{parent_claims_text}\n\n"
                "You are Maintenance Atlas generating an UNVERIFIED HYPOTHESIS troubleshooting analysis.\n"
                "Ground your analysis in official aviation troubleshooting references and manuals:\n"
                "- FAA Aviation Maintenance Technician Handbook - Powerplant (FAA-H-8083-32B)\n"
                "- FAA Advisory Circular AC 43.13-1B (Acceptable Methods, Techniques, and Practices - Aircraft Inspection and Repair)\n"
                "- FAA AMT Airframe Handbook (FAA-H-8083-31B / AC 65-15A)\n"
                "- FAA AMT General Handbook (FAA-H-8083-30B)\n"
                "- FAA Service Difficulty Reporting System (SDRS)\n\n"
                "Respond with a JSON object containing:\n"
                "{\n"
                '  "summary": "1-2 sentence executive troubleshooting overview citing relevant FAA technical manual principles.",\n'
                '  "possible_explanations": ["Physical failure mechanism 1 with technical detail", "Physical failure mechanism 2", "Physical failure mechanism 3"],\n'
                '  "basis": [\n'
                '    "[FAA-H-8083-32B Powerplant Handbook, Ch. 1 & 10](https://www.faa.gov/sites/faa.gov/files/regulations_policies/handbooks_manuals/aviation/FAA-H-8083-32-AMT-Powerplant-Vol-2.pdf) - Specific system principle relevant to complaint.",\n'
                '    "[FAA AC 43.13-1B Aircraft Inspection & Repair](https://www.faa.gov/regulations_policies/advisory_circulars/index.cfm/go/document.information/documentID/99861) - Inspection techniques and maintenance practices."\n'
                '  ],\n'
                '  "assumptions": ["Key operational or structural precondition 1", "Precondition 2"],\n'
                '  "information_needed": ["Concrete diagnostic inspection step 1", "Diagnostic measurement or test 2"],\n'
                '  "what_would_weaken_this": ["Observable condition that would rule out or weaken hypothesis 1", "Condition that would rule out hypothesis 2"],\n'
                '  "limits": [\n'
                '    "UNVERIFIED HYPOTHESIS: Conceptual engineering troubleshooting only, NOT certified AMM maintenance instructions.",\n'
                '    "Consult applicable FAA-approved Aircraft Maintenance Manuals (AMM) and licensed A&P mechanic before performing work."\n'
                '  ]\n'
                "}\n"
                "Rules:\n"
                "- Directly address the specific component and fault mentioned in the complaint (e.g. oil leak, fuel smell, landing gear shimmy, flight controls, electrical, etc.). Do NOT default to unrelated components.\n"
                "- Include markdown links to the official FAA reference websites in the basis array.\n"
                "- Do not fabricate serial numbers or specific model procedures."
            )

            try:
                res = await provider.chat_completion(
                    messages=[{"role": "user", "content": prompt}],
                    response_format={"type": "json_object"},
                    timeout=18.0,
                )
                content = res.get("content", "")
                if "{" in content and "}" in content:
                    data = json.loads(content[content.find("{") : content.rfind("}") + 1])
                    return HypothesisEnvelope(
                        answer_id=uuid4(),
                        run_id=run_id,
                        parent_answer_id=parent_answer.answer_id,
                        state_revision=state_revision,
                        mode="HYPOTHESIS",
                        unverified=True,
                        summary=data.get("summary"),
                        possible_explanations=data.get("possible_explanations") or [],
                        basis=data.get("basis") or [],
                        assumptions=data.get("assumptions") or [],
                        information_needed=data.get("information_needed") or [],
                        what_would_weaken_this=data.get("what_would_weaken_this") or [],
                        limits=data.get("limits") or [
                            "UNVERIFIED HYPOTHESIS: Conceptual engineering troubleshooting only, NOT certified maintenance procedures.",
                            "Do not perform maintenance without applicable approved type certificate manuals and licensed A&P signoff.",
                        ],
                        historical_claims=[],
                    )
            except Exception as exc:
                import logging
                logging.getLogger("maintenance.hypotheses").warning(
                    "LM hypothesis generation failed; falling back to dynamic reference: %s", exc
                )

        return cls.generate_conceptual_hypothesis(parent_answer, query_raw, run_id, state_revision)

    @staticmethod
    def generate_conceptual_hypothesis(
        parent_answer: AnswerEnvelope,
        query_raw: str,
        run_id: UUID,
        state_revision: int,
    ) -> HypothesisEnvelope:
        """Generates conceptual possible explanations and information gaps citing FAA technical references."""
        q_lower = query_raw.lower()

        if any(w in q_lower for w in ["fuel", "gas", "smell", "fume"]):
            explanations = [
                "Fuel injector boss or primer line connection seal relaxation allowing localized seeping under delivery pressure.",
                "Deteriorated fuel strainer bowl gasket or drain valve O-ring seal leaking into lower cowl cavity.",
                "Vapor migration through cowl ventilation passages into cabin air heat exchanger interface.",
            ]
            basis = [
                "[FAA-H-8083-32B Powerplant Handbook, Ch. 2 Fuel Metering](https://www.faa.gov/sites/faa.gov/files/regulations_policies/handbooks_manuals/aviation/FAA-H-8083-32-AMT-Powerplant-Vol-2.pdf) - Fuel distribution lines and injection systems.",
                "[FAA AC 43.13-1B Section 8 Fuel Systems](https://www.faa.gov/regulations_policies/advisory_circulars/index.cfm/go/document.information/documentID/99861) - Fuel line inspection, clamp integrity, and leak limits.",
            ]
            assumptions = [
                "Fuel system operates within approved gravity or engine-driven pump pressure limits.",
                "Cabin heating shroud has not suffered internal exhaust wall breach.",
            ]
            information_needed = [
                "Pressurize fuel system with auxiliary electric pump and perform mirror/flashlight leak inspection.",
                "Conduct carbon monoxide (CO) detector check during taxi ground run with cabin heat on.",
            ]
            what_would_weaken = [
                "Zero fuel odor detected with fuel selector positioned to OFF.",
                "Odor identified as hydraulic fluid or hot electrical insulation rather than aviation gasoline.",
            ]
        elif any(w in q_lower for w in ["gear", "brake", "shimmy", "tire", "wheel"]):
            explanations = [
                "Shimmy damper hydraulic fluid depletion or internal seal blow-by allowing undamped gear oscillation.",
                "Excessive freeplay or worn bushings in upper/lower torque link scissor joints.",
                "Main gear brake master cylinder seal wear or trapped air in hydraulic supply line.",
            ]
            basis = [
                "[FAA-H-8083-31B Airframe Handbook, Ch. 13 Landing Gear](https://www.faa.gov/documentlibrary/media/advisory_circular/ac_65-15a.pdf) - Shimmy damper servicing and torque link alignment.",
                "[FAA AC 43.13-1B Ch. 9 Landing Gear Maintenance](https://www.faa.gov/regulations_policies/advisory_circulars/index.cfm/go/document.information/documentID/99861) - Wheel bearing, brake bleeding, and tire wear tolerances.",
            ]
            assumptions = [
                "Nose gear strut inflation pressure conforms to weight-on-wheels extension specifications.",
                "Brake hydraulic fluid type strictly conforms to MIL-PRF-5606 / manufacturer standard.",
            ]
            information_needed = [
                "Measure torque link apex bolt play and bushing radial clearance with dial indicator.",
                "Bleed brake calipers and pressure-test hydraulic lines for spongy pedal symptom.",
            ]
            what_would_weaken = [
                "Shimmy damper fluid level verified completely full with zero air displacement.",
                "Wheel assembly balanced dynamically with zero tire flat-spotting.",
            ]
        elif any(w in q_lower for w in ["flap", "rudder", "aileron", "control", "flutter", "rigging"]):
            explanations = [
                "Control cable tension relaxation below temperature-compensated tensiometer limits.",
                "Hinge bearing binding or radial play causing asymmetric aerodynamic deflection under airloads.",
                "Trim tab actuator push-pull rod end wear exceeding rotational freeplay tolerances.",
            ]
            basis = [
                "[FAA-H-8083-31B Airframe Handbook, Ch. 2 Flight Controls](https://www.faa.gov/documentlibrary/media/advisory_circular/ac_65-15a.pdf) - Cable rigging, tension charts, and surface travel limits.",
                "[FAA AC 43.13-1B Ch. 7 Aircraft Hardware & Rigging](https://www.faa.gov/regulations_policies/advisory_circulars/index.cfm/go/document.information/documentID/99861) - Control cable inspection and turnbuckle safety wiring.",
            ]
            assumptions = [
                "Airframe primary structural attachment bulkheads are free of cracks or deformation.",
                "Control surface balance conforms to repainting/rebalancing requirements.",
            ]
            information_needed = [
                "Measure cable tension with calibrated tensiometer against ambient temperature chart.",
                "Check surface travel stops with inclinometer against type certificate data sheet (TCDS).",
            ]
            what_would_weaken = [
                "Cable tensions and travel angles match type certificate limits exactly.",
                "Control surface mass balance weights verified securely attached with zero unbalance.",
            ]
        else:
            explanations = [
                "Thermal cycling causing fastener torque relaxation at gasket/seal junctions under operating cycles.",
                "Localized sealing interface corrosion or flange warping preventing uniform gasket seating.",
                "Secondary migration from overhead component seals (e.g. valve cover or pushrod tubes) pooling at lower interfaces.",
            ]
            basis = [
                "[FAA-H-8083-32B Powerplant Handbook, Ch. 1 & 10](https://www.faa.gov/sites/faa.gov/files/regulations_policies/handbooks_manuals/aviation/FAA-H-8083-32-AMT-Powerplant-Vol-2.pdf) - Induction sealing, cylinder assemblies, and lubrication circuits.",
                "[FAA AC 43.13-1B Aircraft Inspection & Repair](https://www.faa.gov/regulations_policies/advisory_circulars/index.cfm/go/document.information/documentID/99861) - Torque relaxation, gasket replacement, and leak check procedures.",
            ]
            assumptions = [
                "Operating temperatures and manifold pressures remain within certified operating limitations.",
                "Mating surfaces have not suffered mechanical score marks or crack propagation.",
            ]
            information_needed = [
                "Clean and degrease component area, apply developer powder, and perform ground run to trace exact origin.",
                "Verify fastener torque values against engine manufacturer overhaul manual specifications.",
            ]
            what_would_weaken = [
                "Component joint verified dry with leak originating entirely from remote breather or accessory pad.",
                "Ground run under pressure fails to replicate any fluid egress.",
            ]

        summary = f"Troubleshooting analysis for '{query_raw[:60]}' grounded in FAA Aviation Maintenance Technician handbooks (FAA-H-8083) and AC 43.13-1B inspection practices."
        limits = [
            "UNVERIFIED HYPOTHESIS: Conceptual engineering troubleshooting only, NOT certified AMM maintenance instructions.",
            "Do not perform aircraft maintenance without applicable approved type certificate manuals and licensed A&P signoff.",
        ]

        return HypothesisEnvelope(
            answer_id=uuid4(),
            run_id=run_id,
            parent_answer_id=parent_answer.answer_id,
            state_revision=state_revision,
            mode="HYPOTHESIS",
            unverified=True,
            summary=summary,
            possible_explanations=explanations,
            basis=basis,
            assumptions=assumptions,
            information_needed=information_needed,
            what_would_weaken_this=what_would_weaken,
            limits=limits,
            historical_claims=[],
        )
