"""Typed context packet construction and safe conversation compaction."""

from typing import Any

from maintenance.contracts import SessionSnapshot


class ContextManager:
    @staticmethod
    def build_run_context(
        session: SessionSnapshot,
        max_recent_turns: int = 6,
    ) -> dict[str, Any]:
        """Builds a bounded context packet for agent inference."""
        recent_messages = session.messages[-max_recent_turns:] if session.messages else []

        # Summarize older messages if list is long
        summary = None
        if len(session.messages) > max_recent_turns:
            older = session.messages[:-max_recent_turns]
            user_questions = [
                m.get("content", {}).get("text", "")
                for m in older
                if m.get("role") == "user"
            ]
            summary = f"Earlier questions explored in this session: {'; '.join(user_questions[:3])}"

        return {
            "session_id": str(session.session_id),
            "domain": session.domain,
            "state_revision": session.state_revision,
            "aircraft_profile": session.aircraft_profile,
            "board": [b.model_dump(mode="json") for b in session.board],
            "recent_messages": recent_messages,
            "history_summary": summary,
        }
