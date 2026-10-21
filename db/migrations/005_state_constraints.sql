-- State revisions are monotonic nonnegative counters, not client authority.
-- Remove only invalid bootstrap test rows before validating this new constraint.
-- NOT VALID protects new rows immediately; existing rows must be checked by migrations.
ALTER TABLE sessions ADD CONSTRAINT session_revision_nonnegative CHECK(state_revision>=0) NOT VALID;
ALTER TABLE runs ADD CONSTRAINT run_revision_nonnegative CHECK(state_revision>=0);
ALTER TABLE claim_supports ADD CONSTRAINT log_span_nonnull CHECK(kind<>'log_span' OR (span_start IS NOT NULL AND span_end IS NOT NULL));
