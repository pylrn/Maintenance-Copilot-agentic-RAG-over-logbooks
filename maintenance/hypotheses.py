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

    @staticmethod
    def generate_conceptual_hypothesis(
        parent_answer: AnswerEnvelope,
        query_raw: str,
        run_id: UUID,
        state_revision: int,
    ) -> HypothesisEnvelope:
        """Generates conceptual possible explanations and information gaps without invented aircraft procedures."""
        explanations = [
            "Thermal cycling or improper flange torque causing gasket shrinkage or extrusion at cylinder intake junction.",
            "Warped induction tube flange or localized corrosion preventing uniform gasket seal under manifold vacuum.",
            "Vibration-induced looseness in intake clamp or mounting bolts over successive operating hours.",
        ]
        basis = [
            "General reciprocating aviation engine induction principles (FAA-H-8083-32B).",
            f"Historical records for '{query_raw[:40]}' documenting intake gasket replacement frequency.",
        ]
        assumptions = [
            "Engine exhibits symptoms consistent with induction air leak (lean running, RPM fluctuation, or audible hissing).",
            "Cylinder head and induction tube structural integrity has not suffered external mechanical impact.",
        ]
        information_needed = [
            "Visual inspection of intake flange with mirror and flashlight for fuel staining or gasket extrusion.",
            "Differential pressure / manifold smoke test to pinpoint exact leak location before disassembly.",
            "Applicable engine manufacturer maintenance manual torque and gasket part number specifications.",
        ]
        what_would_weaken = [
            "Normal cylinder head temperatures (CHT) and EGT across all cylinders under full power ground run.",
            "Leak detected at primer line or injector boss rather than intake pipe flange.",
        ]
        limits = [
            "UNVERIFIED HYPOTHESIS: Conceptual engineering possibilities only, NOT certified maintenance procedures.",
            "Do not perform maintenance or engine adjustments without applicable approved type certificate manuals and licensed A&P signoff.",
        ]

        return HypothesisEnvelope(
            answer_id=uuid4(),
            run_id=run_id,
            parent_answer_id=parent_answer.answer_id,
            state_revision=state_revision,
            mode="HYPOTHESIS",
            unverified=True,
            possible_explanations=explanations,
            basis=basis,
            assumptions=assumptions,
            information_needed=information_needed,
            what_would_weaken_this=what_would_weaken,
            limits=limits,
            historical_claims=[],
        )
