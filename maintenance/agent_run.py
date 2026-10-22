"""Agent execution runner, evidence retrieval, validation gate and release orchestration."""

import logging

from maintenance.agent import AGENT_TOOLS, get_system_prompt
from maintenance.answer_rendering import render_extractive_answer
from maintenance.answer_validation import validate_answer, validate_draft
from maintenance.board import BoardManager
from maintenance.contracts import (
    AnswerEnvelope,
    DraftAnswer,
    ServiceScope,
)
from maintenance.events import EventBus
from maintenance.models.provider import LLMProvider
from maintenance.session_repository import SessionRepository
from maintenance.tools import (
    RunDeps,
    tool_get_records,
    tool_search_records,
)

logger = logging.getLogger("maintenance.runner")

# Questions asking for items explicitly absent from MaintNet logs
UNSUPPORTED_KEYWORDS = [
    "torque",
    "ft-lb",
    "in-lb",
    "airworthiness directive",
    "service bulletin",
    "manual step",
    "removal procedure",
    "installation sequence",
    "clearance limit",
    "manufacturer specification",
]


class AgentRunner:
    def __init__(
        self,
        repository: SessionRepository,
        event_bus: EventBus,
        provider: LLMProvider,
    ):
        self.repository = repository
        self.event_bus = event_bus
        self.provider = provider

    def _resolve_provider_for_run(self, model_id: str | None) -> LLMProvider | None:
        if not model_id or model_id == "extractive/v1":
            return None
        if self.provider and self.provider.is_configured and self.provider.model_name == model_id:
            return self.provider
        if "gemini" in model_id.lower() and self.provider and self.provider.api_key:
            return LLMProvider(
                api_key=self.provider.api_key if self.provider.provider_type == "gemini" else None,
                base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
                model_name=model_id,
                provider_type="gemini",
            )
        if "deepseek" in model_id.lower() and self.provider and self.provider.api_key:
            return LLMProvider(
                api_key=self.provider.api_key if self.provider.provider_type == "deepseek" else None,
                base_url="https://api.deepseek.com",
                model_name=model_id,
                provider_type="deepseek",
            )
        return self.provider if (self.provider and self.provider.is_configured) else None

    async def execute_run(
        self,
        deps: RunDeps,
        query_text: str,
        domain: str = "aviation",
    ) -> AnswerEnvelope:
        seq = 1
        try:
            # 1. run_started
            await self.event_bus.emit(
                deps.run_id,
                seq,
                "run_started",
                {"mode": deps.mode, "session_id": str(deps.session_id)},
            )
            seq += 1

            # 2. query_interpreted
            is_unsupported = any(kw in query_text.lower() for kw in UNSUPPORTED_KEYWORDS)
            await self.event_bus.emit(
                deps.run_id,
                seq,
                "query_interpreted",
                {
                    "query_raw": query_text,
                    "domain": domain,
                    "unsupported_request_detected": is_unsupported,
                },
            )
            seq += 1

            # 3. search_started
            await self.event_bus.emit(
                deps.run_id,
                seq,
                "search_started",
                {"query": query_text, "domain": domain},
            )
            seq += 1

            # 4. Execute search
            search_res = await tool_search_records(deps, query_text, domain=domain, top_k=6)
            hit_ids = [h["record_id"] for h in search_res.get("hits", [])]

            await self.event_bus.emit(
                deps.run_id,
                seq,
                "search_completed",
                {"hit_count": len(hit_ids), "record_ids": hit_ids},
            )
            seq += 1

            # 5. Fetch authoritative records
            fetched_records = []
            if hit_ids:
                await self.event_bus.emit(
                    deps.run_id,
                    seq,
                    "tool_started",
                    {"tool_name": "get_records", "record_ids": hit_ids},
                )
                seq += 1

                records_res = await tool_get_records(deps, hit_ids)
                if deps.record_service:
                    try:
                        scope = ServiceScope(owner_id=deps.owner_id, corpus_ids=deps.corpus_ids)
                        records_list = await deps.record_service.fetch(hit_ids, scope)
                        for rec in records_list:
                            fetched_records.append(
                                {
                                    "record_id": rec.record_id,
                                    "domain": rec.domain,
                                    "source_id": rec.source_id,
                                    "corpus_id": str(rec.corpus_id) if rec.corpus_id else None,
                                    "problem_raw": rec.problem_raw,
                                    "action_raw": rec.action_raw,
                                    "fields": {
                                        **(rec.original_fields or {}),
                                        **({"PROBLEM": rec.problem_raw} if rec.problem_raw else {}),
                                        **({"ACTION": rec.action_raw} if rec.action_raw else {}),
                                    },
                                    "original_fields": rec.original_fields,
                                    "source_sha256": rec.field_sha256.get("PROBLEM") or rec.field_sha256.get("DESCRIPTION") or "",
                                }
                            )
                    except Exception as exc:
                        logger.warning("Failed to fetch full record snapshots for UI: %s", exc)

                await self.event_bus.emit(
                    deps.run_id,
                    seq,
                    "tool_completed",
                    {"tool_name": "get_records", "fetched_count": len(records_res.get("records", []))},
                )
                seq += 1

            await self.event_bus.emit(
                deps.run_id,
                seq,
                "evidence_ready",
                {
                    "evidence_snapshots_count": len(deps.fetched_evidence),
                    "records": fetched_records,
                },
            )
            seq += 1

            # 6. validation_started
            await self.event_bus.emit(
                deps.run_id,
                seq,
                "validation_started",
                {"evidence_count": len(deps.fetched_evidence)},
            )
            seq += 1

            # Check for explicit refusal / unsupported question
            if is_unsupported:
                answer = render_extractive_answer(
                    run_id=deps.run_id,
                    mode=deps.mode,  # type: ignore
                    query_raw=query_text,
                    fetched_evidence=deps.fetched_evidence,
                    state_revision=deps.state_revision,
                    status="insufficient_evidence",
                    limitations=[
                        "Requested procedure/torque specification is absent from historical maintenance logs.",
                        "Refer to official FAA-approved Aircraft Maintenance Manuals (AMM) for certified specifications.",
                    ],
                    missing=[
                        "Approved torque specification / procedural steps not present in dataset.",
                    ],
                    clarification=None,
                )
                answer.headline = "Requested procedural specification absent from historical logs."
            else:
                answer = None
                run_provider = self._resolve_provider_for_run(getattr(deps, "model_id", None))
                if run_provider and run_provider.is_configured:
                    try:
                        async def dispatch_search(args):
                            return await tool_search_records(
                                deps,
                                query=args.get("query", query_text),
                                domain=args.get("domain", domain),
                                top_k=args.get("top_k", 6),
                            )

                        async def dispatch_get_records(args):
                            return await tool_get_records(
                                deps,
                                record_ids=args.get("record_ids", []),
                            )

                        async def dispatch_compare(args):
                            from maintenance.tools import tool_compare_records
                            return await tool_compare_records(deps, record_ids=args.get("record_ids", []))

                        async def dispatch_patterns(args):
                            from maintenance.tools import tool_get_pattern_summary
                            return await tool_get_pattern_summary(deps, component=args.get("component", ""), domain=args.get("domain", domain))

                        async def dispatch_visual(args):
                            from maintenance.tools import tool_get_component_context
                            return await tool_get_component_context(deps, component_id=args.get("component_id", ""))

                        tool_dispatch = {
                            "search_records": dispatch_search,
                            "get_records": dispatch_get_records,
                            "compare_records": dispatch_compare,
                            "get_pattern_summary": dispatch_patterns,
                            "get_component_context": dispatch_visual,
                        }

                        evidence_summary = []
                        for ev_id, ev in deps.fetched_evidence.items():
                            evidence_summary.append(
                                f"Evidence ID: {ev_id} | Record ID: {ev['record_id']} | Field: {ev['field']} | "
                                f"Text: \"{ev['raw_text']}\" | SHA256: {ev['source_sha256']}"
                            )

                        messages = [
                            {"role": "system", "content": get_system_prompt()},
                            {
                                "role": "user",
                                "content": (
                                    f"User Query: {query_text}\n"
                                    f"Domain: {domain}\n"
                                    f"Authoritative Fetched Evidence:\n" + "\n".join(evidence_summary)
                                ),
                            },
                        ]

                        final_resp, message_history = await run_provider.roundtrip_tool_loop(
                            messages=messages,
                            tools=AGENT_TOOLS,
                            tool_dispatch=tool_dispatch,
                            max_turns=3,
                            max_tool_calls=deps.max_tool_calls,
                            deadline_seconds=25.0,
                        )
                        # Persist exact native model tool transcript
                        if self.repository and hasattr(self.repository, "save_model_messages"):
                            await self.repository.save_model_messages(
                                run_id=deps.run_id,
                                turn_index=0,
                                messages=message_history,
                                provider=run_provider.provider_type,
                            )
                        content = final_resp.get("content", "")
                        if "{" in content and "proposed_status" in content:
                            import json
                            draft_dict = json.loads(content[content.find("{") : content.rfind("}") + 1])
                            draft = DraftAnswer.model_validate(draft_dict)
                            val_res = validate_draft(draft, deps.fetched_evidence, deps.computed_receipts, deps.mode)  # type: ignore
                            if val_res.is_valid:
                                from maintenance.answer_rendering import build_allowed_actions
                                answer = AnswerEnvelope(
                                    answer_id=deps.run_id,
                                    run_id=deps.run_id,
                                    mode=deps.mode,  # type: ignore
                                    status=draft.proposed_status,
                                    headline=f"Historical maintenance records matching '{query_text[:40]}'.",
                                    claims=draft.findings + draft.historical_actions + draft.contrasting_cases,
                                    limitations=draft.limitation_refs or [
                                        "Historical maintenance records lack operational context and model identity."
                                    ],
                                    missing=draft.gap_refs,
                                    clarification=draft.clarification_ref,
                                    visual_refs=draft.component_refs,
                                    allowed_actions=build_allowed_actions(
                                        deps.run_id, deps.state_revision, hit_ids, deps.mode  # type: ignore
                                    ),
                                )
                    except Exception as exc:
                        logger.warning("LLM generation/validation fallback to extractive: %s", type(exc).__name__)

                if answer is None:
                    answer = render_extractive_answer(
                        run_id=deps.run_id,
                        mode=deps.mode,  # type: ignore
                        query_raw=query_text,
                        fetched_evidence=deps.fetched_evidence,
                        state_revision=deps.state_revision,
                    )

            # 7. Deterministic validation gate applied to ALL candidate answers BEFORE board update
            val_res = validate_answer(answer, deps.fetched_evidence, deps.computed_receipts, deps.mode)
            snapshots_list = list(deps.fetched_evidence.values())
            if not val_res.is_valid:
                logger.error("Released answer failed deterministic validation gate: %s", val_res.errors)
                # Fallback to insufficient evidence answer with unverified claims stripped
                answer = render_extractive_answer(
                    run_id=deps.run_id,
                    mode=deps.mode,
                    query_raw=query_text,
                    fetched_evidence={},
                    state_revision=deps.state_revision,
                    status="insufficient_evidence",
                    limitations=["Evidence validation gate rejected unsupported or corrupted claim citations."],
                )
                val_report = {
                    "valid": False,
                    "errors": val_res.errors,
                    "claims_count": 0,
                    "evidence_checked": len(snapshots_list),
                    "fallback_engaged": True,
                }
            else:
                val_report = {
                    "valid": True,
                    "claims_count": len(answer.claims),
                    "evidence_checked": len(snapshots_list),
                    "errors": [],
                }

            # 8. Update board from verified released answer only
            session_snap = await self.repository.get_session(deps.session_id, deps.owner_id)
            current_board = session_snap.board if session_snap else []
            new_board = BoardManager.update_from_answer(current_board, answer, deps.state_revision)

            await self.repository.save_evidence_snapshots(deps.run_id, snapshots_list)

            new_rev = await self.repository.commit_answer_and_state(
                run_id=deps.run_id,
                session_id=deps.session_id,
                answer=answer,
                validation_report=val_report,
                new_board_items=new_board,
            )

            # If run was cancelled concurrently, stop immediately without emitting answer_validated
            if new_rev < 0:
                logger.info("Run %s was cancelled before commit; suppressing answer release", deps.run_id)
                return answer

            # 9. board_updated (after successful commit)
            await self.event_bus.emit(
                deps.run_id,
                seq,
                "board_updated",
                {
                    "board_items_count": len(new_board),
                    "columns": {
                        "known": sum(1 for b in new_board if b.column == "known"),
                        "reported": sum(1 for b in new_board if b.column == "reported"),
                        "missing": sum(1 for b in new_board if b.column == "missing"),
                    },
                },
            )
            seq += 1

            # 10. answer_validated
            envelope_data = answer.model_dump(mode="json")
            await self.event_bus.emit(
                deps.run_id,
                seq,
                "answer_validated",
                {
                    "answer_id": str(answer.answer_id),
                    "status": answer.status,
                    "headline": answer.headline,
                    "claims_count": len(answer.claims),
                    "new_state_revision": new_rev,
                    "envelope": envelope_data,
                    "answer": envelope_data,
                },
            )
            seq += 1

            # 11. done
            await self.event_bus.emit(
                deps.run_id,
                seq,
                "done",
                {"run_id": str(deps.run_id), "completed": True},
            )

            return answer

        except Exception as exc:
            logger.error("execute_run failed: %s", exc, exc_info=True)
            if self.repository and self.repository.pool:
                async with self.repository.pool.acquire() as conn:
                    await conn.execute(
                        "UPDATE runs SET status = 'failed', completed_at = now() WHERE run_id = $1",
                        deps.run_id,
                    )
            await self.event_bus.emit(
                deps.run_id,
                seq,
                "run_failed",
                {"run_id": str(deps.run_id), "error": str(exc)},
            )
            raise
