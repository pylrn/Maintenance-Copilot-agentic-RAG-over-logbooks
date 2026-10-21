CREATE TABLE evidence_snapshots (
 evidence_id uuid PRIMARY KEY, run_id uuid NOT NULL REFERENCES runs(run_id) ON DELETE CASCADE,
 corpus_id uuid NOT NULL, record_id text NOT NULL,
 field text NOT NULL CHECK(field IN ('PROBLEM','ACTION','DESCRIPTION')),
 raw_text text NOT NULL, text_sha256 char(64) NOT NULL, fetched_at timestamptz NOT NULL DEFAULT now(),
 FOREIGN KEY(corpus_id,record_id) REFERENCES maintenance_records(corpus_id,record_id),
 UNIQUE(run_id,corpus_id,record_id,field)
);
CREATE TABLE computed_receipts (
 receipt_id uuid PRIMARY KEY, run_id uuid NOT NULL REFERENCES runs(run_id) ON DELETE CASCADE,
 kind text NOT NULL CHECK(kind IN ('aggregate','comparison','search_comparison')),
 parameters jsonb NOT NULL, result jsonb NOT NULL, corpus_ids jsonb NOT NULL,
 manifest_sha256 char(64) NOT NULL, contributing_ids jsonb NOT NULL,
 validator_version text NOT NULL, created_at timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE claim_supports (
 answer_id uuid NOT NULL REFERENCES answers(answer_id) ON DELETE CASCADE,
 claim_id text NOT NULL, support_index integer NOT NULL CHECK(support_index>=0),
 kind text NOT NULL CHECK(kind IN ('log_span','aggregate_receipt','search_comparison')),
 evidence_id uuid REFERENCES evidence_snapshots(evidence_id) ON DELETE CASCADE,
 receipt_id uuid REFERENCES computed_receipts(receipt_id) ON DELETE CASCADE,
 span_start integer, span_end integer, quote text, result_keys jsonb,
 PRIMARY KEY(answer_id,claim_id,support_index),
 CHECK ((kind='log_span' AND evidence_id IS NOT NULL AND receipt_id IS NULL AND span_start>=0 AND span_end>span_start AND quote IS NOT NULL) OR (kind IN ('aggregate_receipt','search_comparison') AND receipt_id IS NOT NULL AND evidence_id IS NULL AND span_start IS NULL AND span_end IS NULL AND result_keys IS NOT NULL))
);
CREATE TABLE model_messages (
 run_id uuid NOT NULL REFERENCES runs(run_id) ON DELETE CASCADE, turn_index integer NOT NULL CHECK(turn_index>=0),
 serialized_messages jsonb NOT NULL, adapter_version text NOT NULL, provider text NOT NULL,
 PRIMARY KEY(run_id,turn_index)
);
CREATE TABLE hypothesis_requests (
 request_id uuid PRIMARY KEY, owner_id uuid NOT NULL, session_id uuid NOT NULL REFERENCES sessions(session_id) ON DELETE CASCADE,
 parent_answer_id uuid NOT NULL REFERENCES answers(answer_id) ON DELETE CASCADE,
 parent_hash char(64) NOT NULL, state_revision integer NOT NULL, requested_at timestamptz NOT NULL DEFAULT now(),
 expires_at timestamptz NOT NULL, consumed_run_id uuid UNIQUE REFERENCES runs(run_id) ON DELETE SET NULL,
 mode_label text NOT NULL DEFAULT 'HYPOTHESIS' CHECK(mode_label='HYPOTHESIS')
);
CREATE TABLE session_summaries (
 session_id uuid NOT NULL REFERENCES sessions(session_id) ON DELETE CASCADE,
 through_sequence bigint NOT NULL, typed_summary jsonb NOT NULL, source_message_ids jsonb NOT NULL, prompt_version text NOT NULL,
 PRIMARY KEY(session_id,through_sequence)
);
CREATE TABLE attachments (
 attachment_id uuid PRIMARY KEY, owner_id uuid NOT NULL, session_id uuid NOT NULL REFERENCES sessions(session_id) ON DELETE CASCADE,
 content_hash char(64) NOT NULL, mime text NOT NULL, extraction_status text NOT NULL,
 storage_key text NOT NULL, trust_type text NOT NULL DEFAULT 'user_input' CHECK(trust_type='user_input'),
 extracted_text text, created_at timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE feedback (
 feedback_id uuid PRIMARY KEY, answer_id uuid NOT NULL REFERENCES answers(answer_id) ON DELETE CASCADE,
 owner_id uuid NOT NULL, reason text NOT NULL, source_ids jsonb NOT NULL DEFAULT '[]', user_note text,
 review_status text NOT NULL DEFAULT 'pending', created_at timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE pinned_evidence (
 session_id uuid NOT NULL REFERENCES sessions(session_id) ON DELETE CASCADE,
 corpus_id uuid NOT NULL, record_id text NOT NULL, pinned_at timestamptz NOT NULL DEFAULT now(), user_note text,
 PRIMARY KEY(session_id,corpus_id,record_id), FOREIGN KEY(corpus_id,record_id) REFERENCES maintenance_records(corpus_id,record_id)
);
CREATE INDEX runs_session_created ON runs(session_id,created_at DESC);
CREATE INDEX evidence_run ON evidence_snapshots(run_id);
CREATE INDEX searches_run ON search_runs(run_id);
ALTER TABLE run_events ADD CHECK(sequence>0);
ALTER TABLE messages ADD CHECK(sequence>0);
ALTER TABLE run_events ADD CHECK(event_type IN ('run_started','query_interpreted','search_started','search_completed','tool_started','tool_completed','evidence_ready','validation_started','board_updated','answer_validated','run_cancelled','run_failed','done'));
