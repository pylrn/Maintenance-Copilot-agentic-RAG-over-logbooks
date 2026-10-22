CREATE EXTENSION IF NOT EXISTS vector;
CREATE TABLE corpus_versions (
  corpus_id uuid PRIMARY KEY,
  domain text NOT NULL CHECK (domain IN ('aviation','facility')),
  source_url text NOT NULL,
  sha256 char(64) NOT NULL,
  record_count integer NOT NULL CHECK (record_count >= 0),
  terms_note text NOT NULL,
  manifest jsonb NOT NULL,
  imported_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE(domain, sha256)
);
CREATE TABLE maintenance_records (
  corpus_id uuid NOT NULL REFERENCES corpus_versions(corpus_id),
  record_id text NOT NULL,
  source_id text NOT NULL,
  csv_row integer NOT NULL,
  original_fields jsonb NOT NULL,
  problem_raw text NOT NULL,
  action_raw text,
  problem_normalized text NOT NULL,
  action_normalized text,
  normalization_version text NOT NULL,
  annotations jsonb NOT NULL DEFAULT '{}'::jsonb,
  duplicate_key char(64) NOT NULL,
  source_model text,
  PRIMARY KEY(corpus_id, record_id)
);
CREATE TABLE record_embeddings (
  corpus_id uuid NOT NULL,
  record_id text NOT NULL,
  representation text NOT NULL CHECK (representation IN ('problem','problem_action')),
  embedding_model text NOT NULL,
  model_revision text NOT NULL,
  embedding vector(384) NOT NULL,
  document_sha256 char(64) NOT NULL,
  PRIMARY KEY(corpus_id, record_id, representation, embedding_model, model_revision),
  FOREIGN KEY(corpus_id,record_id) REFERENCES maintenance_records(corpus_id,record_id)
);
CREATE TABLE sessions (
  session_id uuid PRIMARY KEY,
  owner_id uuid NOT NULL,
  title text NOT NULL DEFAULT 'New investigation',
  domain text NOT NULL CHECK (domain IN ('aviation','facility')),
  status text NOT NULL DEFAULT 'active',
  state_revision integer NOT NULL DEFAULT 0,
  aircraft_profile jsonb NOT NULL DEFAULT '{}'::jsonb,
  board jsonb NOT NULL DEFAULT '{"known":[],"reported":[],"missing":[]}'::jsonb,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  archived_at timestamptz
);
CREATE TABLE runs (
  run_id uuid PRIMARY KEY,
  session_id uuid NOT NULL REFERENCES sessions(session_id) ON DELETE CASCADE,
  parent_answer_id uuid,
  mode text NOT NULL CHECK (mode IN ('EVIDENCE','HYPOTHESIS','CHALLENGE','SENSITIVITY','DISTINGUISH','HANDOVER')),
  idempotency_key uuid NOT NULL,
  request_hash char(64) NOT NULL,
  state_revision integer NOT NULL,
  corpus_ids jsonb NOT NULL,
  prompt_version text NOT NULL,
  model_id text NOT NULL,
  status text NOT NULL CHECK (status IN ('queued','running','validating','completed','cancelled','failed')),
  lease_owner text,
  lease_expires_at timestamptz,
  cancel_requested_at timestamptz,
  created_at timestamptz NOT NULL DEFAULT now(),
  completed_at timestamptz,
  UNIQUE(session_id,idempotency_key)
);
CREATE TABLE run_events (
  run_id uuid NOT NULL REFERENCES runs(run_id) ON DELETE CASCADE,
  sequence bigint NOT NULL,
  event_type text NOT NULL,
  public_payload jsonb NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY(run_id,sequence)
);
CREATE TABLE messages (
  message_id uuid PRIMARY KEY,
  session_id uuid NOT NULL REFERENCES sessions(session_id) ON DELETE CASCADE,
  run_id uuid REFERENCES runs(run_id) ON DELETE CASCADE,
  sequence bigint NOT NULL,
  role text NOT NULL,
  source_type text NOT NULL,
  content jsonb NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE(session_id,sequence)
);
CREATE TABLE search_runs (
  search_id uuid PRIMARY KEY,
  run_id uuid NOT NULL REFERENCES runs(run_id) ON DELETE CASCADE,
  query_raw text NOT NULL,
  search_spec jsonb NOT NULL,
  pipeline_version text NOT NULL,
  channel_results jsonb NOT NULL,
  final_results jsonb NOT NULL,
  timings jsonb NOT NULL,
  limitations jsonb NOT NULL DEFAULT '[]'::jsonb
);
CREATE TABLE answers (
  answer_id uuid PRIMARY KEY,
  run_id uuid NOT NULL UNIQUE REFERENCES runs(run_id) ON DELETE CASCADE,
  source_mode text NOT NULL,
  envelope jsonb NOT NULL,
  validation_report jsonb NOT NULL,
  released_at timestamptz NOT NULL DEFAULT now()
);
ALTER TABLE runs ADD CONSTRAINT runs_parent_answer_fk
  FOREIGN KEY(parent_answer_id) REFERENCES answers(answer_id) ON DELETE SET NULL;
CREATE INDEX sessions_owner_updated ON sessions(owner_id,updated_at DESC);
CREATE INDEX records_duplicate ON maintenance_records(corpus_id,duplicate_key);
CREATE UNIQUE INDEX one_live_run_per_session ON runs(session_id)
  WHERE status IN ('queued','running','validating');