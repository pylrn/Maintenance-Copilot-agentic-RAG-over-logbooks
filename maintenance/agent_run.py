"""Agent execution runner, evidence retrieval, validation gate and release orchestration."""

import asyncio
import json
import logging
import time
from typing import Any
from uuid import UUID

from maintenance.agent import AGENT_TOOLS, get_system_prompt
from maintenance.answer_rendering import render_extractive_answer
from maintenance.answer_validation import validate_answer, validate_draft
from maintenance.board import BoardManager
from maintenance.contracts import (
    AnswerEnvelope,
    DraftAnswer,
    ServiceScope,
)
from maintenance.evidence_sufficiency import supporting_evidence
from maintenance.events import EventBus
from maintenance.ingest.annotate import mentions
from maintenance.models.provider import LLMProvider
from maintenance.session_repository import SessionRepository
from maintenance.telemetry import observation, observed, trace_info
from maintenance.synthesis import (EvidenceSelection, PROMPT_VERSION, check_selection, synthesis_messages)
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
    "safe to fly",
    "airworthy",
    "approved procedure",
    "guaranteed fix",
    "permanently fixed",
]


class AgentRunner:
    def __init__(
        self,
        repository: SessionRepository,
        event_bus: EventBus,
        provider: LLMProvider,
        synthesis_reasoning_effort: str = "low",
        synthesis_timeout_seconds: float = 12.0,
        synthesis_max_tokens: int = 3072,
    ):
        self.repository = repository
        self.event_bus = event_bus
        self.provider = provider
        self.synthesis_reasoning_effort = synthesis_reasoning_effort
        self.synthesis_timeout_seconds = synthesis_timeout_seconds
        self.synthesis_max_tokens = synthesis_max_tokens

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

    async def synthesize_conclusions(
        self,
        provider: LLMProvider | None,
        query_text: str,
        fetched_evidence: dict[UUID, dict[str, Any]],
    ) -> tuple[EvidenceSelection | None, dict[str, Any]]:
        """One bounded structured selection; rejected output is never released as prose."""
        model = provider.model_name if provider else None
        info = {"prompt_version": PROMPT_VERSION, "requested_model": model,
                "effective_model": None, "reasoning_effort": self.synthesis_reasoning_effort,
                "status": "not_requested", "fallback_reason": None}
        if not provider or not provider.is_configured or not fetched_evidence:
            return None, info
        start = time.perf_counter()
        with observation("synthesis.selection", "guardrail", requested_model=model) as span:
            try:
                res = await asyncio.wait_for(
                    provider.chat_completion(
                        messages=synthesis_messages(query_text, fetched_evidence),
                        response_format={"type": "json_schema", "json_schema": {
                            "name": "evidence_selection", "strict": True,
                            "schema": EvidenceSelection.model_json_schema(),
                        }},
                        reasoning_effort=(self.synthesis_reasoning_effort
                                          if provider.provider_type == "gemini" else None),
                        max_tokens=self.synthesis_max_tokens,
                        timeout=self.synthesis_timeout_seconds,
                    ), timeout=self.synthesis_timeout_seconds,
                )
                info.update(effective_model=res.get("effective_model"), usage=res.get("usage", {}))
                selection = EvidenceSelection.model_validate_json(res.get("content", ""))
                check_selection(selection, fetched_evidence)
                info.update(status="validated_selection", decision=selection.decision)
                return selection, info
            except Exception as exc:
                # Exception type only: request objects/messages may include credentials or source data.
                code = getattr(exc, "status_code", None)
                reason = ("rate_limited" if code == 429 else "timeout"
                          if isinstance(exc, (TimeoutError, asyncio.TimeoutError))
                          else "provider_error" if code is not None else "invalid_selection")
                info.update(status="extractive_fallback", fallback_reason=reason,
                            error_type=type(exc).__name__)
                logger.warning("Evidence selection fallback: %s", reason)
                return None, info
            finally:
                info["latency_ms"] = round((time.perf_counter() - start) * 1000, 2)
                span.update(metadata={k: v for k, v in info.items() if k != "usage"})

    @observed("agent.run", "agent",
        metadata=lambda self, deps, query_text, domain="aviation": {"run_id": str(deps.run_id), "session_id": str(deps.session_id), "mode": deps.mode, "domain": domain, "state_revision": deps.state_revision},
        result_metadata=lambda answer: {"status": answer.status, "claim_count": len(answer.claims)})
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
                {"mode": deps.mode, "session_id": str(deps.session_id), "telemetry": trace_info(run_id=deps.run_id)},
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

            # Filter out spurious dense noise when query is gibberish or lacks domain terms
            ms = mentions(query_text)
            hits = search_res.get("hits", [])
            has_relevant_hits = any(h.get("compatibility") in ("direct", "related") for h in hits)
            has_keywords = bool(ms) or any(
                kw in query_text.lower()
                for kw in [
                    "leak", "crack", "smoke", "noise", "vibration", "oil", "fuel", "engine",
                    "intake", "cylinder", "gasket", "flap", "rudder", "gear", "brake",
                    "tire", "light", "door", "window", "pump", "valve", "hot", "pressure", "exhaust"
                ]
            )
            if not has_keywords and not has_relevant_hits:
                hit_ids = []

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
                        "Historical logs do not establish approved specifications, repair instructions, or operational clearance.",
                        "Refer to official FAA-approved Aircraft Maintenance Manuals (AMM) for certified specifications.",
                    ],
                    missing=[
                        "Applicable approved documentation and qualified operational assessment are not present in these historical records.",
                    ],
                    clarification=None,
                )
                answer.headline = "Requested specification or operational guarantee is not established by historical logs."
                answer.generation = {"status": "not_requested", "requested_model": getattr(deps, "model_id", None),
                                     "effective_model": None, "fallback_reason": "outside_log_authority",
                                     "prompt_version": PROMPT_VERSION}
            else:
                answer = None
                run_provider = self._resolve_provider_for_run(getattr(deps, "model_id", None))
                # Evidence mode already has authoritative records from the prefetch.
                # Synthesize them once instead of asking an agent to retrieve them again.
                if run_provider and run_provider.is_configured and deps.mode != "EVIDENCE":
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
                                    summary=draft.summary,
                                    what_can_be_concluded=draft.what_can_be_concluded,
                                    what_cannot_be_concluded=draft.what_cannot_be_concluded,
                                )
                    except Exception as exc:
                        logger.warning("LLM generation/validation fallback to extractive: %s", type(exc).__name__)

                if answer is None:
                    answer_evidence = (
                        supporting_evidence(query_text, deps.fetched_evidence)
                        if deps.mode == "EVIDENCE" else deps.fetched_evidence
                    )
                    selection = None
                    generation = {"status": "not_requested", "requested_model": getattr(deps, "model_id", None),
                                  "effective_model": None, "prompt_version": PROMPT_VERSION,
                                  "fallback_reason": "no_matching_evidence" if not answer_evidence else "extractive_selected"}
                    if run_provider and run_provider.is_configured and answer_evidence:
                        selection, generation = await self.synthesize_conclusions(
                            run_provider, query_text, answer_evidence
                        )
                        if selection and selection.decision == "insufficient_evidence":
                            answer_evidence = {}

                    answer = render_extractive_answer(
                        run_id=deps.run_id,
                        mode=deps.mode,  # type: ignore
                        query_raw=query_text,
                        fetched_evidence=answer_evidence,
                        state_revision=deps.state_revision,
                        status="insufficient_evidence" if not answer_evidence else None,
                        synthesis_selection=selection,
                    )
                    answer.generation = generation

            # 7. Deterministic validation gate applied to ALL candidate answers BEFORE board update
            val_res = validate_answer(answer, deps.fetched_evidence, deps.computed_receipts, deps.mode)
            snapshots_list = list(deps.fetched_evidence.values())
            if not val_res.is_valid:
                logger.error("Released answer failed deterministic validation gate: %s", val_res.errors)
                rejected_generation = dict(answer.generation)
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
                answer.generation = {**rejected_generation, "status": "extractive_fallback", "fallback_reason": "source_validation_failed",
                                     "requested_model": getattr(deps, "model_id", None)}
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
                    "telemetry": trace_info(run_id=deps.run_id),
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
