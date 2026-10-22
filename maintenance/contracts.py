"""maintenance/v1 shared types. Owned by P1; workflow implementation belongs to P2."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Annotated, Any, Literal, Protocol
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field, model_validator

Domain = Literal["aviation", "facility"]
Mode = Literal["EVIDENCE", "HYPOTHESIS", "CHALLENGE", "SENSITIVITY", "DISTINGUISH", "HANDOVER"]
AnswerStatus = Literal[
    "supported_historical",
    "partial_evidence",
    "clarification_needed",
    "insufficient_evidence",
    "retrieval_unavailable",
]
EventType = Literal[
    "run_started",
    "query_interpreted",
    "search_started",
    "search_completed",
    "tool_started",
    "tool_completed",
    "evidence_ready",
    "validation_started",
    "board_updated",
    "answer_validated",
    "run_cancelled",
    "run_failed",
    "done",
]


class Contract(BaseModel):
    model_config = ConfigDict(extra="forbid", validate_assignment=True)


class Mention(Contract):
    value: str
    text: str
    start: int = Field(ge=0)
    end: int = Field(gt=0)
    kind: str


class SearchFilters(Contract):
    component: str | None = None
    symptom: str | None = None


class SearchSpec(Contract):
    query_raw: str = Field(min_length=1, max_length=2000)
    query_normalized: str = ""
    domain: Domain
    corpus_ids: list[UUID] = Field(default_factory=list)
    intent: Literal["fault", "action_history"] = "fault"
    explicit_components: list[Mention] = Field(default_factory=list)
    symptoms: list[Mention] = Field(default_factory=list)
    location_mentions: list[Mention] = Field(default_factory=list)
    number_mentions: list[Mention] = Field(default_factory=list)
    negation_spans: list[Mention] = Field(default_factory=list)
    ambiguous_terms: list[str] = Field(default_factory=list)
    requested_fact_type: str = "historical_cases"
    aircraft_profile_revision: int = Field(default=0, ge=0)
    filters: SearchFilters = Field(default_factory=SearchFilters)
    top_k: int = Field(default=6, ge=1, le=10)
    quality_mode: bool = False
    collapse_duplicates: bool = True

    @model_validator(mode="after")
    def nonblank(self):
        if not self.query_raw.strip():
            raise ValueError("query must not be blank")
        if len(self.corpus_ids) != len(set(self.corpus_ids)):
            raise ValueError("duplicate corpus IDs")
        return self


class ServiceScope(Contract):
    owner_id: UUID
    corpus_ids: list[UUID] = Field(min_length=1)
    session_id: UUID | None = None
    run_id: UUID | None = None


class CorpusManifest(Contract):
    corpus_id: UUID
    domain: Domain
    sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    source_url: str
    terms_note: str
    record_count: int = Field(ge=0)
    distinct_pairs: int = Field(ge=0)
    fields: list[str]
    parser_version: str = "csv/v1"
    normalization_version: str = "reviewed/v1"
    catalog_revision: str = "unreviewed/no-visual-mapping"
    warnings: list[str] = Field(default_factory=list)


class RecordSnapshot(Contract):
    corpus_id: UUID
    record_id: str = Field(pattern=r"^(aviation|facility):[^:]+$")
    source_id: str
    domain: Domain
    csv_row: int = Field(ge=2)
    original_fields: dict[str, str]
    problem_raw: str
    action_raw: str | None
    problem_normalized: str
    action_normalized: str | None
    normalization_version: str = "reviewed/v1"
    annotations: dict[str, Any] = Field(default_factory=dict)
    duplicate_key: str
    source_file_sha256: str
    field_sha256: dict[str, str]
    source_model: str | None = None
    applicability: Literal["unknown", "generic", "applicable", "mismatch"] = "unknown"


class ParsedCorpus(Contract):
    manifest: CorpusManifest
    records: list[RecordSnapshot]


class Compatibility(Contract):
    tier: Literal["direct", "related", "tangential"]
    facts: dict[str, Literal["agreement", "difference", "unknown"]]
    query_mentions: list[Mention] = Field(default_factory=list)
    source_mentions: list[Mention] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)


class SearchHit(Contract):
    corpus_id: UUID
    record_id: str
    rrf_score: float
    channel_ranks: dict[str, int]
    channel_scores: dict[str, float]
    compatibility: Compatibility
    duplicate_ids: list[str]
    duplicate_count: int
    reranker_score: float | None = None
    record_snapshot: RecordSnapshot | None = None


class StageTrace(Contract):
    stage: str
    duration_ms: float
    count_in: int | None = None
    count_out: int | None = None
    details: dict[str, Any] = Field(default_factory=dict)


class SearchTrace(Contract):
    telemetry: dict[str, str] = Field(default_factory=dict)
    stages: list[StageTrace] = Field(default_factory=list)
    stage_timings_ms: dict[str, float] = Field(default_factory=dict)
    stage_counts: dict[str, int] = Field(default_factory=dict)
    original_query: str = ""
    normalized_query: str = ""
    query_mentions: list[Mention] = Field(default_factory=list)


class SearchResult(Contract):
    search_id: UUID = Field(default_factory=uuid4)
    protocol_version: Literal["maintenance/v1"] = "maintenance/v1"
    spec: SearchSpec
    hits: list[SearchHit]
    channels: dict[str, list[str]]
    versions: dict[str, str]
    timings_ms: dict[str, float]
    degraded_branches: list[str] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)
    fixture_only: bool = False
    trace: SearchTrace | None = None


class EvidenceSpan(Contract):
    corpus_id: UUID
    record_id: str
    field: Literal["PROBLEM", "ACTION", "DESCRIPTION"]
    start: int = Field(ge=0)
    end: int = Field(gt=0)
    quote: str
    source_sha256: str = Field(description="SHA256 of decoded raw field encoded as UTF-8")

    @model_validator(mode="after")
    def valid_span(self):
        if self.end <= self.start:
            raise ValueError("empty/reversed source span")
        return self


class SupportSpan(EvidenceSpan):
    kind: Literal["log_span"] = "log_span"
    evidence_id: UUID
    support_kind: Literal["direct_quote", "faithful_paraphrase", "reported_check"] = "direct_quote"


class ReceiptSupport(Contract):
    kind: Literal["aggregate_receipt", "search_comparison"]
    receipt_id: UUID
    result_keys: list[str] = Field(min_length=1)


Support = Annotated[SupportSpan | ReceiptSupport, Field(discriminator="kind")]


class Claim(Contract):
    claim_id: str
    text: str
    claim_type: Literal[
        "historical_problem",
        "historical_action",
        "reported_result",
        "source_difference",
        "count",
        "sensitivity",
    ]
    supports: list[Support] = Field(min_length=1)


class DraftAnswer(Contract):
    proposed_status: AnswerStatus
    findings: list[Claim] = Field(default_factory=list)
    historical_actions: list[Claim] = Field(default_factory=list)
    contrasting_cases: list[Claim] = Field(default_factory=list)
    gap_refs: list[str] = Field(default_factory=list)
    limitation_refs: list[str] = Field(default_factory=list)
    clarification_ref: str | None = None
    component_refs: list[str] = Field(default_factory=list)
    summary: str | None = None
    what_can_be_concluded: list[str] = Field(default_factory=list)
    what_cannot_be_concluded: list[str] = Field(default_factory=list)


class AllowedAction(Contract):
    action: Literal["challenge", "distinguish", "sensitivity", "hypothesis", "handover"]
    parent_answer_id: UUID
    state_revision: int = Field(ge=0)


class AnswerEnvelope(Contract):
    answer_id: UUID
    run_id: UUID
    mode: Mode
    status: AnswerStatus
    headline: str
    claims: list[Claim]
    limitations: list[str] = Field(default_factory=list)
    missing: list[str] = Field(default_factory=list)
    clarification: str | None = None
    visual_refs: list[str] = Field(default_factory=list)
    allowed_actions: list[AllowedAction] = Field(default_factory=list)
    summary: str | None = None
    what_can_be_concluded: list[str] = Field(default_factory=list)
    what_cannot_be_concluded: list[str] = Field(default_factory=list)

    synthesis_evidence_ids: list[UUID] = Field(default_factory=list)
    generation: dict[str, Any] = Field(default_factory=dict)


class HypothesisDraft(Contract):
    possible_explanations: list[str]
    basis: list[str]
    assumptions: list[str]
    information_needed: list[str]
    what_would_weaken_this: list[str]
    limits: list[str]
    historical_claims: list[Claim] = Field(default_factory=list)
    summary: str | None = None
    what_can_be_concluded: list[str] = Field(default_factory=list)
    what_cannot_be_concluded: list[str] = Field(default_factory=list)


class HypothesisEnvelope(HypothesisDraft):
    answer_id: UUID
    run_id: UUID
    parent_answer_id: UUID
    state_revision: int
    mode: Literal["HYPOTHESIS"] = "HYPOTHESIS"
    unverified: Literal[True] = True


class PublicEvent(Contract):
    protocol_version: Literal["maintenance/v1"] = "maintenance/v1"
    run_id: UUID
    sequence: int = Field(ge=1)
    type: EventType
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    data: dict[str, Any]


class BoardItem(Contract):
    item_id: UUID
    column: Literal["known", "reported", "missing"]
    text: str
    origin: Literal["user_report", "historical_log", "verified_document", "schema_gap"]
    origin_ref: str
    created_revision: int = Field(ge=0)
    supersedes: UUID | None = None
    verification_status: Literal["user_reported", "source_validated", "unresolved"]
    affected_component_ids: list[str] = Field(default_factory=list)


class SessionSnapshot(Contract):
    session_id: UUID
    domain: Domain
    title: str
    state_revision: int = Field(ge=0)
    aircraft_profile: dict[str, Any]
    board: list[BoardItem]
    messages: list[dict[str, Any]]
    answers: list[AnswerEnvelope | HypothesisEnvelope]
    active_run_id: UUID | None = None


class ComponentContextEnvelope(Contract):
    component_id: str
    name: str
    explanation: str
    citations: list[dict[str, Any]]
    profile_revision: int
    applicability: Literal["generic", "applicable", "unknown", "mismatch"]
    source_available: bool
    asset_mapping_ids: list[str]
    related_log_ids: list[str]


class MessageRequest(Contract):
    text: str = Field(min_length=1, max_length=10000)
    idempotency_key: UUID
    expected_revision: int = Field(ge=0)
    model: str | None = None
    parameters: dict[str, Any] = Field(default_factory=dict)
    corpus_version: str | None = None


class ActionRequest(Contract):
    action: Literal["challenge", "distinguish", "sensitivity", "hypothesis", "handover"]
    parent_answer_id: UUID
    expected_revision: int = Field(ge=0)
    idempotency_key: UUID
    parameters: dict[str, Any] = Field(default_factory=dict)


class ComputationReceipt(Contract):
    kind: Literal["aggregate", "comparison", "search_comparison"]
    parameters: dict[str, Any]
    result: dict[str, Any]
    corpus_ids: list[UUID]
    manifest_sha256: str
    contributing_ids: list[str]
    validator_version: str = "computation/v1"


class ErrorEnvelope(Contract):
    error: str
    message: str
    retryable: bool = False


class SearchService(Protocol):
    async def search(self, spec: SearchSpec, scope: ServiceScope) -> SearchResult: ...
    async def fetch(self, record_ids: list[str], scope: ServiceScope) -> list[RecordSnapshot]: ...
