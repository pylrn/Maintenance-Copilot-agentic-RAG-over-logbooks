"""Regenerate schemas/fixtures from canonical models: python -m contracts.v1.export."""

import asyncio
import hashlib
import inspect
import json
from pathlib import Path
from uuid import uuid4

from pydantic.json_schema import models_json_schema

import maintenance.contracts as c
from contracts.v1.fakes import FixtureSearchService

HERE = Path(__file__).resolve().parent
models = [
    m
    for _, m in inspect.getmembers(c, inspect.isclass)
    if issubclass(m, c.Contract) and m is not c.Contract
]
_, schema = models_json_schema(
    [(m, "validation") for m in models], title="Maintenance v1 shared contracts"
)
schema["x-contract-version"] = "maintenance/v1"
(HERE / "schema.json").write_text(json.dumps(schema, indent=2) + "\n")


async def fixtures():
    service = FixtureSearchService()
    scope = c.ServiceScope(
        owner_id=uuid4(), corpus_ids=[x.manifest.corpus_id for x in service.corpora.values()]
    )
    result = await service.search(c.SearchSpec(query_raw="intake leak", domain="aviation"), scope)
    (HERE / "fixtures/search.json").write_text(result.model_dump_json(indent=2) + "\n")
    snapshot = (await service.fetch(["aviation:DEMO-1"], scope))[0]
    (HERE / "fixtures/record.json").write_text(
        json.dumps({"fixture_only": True, "record": snapshot.model_dump(mode="json")}, indent=2)
        + "\n"
    )
    run = uuid4()
    answer = uuid4()
    span = c.SupportSpan(
        corpus_id=snapshot.corpus_id,
        record_id=snapshot.record_id,
        field="PROBLEM",
        start=0,
        end=len(snapshot.problem_raw),
        quote=snapshot.problem_raw,
        source_sha256=snapshot.field_sha256["PROBLEM"],
        evidence_id=uuid4(),
    )
    envelope = c.AnswerEnvelope(
        answer_id=answer,
        run_id=run,
        mode="EVIDENCE",
        status="supported_historical",
        headline="Synthetic example only",
        claims=[
            c.Claim(
                claim_id="fixture-claim",
                text="The example record reports an intake leak.",
                claim_type="historical_problem",
                supports=[span],
            )
        ],
        limitations=["SYNTHETIC FIXTURE: not a released maintenance answer."],
    )
    (HERE / "fixtures/answer.json").write_text(
        json.dumps({"fixture_only": True, "answer": envelope.model_dump(mode="json")}, indent=2)
        + "\n"
    )
    events = [
        c.PublicEvent(run_id=run, sequence=i, type=t, data={"fixture_only": True})
        for i, t in enumerate(
            [
                "run_started",
                "tool_started",
                "tool_completed",
                "evidence_ready",
                "validation_started",
                "answer_validated",
                "done",
            ],
            1,
        )
    ]
    (HERE / "fixtures/events.json").write_text(
        json.dumps([e.model_dump(mode="json") for e in events], indent=2) + "\n"
    )
    session = c.SessionSnapshot(
        session_id=uuid4(),
        domain="aviation",
        title="Fixture investigation",
        state_revision=1,
        aircraft_profile={},
        board=[],
        messages=[],
        answers=[envelope],
    )
    (HERE / "fixtures/session.json").write_text(
        json.dumps({"fixture_only": True, "session": session.model_dump(mode="json")}, indent=2)
        + "\n"
    )


asyncio.run(fixtures())
(HERE / "manifest.json").write_text(
    json.dumps(
        {
            "protocol_version": "maintenance/v1",
            "status": "P1 implementation baseline; P2 schema review pending",
            "schema_sha256": hashlib.sha256((HERE / "schema.json").read_bytes()).hexdigest(),
            "canonical_python": "maintenance/contracts.py",
        },
        indent=2,
    )
    + "\n"
)
print("Exported shared schema and five marked fixture files.")
