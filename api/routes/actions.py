"""Investigation user action modes (hypothesis, distinguish, challenge, sensitivity, handover)."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import PlainTextResponse

from maintenance.auth import require_owner
from maintenance.contracts import (
    ActionRequest,
    SearchSpec,
    ServiceScope,
)
from maintenance.features.handover import HandoverService
from maintenance.hypotheses import HypothesisService

router = APIRouter(tags=["actions"])


@router.post("/sessions/{session_id}/actions")
async def perform_action(
    session_id: UUID,
    payload: ActionRequest,
    request: Request,
    owner_id: UUID = Depends(require_owner),
):
    repo = request.app.state.session_repo
    session = await repo.get_session(session_id, owner_id)
    if not session:
        raise HTTPException(404, "session_not_found")
    if session.state_revision != payload.expected_revision:
        raise HTTPException(
            409,
            f"state_revision_conflict: expected {payload.expected_revision} got {session.state_revision}",
        )

    # Find parent answer
    parent_answer = next(
        (a for a in session.answers if a.answer_id == payload.parent_answer_id),
        None,
    )
    if not parent_answer:
        raise HTTPException(404, "parent_answer_not_found")

    engine = request.app.state.search_engine
    corpus_ids = [
        c.manifest.corpus_id
        for c in engine.corpora.values()
        if c.manifest.domain == session.domain
    ] if engine else []

    if payload.action == "hypothesis":
        hypo_service = HypothesisService(request.app.state.pool)
        try:
            await hypo_service.authorize_hypothesis_request(
                session_id=session_id,
                owner_id=owner_id,
                parent_answer_id=payload.parent_answer_id,
                expected_revision=payload.expected_revision,
            )
        except Exception as exc:
            raise HTTPException(409, str(exc))

        provider = getattr(request.app.state, "provider", None)
        model_id = provider.model_name if (provider and provider.is_configured) else "extractive/v1"

        run_id, _ = await repo.create_run(
            session_id=session_id,
            owner_id=owner_id,
            mode="HYPOTHESIS",
            idempotency_key=payload.idempotency_key,
            request_text="Possible solutions - unverified conceptual exploration",
            expected_revision=payload.expected_revision,
            corpus_ids=corpus_ids,
            parent_answer_id=payload.parent_answer_id,
            model_id=model_id,
        )

        hypo_env = await hypo_service.generate_hypothesis_with_lm(
            provider=provider,
            parent_answer=parent_answer,  # type: ignore
            query_raw=parent_answer.headline,
            run_id=run_id,
            state_revision=payload.expected_revision,
        )

        new_rev = await repo.commit_answer_and_state(
            run_id=run_id,
            session_id=session_id,
            answer=hypo_env,
            validation_report={"valid": True, "mode": "HYPOTHESIS", "unverified": True},
            new_board_items=session.board,
        )

        return {
            "action": "hypothesis",
            "run_id": str(run_id),
            "state_revision": new_rev,
            "envelope": hypo_env.model_dump(mode="json"),
        }

    elif payload.action == "distinguish":
        comp_service = request.app.state.comparison_service
        rec_ids = payload.parameters.get("record_ids", [])
        if not rec_ids:
            # Pick first two records from parent claims
            for c in parent_answer.claims:
                for s in c.supports:
                    if hasattr(s, "record_id") and s.record_id not in rec_ids:
                        rec_ids.append(s.record_id)
                    if len(rec_ids) == 2:
                        break
                if len(rec_ids) == 2:
                    break

        if len(rec_ids) < 2:
            raise HTTPException(400, "distinguish_requires_at_least_two_records")

        scope = ServiceScope(owner_id=owner_id, corpus_ids=corpus_ids)
        receipt = await comp_service.compare(rec_ids, scope)
        return {
            "action": "distinguish",
            "record_ids": rec_ids,
            "comparison": receipt.result,
        }

    elif payload.action == "challenge":
        challenge_service = request.app.state.challenge_service
        scope = ServiceScope(owner_id=owner_id, corpus_ids=corpus_ids)
        res = await challenge_service.search_alternatives(parent_answer, scope)
        return {
            "action": "challenge",
            "result": res,
        }

    elif payload.action == "sensitivity":
        sens_service = request.app.state.sensitivity_service
        scope = ServiceScope(owner_id=owner_id, corpus_ids=corpus_ids)
        base_spec = SearchSpec(query_raw=parent_answer.headline, domain=session.domain)
        variants = [
            SearchSpec(query_raw="intake leaking", domain=session.domain),
            SearchSpec(query_raw="rocker cover leaking", domain=session.domain),
        ]
        receipt = await sens_service.compare_specs(base_spec, variants, scope)
        return {
            "action": "sensitivity",
            "result": receipt.result,
        }

    elif payload.action == "handover":
        md = HandoverService.generate_markdown(session, include_hypotheses=False)
        return {
            "action": "handover",
            "markdown": md,
        }

    raise HTTPException(400, f"unsupported_action: {payload.action}")


@router.get("/sessions/{session_id}/handover")
async def get_handover(
    session_id: UUID,
    request: Request,
    include_hypotheses: bool = Query(default=False),
    owner_id: UUID = Depends(require_owner),
):
    repo = request.app.state.session_repo
    session = await repo.get_session(session_id, owner_id)
    if not session:
        raise HTTPException(404, "session_not_found")

    md = HandoverService.generate_markdown(session, include_hypotheses=include_hypotheses)
    return PlainTextResponse(md, media_type="text/markdown")
