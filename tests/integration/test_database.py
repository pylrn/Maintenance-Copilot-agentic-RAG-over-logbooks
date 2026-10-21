import os
from uuid import uuid4

import asyncpg
import pytest

from maintenance.db import Database
from maintenance.ingest.aviation import parse_aviation

pytestmark = pytest.mark.skipif(
    not os.getenv("TEST_DATABASE_URL"), reason="isolated PostgreSQL required"
)


async def test_migrations_ingest_atomicity_and_immutable_sources():
    db = Database(os.environ["TEST_DATABASE_URL"])
    await db.open()
    try:
        assert await db.migrate() == []  # test setup applies migrations first
        c = parse_aviation(b"IDENT,PROBLEM,ACTION\nTEST1,INTAKE LEAK,REPLACED GASKET\n")
        await db.ingest(c)
        await db.ingest(c)
        loaded = await db.load_corpora([c.manifest.corpus_id])
        assert loaded[0] == c
        async with db.pool.acquire() as conn:
            with pytest.raises(asyncpg.RaiseError, match="immutable"):
                await conn.execute(
                    "UPDATE maintenance_records SET problem_raw='tampered' WHERE corpus_id=$1",
                    c.manifest.corpus_id,
                )
    finally:
        await db.close()


async def test_one_live_run_and_owner_lookup():
    db = Database(os.environ["TEST_DATABASE_URL"])
    await db.open()
    try:
        sid = uuid4()
        oid = uuid4()
        await db.pool.execute(
            "INSERT INTO sessions(session_id,owner_id,domain) VALUES($1,$2,$3)",
            sid,
            oid,
            "aviation",
        )
        from maintenance.auth import require_session_owner

        assert (await require_session_owner(db.pool, sid, oid))["session_id"] == sid
        from fastapi import HTTPException

        with pytest.raises(HTTPException):
            await require_session_owner(db.pool, sid, uuid4())
        sql = "INSERT INTO runs(run_id,session_id,mode,idempotency_key,request_hash,state_revision,corpus_ids,prompt_version,model_id,status) VALUES($1,$2,'EVIDENCE',$3,$4,0,'[]','v1','test','queued')"
        await db.pool.execute(sql, uuid4(), sid, uuid4(), "0" * 64)
        with pytest.raises(asyncpg.UniqueViolationError):
            await db.pool.execute(sql, uuid4(), sid, uuid4(), "1" * 64)
    finally:
        await db.close()


async def test_archived_version_record_lookup_and_receipt_span_constraints():
    db = Database(os.environ["TEST_DATABASE_URL"])
    await db.open()
    try:
        from maintenance.contracts import ServiceScope
        from maintenance.retrieval.records import RecordService

        c = parse_aviation(b"IDENT,PROBLEM,ACTION\nARCHIVE1,OLD INTAKE LEAK,REPL GSKT\n")
        await db.ingest(c)
        scope = ServiceScope(owner_id=uuid4(), corpus_ids=[c.manifest.corpus_id])
        found = await RecordService(db).fetch(["aviation:ARCHIVE1"], scope)
        assert found[0].problem_raw == "OLD INTAKE LEAK"
        with pytest.raises(LookupError):
            await RecordService(db).fetch(
                ["aviation:ARCHIVE1"], ServiceScope(owner_id=uuid4(), corpus_ids=[uuid4()])
            )
    finally:
        await db.close()


async def test_negative_revisions_are_rejected():
    db = Database(os.environ["TEST_DATABASE_URL"])
    await db.open()
    try:
        with pytest.raises(asyncpg.CheckViolationError):
            await db.pool.execute(
                "INSERT INTO sessions(session_id,owner_id,domain,state_revision) VALUES($1,$2,'aviation',-1)",
                uuid4(),
                uuid4(),
            )
    finally:
        await db.close()
