"""Regression tests verifying single JSONB encoding in SessionRepository.

Asserts jsonb_typeof on stored rows for sessions, runs, messages, answers,
claim_supports, session board updates, and model_messages.
Verifies get_session roundtrip and backward compatibility with legacy string rows.
"""

import json
import os
from uuid import uuid4

import pytest

from maintenance.contracts import (
    AnswerEnvelope,
    BoardItem,
    Claim,
    ReceiptSupport,
)
from maintenance.db import Database
from maintenance.session_repository import SessionRepository

pytestmark = [
    pytest.mark.skipif(
        not os.getenv("TEST_DATABASE_URL"), reason="isolated PostgreSQL required"
    ),
    pytest.mark.asyncio,
]


async def test_session_repository_jsonb_typeof_writes():
    """Verify that SessionRepository writes store native JSONB objects/arrays, not double-encoded strings."""
    db = Database(os.environ["TEST_DATABASE_URL"])
    await db.open()
    try:
        await db.migrate()
        repo = SessionRepository(db.pool)
        owner_id = uuid4()

        # 1. create_session: aircraft_profile and initial board
        profile = {"airframe": "PA-28", "serial": "28-1001", "hours": 1250}
        session = await repo.create_session(
            owner_id=owner_id,
            domain="aviation",
            title="PA-28 Fuel Pressure Investigation",
            aircraft_profile=profile,
        )

        async with db.pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT
                    jsonb_typeof(aircraft_profile) AS profile_typeof,
                    aircraft_profile,
                    jsonb_typeof(board) AS board_typeof,
                    board
                FROM sessions
                WHERE session_id = $1
                """,
                session.session_id,
            )
            assert row is not None
            assert row["profile_typeof"] == "object"
            assert row["aircraft_profile"] == profile
            assert row["board_typeof"] == "object"
            assert row["board"] == {"known": [], "reported": [], "missing": []}

        # 2. update_session_profile: updated aircraft_profile
        updated_profile = {"airframe": "PA-28R", "serial": "28-1001", "hours": 1260}
        new_rev = await repo.update_session_profile(
            session_id=session.session_id,
            owner_id=owner_id,
            expected_revision=0,
            aircraft_profile=updated_profile,
            title="Updated PA-28R Investigation",
        )
        assert new_rev == 1

        async with db.pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT
                    jsonb_typeof(aircraft_profile) AS profile_typeof,
                    aircraft_profile,
                    title,
                    state_revision
                FROM sessions
                WHERE session_id = $1
                """,
                session.session_id,
            )
            assert row is not None
            assert row["profile_typeof"] == "object"
            assert row["aircraft_profile"] == updated_profile
            assert row["state_revision"] == 1

        # 3. create_run: corpus_ids and user message content
        cid1 = uuid4()
        cid2 = uuid4()
        idempotency_key = uuid4()
        request_text = "Fuel pressure fluctuation during climb"

        run_id, is_new = await repo.create_run(
            session_id=session.session_id,
            owner_id=owner_id,
            mode="EVIDENCE",
            idempotency_key=idempotency_key,
            request_text=request_text,
            expected_revision=1,
            corpus_ids=[cid1, cid2],
            prompt_version="v1.0",
            model_id="deepseek-flash",
        )
        assert is_new is True

        async with db.pool.acquire() as conn:
            # Check runs.corpus_ids
            r_row = await conn.fetchrow(
                """
                SELECT jsonb_typeof(corpus_ids) AS corpus_typeof, corpus_ids
                FROM runs
                WHERE run_id = $1
                """,
                run_id,
            )
            assert r_row is not None
            assert r_row["corpus_typeof"] == "array"
            assert r_row["corpus_ids"] == [str(cid1), str(cid2)]

            # Check messages (user message)
            m_row = await conn.fetchrow(
                """
                SELECT jsonb_typeof(content) AS content_typeof, content, role, source_type
                FROM messages
                WHERE session_id = $1 AND role = 'user'
                """,
                session.session_id,
            )
            assert m_row is not None
            assert m_row["content_typeof"] == "object"
            assert m_row["content"] == {"text": request_text}

        # 4. commit_answer_and_state: answers envelope, validation_report, receipt result_keys, board, assistant message
        receipt_id = uuid4()
        async with db.pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO computed_receipts (
                    receipt_id, run_id, kind, parameters, result, corpus_ids, manifest_sha256, contributing_ids, validator_version
                ) VALUES ($1, $2, 'aggregate', '{}', '{}', '[]', $3, '[]', 'computation/v1')
                """,
                receipt_id,
                run_id,
                "0" * 64,
            )

        sup = ReceiptSupport(
            kind="aggregate_receipt",
            receipt_id=receipt_id,
            result_keys=["fuel_pump_failure_rate", "vapor_lock_frequency"],
        )
        claim = Claim(
            claim_id="claim-fuel-1",
            text="High incidence of vapor lock reported in summer ambient temperatures",
            claim_type="count",
            supports=[sup],
        )
        answer = AnswerEnvelope(
            answer_id=uuid4(),
            run_id=run_id,
            mode="EVIDENCE",
            status="supported_historical",
            headline="Vapor lock probable in auxiliary fuel pump lines",
            claims=[claim],
            limitations=["Ambient temperature assumed above 30C"],
            missing=[],
        )
        board_item = BoardItem(
            item_id=uuid4(),
            column="known",
            text="Auxiliary pump vapor lock confirmed in historical records",
            origin="historical_log",
            origin_ref="LOG:FUEL-2023",
            created_revision=1,
            verification_status="source_validated",
            affected_component_ids=["fuel_pump_aux"],
        )
        validation_report = {"valid": True, "score": 1.0, "notes": "all claims verified"}

        rev_after_commit = await repo.commit_answer_and_state(
            run_id=run_id,
            session_id=session.session_id,
            answer=answer,
            validation_report=validation_report,
            new_board_items=[board_item],
        )
        assert rev_after_commit == 2

        async with db.pool.acquire() as conn:
            # Check answers: envelope and validation_report
            ans_row = await conn.fetchrow(
                """
                SELECT
                    jsonb_typeof(envelope) AS envelope_typeof,
                    envelope,
                    jsonb_typeof(validation_report) AS val_typeof,
                    validation_report
                FROM answers
                WHERE answer_id = $1
                """,
                answer.answer_id,
            )
            assert ans_row is not None
            assert ans_row["envelope_typeof"] == "object"
            assert ans_row["val_typeof"] == "object"
            assert ans_row["envelope"]["headline"] == "Vapor lock probable in auxiliary fuel pump lines"
            assert ans_row["validation_report"] == validation_report

            # Check claim_supports: result_keys
            cs_row = await conn.fetchrow(
                """
                SELECT jsonb_typeof(result_keys) AS keys_typeof, result_keys
                FROM claim_supports
                WHERE answer_id = $1 AND claim_id = 'claim-fuel-1'
                """,
                answer.answer_id,
            )
            assert cs_row is not None
            assert cs_row["keys_typeof"] == "array"
            assert cs_row["result_keys"] == ["fuel_pump_failure_rate", "vapor_lock_frequency"]

            # Check sessions: board (now array of board items)
            sess_row = await conn.fetchrow(
                """
                SELECT jsonb_typeof(board) AS board_typeof, board, state_revision
                FROM sessions
                WHERE session_id = $1
                """,
                session.session_id,
            )
            assert sess_row is not None
            assert sess_row["board_typeof"] == "array"
            assert sess_row["state_revision"] == 2
            assert len(sess_row["board"]) == 1
            assert sess_row["board"][0]["item_id"] == str(board_item.item_id)
            assert sess_row["board"][0]["column"] == "known"

            # Check messages: assistant message content
            asst_msg_row = await conn.fetchrow(
                """
                SELECT jsonb_typeof(content) AS content_typeof, content, sequence
                FROM messages
                WHERE session_id = $1 AND role = 'assistant'
                """,
                session.session_id,
            )
            assert asst_msg_row is not None
            assert asst_msg_row["content_typeof"] == "object"
            assert asst_msg_row["content"]["headline"] == "Vapor lock probable in auxiliary fuel pump lines"
    finally:
        await db.close()


async def test_session_repository_roundtrip_and_model_messages():
    """Verify get_session roundtrip and save_model_messages on properly encoded rows."""
    db = Database(os.environ["TEST_DATABASE_URL"])
    await db.open()
    try:
        await db.migrate()
        repo = SessionRepository(db.pool)
        owner_id = uuid4()

        profile = {"airframe": "BE36", "engine": "IO-550"}
        session = await repo.create_session(
            owner_id=owner_id,
            domain="aviation",
            title="Bonanza Engine Investigation",
            aircraft_profile=profile,
        )

        cid = uuid4()
        run_id, _ = await repo.create_run(
            session_id=session.session_id,
            owner_id=owner_id,
            mode="EVIDENCE",
            idempotency_key=uuid4(),
            request_text="Check cylinder #3 EGT rise",
            expected_revision=0,
            corpus_ids=[cid],
        )

        receipt_id = uuid4()
        async with db.pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO computed_receipts (
                    receipt_id, run_id, kind, parameters, result, corpus_ids, manifest_sha256, contributing_ids, validator_version
                ) VALUES ($1, $2, 'aggregate', '{}', '{}', '[]', $3, '[]', 'computation/v1')
                """,
                receipt_id,
                run_id,
                "0" * 64,
            )

        sup = ReceiptSupport(kind="aggregate_receipt", receipt_id=receipt_id, result_keys=["egt_mean"])
        claim = Claim(
            claim_id="claim-egt",
            text="EGT rise consistent with partially clogged injector",
            claim_type="historical_problem",
            supports=[sup],
        )
        answer = AnswerEnvelope(
            answer_id=uuid4(),
            run_id=run_id,
            mode="EVIDENCE",
            status="supported_historical",
            headline="Injector nozzle fouling detected",
            claims=[claim],
        )
        board_item = BoardItem(
            item_id=uuid4(),
            column="known",
            text="Injector nozzle fouled on cyl 3",
            origin="historical_log",
            origin_ref="LOG:INJ-3",
            created_revision=0,
            verification_status="source_validated",
            affected_component_ids=["injector_3"],
        )

        await repo.commit_answer_and_state(
            run_id=run_id,
            session_id=session.session_id,
            answer=answer,
            validation_report={"valid": True},
            new_board_items=[board_item],
        )

        # Verify get_session roundtrip
        snapshot = await repo.get_session(session.session_id, owner_id)
        assert snapshot is not None
        assert snapshot.session_id == session.session_id
        assert snapshot.aircraft_profile == profile
        assert len(snapshot.board) == 1
        assert snapshot.board[0].item_id == board_item.item_id
        assert snapshot.board[0].column == "known"
        assert len(snapshot.messages) == 2
        assert snapshot.messages[0]["content"] == {"text": "Check cylinder #3 EGT rise"}
        assert snapshot.messages[1]["content"]["headline"] == "Injector nozzle fouling detected"
        assert len(snapshot.answers) == 1
        assert snapshot.answers[0].answer_id == answer.answer_id
        assert snapshot.answers[0].headline == "Injector nozzle fouling detected"

        # Verify save_model_messages
        transcript = [
            {"role": "user", "content": "What causes EGT rise?"},
            {
                "role": "assistant",
                "content": "",
                "tool_calls": [
                    {
                        "id": "call_inj_1",
                        "type": "function",
                        "function": {"name": "search_records", "arguments": '{"query": "injector"}'},
                    }
                ],
            },
            {
                "role": "tool",
                "tool_call_id": "call_inj_1",
                "name": "search_records",
                "content": '{"results": 1}',
            },
        ]
        await repo.save_model_messages(
            run_id=run_id,
            turn_index=0,
            messages=transcript,
            provider="openai",
            adapter_version="openai/v1",
        )

        async with db.pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT jsonb_typeof(serialized_messages) AS typeof, serialized_messages, provider
                FROM model_messages
                WHERE run_id = $1 AND turn_index = 0
                """,
                run_id,
            )
            assert row is not None
            assert row["typeof"] == "array"
            assert row["provider"] == "openai"
            assert row["serialized_messages"] == transcript
    finally:
        await db.close()


async def test_session_repository_legacy_string_backward_compatibility():
    """Verify that get_session backwards compatibility works for legacy rows with double-encoded JSON strings."""
    db = Database(os.environ["TEST_DATABASE_URL"])
    await db.open()
    try:
        await db.migrate()
        repo = SessionRepository(db.pool)
        owner_id = uuid4()
        session_id = uuid4()
        run_id = uuid4()
        answer_id = uuid4()
        msg_id1 = uuid4()
        msg_id2 = uuid4()

        legacy_profile_dict = {"airframe": "Legacy-172", "registration": "N-LEGACY"}
        legacy_board_list = [
            {
                "item_id": str(uuid4()),
                "column": "reported",
                "text": "Legacy reported issue",
                "origin": "user_report",
                "origin_ref": "REF:LEGACY",
                "created_revision": 0,
                "supersedes": None,
                "verification_status": "user_reported",
                "affected_component_ids": [],
            }
        ]
        legacy_user_content = {"text": "Legacy question about alternator"}
        legacy_answer_dict = {
            "answer_id": str(answer_id),
            "run_id": str(run_id),
            "mode": "EVIDENCE",
            "status": "supported_historical",
            "headline": "Legacy answer headline",
            "claims": [],
            "limitations": [],
            "missing": [],
            "clarification": None,
            "visual_refs": [],
            "allowed_actions": [],
        }

        # Insert rows using to_jsonb(text) which explicitly creates JSONB strings (jsonb_typeof == 'string')
        async with db.pool.acquire() as conn:
            # 1. Legacy session row
            await conn.execute(
                """
                INSERT INTO sessions (
                    session_id, owner_id, title, domain, status, state_revision, aircraft_profile, board
                ) VALUES (
                    $1, $2, 'Legacy Session', 'aviation', 'active', 1,
                    to_jsonb($3::text),
                    to_jsonb($4::text)
                )
                """,
                session_id,
                owner_id,
                json.dumps(legacy_profile_dict),
                json.dumps(legacy_board_list),
            )

            # Confirm they were stored as string type
            s_check = await conn.fetchrow(
                """
                SELECT
                    jsonb_typeof(aircraft_profile) AS p_type,
                    jsonb_typeof(board) AS b_type
                FROM sessions
                WHERE session_id = $1
                """,
                session_id,
            )
            assert s_check["p_type"] == "string"
            assert s_check["b_type"] == "string"

            # 2. Legacy run row
            await conn.execute(
                """
                INSERT INTO runs (
                    run_id, session_id, mode, idempotency_key, request_hash,
                    state_revision, corpus_ids, prompt_version, model_id, status
                ) VALUES (
                    $1, $2, 'EVIDENCE', $3, $4, 0,
                    to_jsonb($5::text),
                    'v1.0', 'deepseek-flash', 'completed'
                )
                """,
                run_id,
                session_id,
                uuid4(),
                "0" * 64,
                json.dumps([str(uuid4())]),
            )

            # 3. Legacy messages
            await conn.execute(
                """
                INSERT INTO messages (message_id, session_id, run_id, sequence, role, source_type, content)
                VALUES ($1, $2, $3, 1, 'user', 'user_input', to_jsonb($4::text))
                """,
                msg_id1,
                session_id,
                run_id,
                json.dumps(legacy_user_content),
            )
            await conn.execute(
                """
                INSERT INTO messages (message_id, session_id, run_id, sequence, role, source_type, content)
                VALUES ($1, $2, $3, 2, 'assistant', 'model_answer', to_jsonb($4::text))
                """,
                msg_id2,
                session_id,
                run_id,
                json.dumps(legacy_answer_dict),
            )

            # Confirm message content stored as string
            m_check = await conn.fetchrow(
                "SELECT jsonb_typeof(content) AS m_type FROM messages WHERE message_id = $1",
                msg_id1,
            )
            assert m_check["m_type"] == "string"

            # 4. Legacy answers
            await conn.execute(
                """
                INSERT INTO answers (answer_id, run_id, source_mode, envelope, validation_report)
                VALUES ($1, $2, 'EVIDENCE', to_jsonb($3::text), to_jsonb($4::text))
                """,
                answer_id,
                run_id,
                json.dumps(legacy_answer_dict),
                json.dumps({"valid": True}),
            )

            # Confirm answer envelope stored as string
            a_check = await conn.fetchrow(
                "SELECT jsonb_typeof(envelope) AS e_type, jsonb_typeof(validation_report) AS v_type FROM answers WHERE answer_id = $1",
                answer_id,
            )
            assert a_check["e_type"] == "string"
            assert a_check["v_type"] == "string"

        # Now get_session should transparently decode legacy double-encoded strings without error
        snapshot = await repo.get_session(session_id, owner_id)
        assert snapshot is not None
        assert snapshot.aircraft_profile == legacy_profile_dict
        assert len(snapshot.board) == 1
        assert str(snapshot.board[0].item_id) == legacy_board_list[0]["item_id"]
        assert snapshot.board[0].column == "reported"
        assert len(snapshot.messages) == 2
        assert snapshot.messages[0]["content"] == legacy_user_content
        assert snapshot.messages[1]["content"]["headline"] == "Legacy answer headline"
        assert len(snapshot.answers) == 1
        assert str(snapshot.answers[0].answer_id) == str(answer_id)
        assert snapshot.answers[0].headline == "Legacy answer headline"
    finally:
        await db.close()
