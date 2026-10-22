"""Handover document generator."""

from datetime import datetime, timezone

from maintenance.contracts import SessionSnapshot


class HandoverService:
    @staticmethod
    def generate_markdown(
        session: SessionSnapshot,
        include_hypotheses: bool = False,
    ) -> str:
        lines: list[str] = []
        now_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

        lines.append("# Maintenance Atlas Investigation Handover")
        lines.append(f"**Session ID:** `{session.session_id}`")
        lines.append(f"**Domain:** `{session.domain}`")
        lines.append(f"**State Revision:** `{session.state_revision}`")
        lines.append(f"**Generated:** {now_str}")
        lines.append("")

        lines.append("## 1. Aircraft / Investigation Profile")
        if session.aircraft_profile:
            for k, v in session.aircraft_profile.items():
                lines.append(f"- **{k.replace('_', ' ').title()}:** {v}")
        else:
            lines.append("No specific aircraft model configured (generic evaluation context).")
        lines.append("")

        lines.append("## 2. Investigation Board")
        known = [item for item in session.board if item.column == "known"]
        reported = [item for item in session.board if item.column == "reported"]
        missing = [item for item in session.board if item.column == "missing"]

        lines.append("### Known Observations (Session Context)")
        if known:
            for item in known:
                lines.append(f"- {item.text} *(Origin: {item.origin})*")
        else:
            lines.append("- *No user-confirmed observations entered.*")
        lines.append("")

        lines.append("### Reported in Historical Records")
        if reported:
            for item in reported:
                lines.append(f"- {item.text} *(Origin Ref: {item.origin_ref})*")
        else:
            lines.append("- *No verified historical findings recorded yet.*")
        lines.append("")

        lines.append("### Missing Information & Applicable Limits")
        if missing:
            for item in missing:
                lines.append(f"- {item.text}")
        else:
            lines.append("- *No unresolved gaps noted.*")
        lines.append("")

        lines.append("## 3. Validated Answers & Evidence")
        evidence_answers = [
            a for a in session.answers if getattr(a, "mode", "") != "HYPOTHESIS"
        ]
        if evidence_answers:
            for i, ans in enumerate(evidence_answers, 1):
                lines.append(f"### Answer {i} ({ans.mode} - {ans.status})")
                lines.append(f"**Headline:** {ans.headline}")
                lines.append("")
                lines.append("**Claims:**")
                for c in ans.claims:
                    lines.append(f"- [{c.claim_type}] {c.text}")
                    for s in c.supports:
                        if hasattr(s, "quote"):
                            lines.append(
                                f"  - Citation: Record `{s.record_id}` ({s.field}) [offset {s.start}:{s.end}]: \"{s.quote}\""
                            )
                if ans.limitations:
                    lines.append("")
                    lines.append("**Limitations:**")
                    for lim in ans.limitations:
                        lines.append(f"- {lim}")
                lines.append("")
        else:
            lines.append("No validated answers released.")
        lines.append("")

        if include_hypotheses:
            hypo_answers = [
                a for a in session.answers if getattr(a, "mode", "") == "HYPOTHESIS"
            ]
            if hypo_answers:
                lines.append("## Appendix: Unverified Hypotheses (Exploratory Only)")
                lines.append(
                    "> **DISCLAIMER:** These entries are conceptual unverified possibilities and do NOT constitute approved maintenance procedures or certified facts."
                )
                lines.append("")
                for h in hypo_answers:
                    lines.append(f"### Hypothesis (Parent Answer `{h.parent_answer_id}`)")
                    lines.append("**Possible Explanations:**")
                    for exp in h.possible_explanations:
                        lines.append(f"- {exp}")
                    lines.append("**Assumptions:**")
                    for asm in h.assumptions:
                        lines.append(f"- {asm}")
                    lines.append("**Information Needed:**")
                    for inf in h.information_needed:
                        lines.append(f"- {inf}")
                    lines.append("")

        lines.append("---")
        lines.append(
            "*Document produced by Maintenance Atlas. Historical maintenance records are reference only and not approved maintenance instructions.*"
        )
        return "\n".join(lines)
