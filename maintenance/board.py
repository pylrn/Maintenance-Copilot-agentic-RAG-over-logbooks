"""Investigation board state management."""

from uuid import UUID, uuid4

from maintenance.contracts import AnswerEnvelope, BoardItem


class BoardManager:
    @staticmethod
    def add_user_observation(
        board: list[BoardItem],
        text: str,
        state_revision: int,
        affected_components: list[str] | None = None,
        supersedes_id: UUID | None = None,
    ) -> list[BoardItem]:
        new_item = BoardItem(
            item_id=uuid4(),
            column="known",
            text=text,
            origin="user_report",
            origin_ref="user_input",
            created_revision=state_revision,
            supersedes=supersedes_id,
            verification_status="user_reported",
            affected_component_ids=affected_components or [],
        )
        return [*board, new_item]

    @staticmethod
    def update_from_answer(
        board: list[BoardItem],
        answer: AnswerEnvelope,
        state_revision: int,
    ) -> list[BoardItem]:
        updated = list(board)

        # Add reported items from claims
        for claim in answer.claims:
            # Find evidence ref
            origin_ref = "historical_logs"
            if claim.supports:
                first_sup = claim.supports[0]
                if hasattr(first_sup, "record_id"):
                    origin_ref = f"record:{first_sup.record_id}"

            item = BoardItem(
                item_id=uuid4(),
                column="reported",
                text=claim.text,
                origin="historical_log",
                origin_ref=origin_ref,
                created_revision=state_revision,
                supersedes=None,
                verification_status="source_validated",
                affected_component_ids=[],
            )
            updated.append(item)

        # Add missing items from missing / limitations
        for m in answer.missing:
            item = BoardItem(
                item_id=uuid4(),
                column="missing",
                text=m,
                origin="schema_gap",
                origin_ref=f"answer:{answer.answer_id}",
                created_revision=state_revision,
                supersedes=None,
                verification_status="unresolved",
                affected_component_ids=[],
            )
            updated.append(item)

        return updated
