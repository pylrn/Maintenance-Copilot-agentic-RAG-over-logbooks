CREATE FUNCTION prevent_immutable_update() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN RAISE EXCEPTION 'immutable source/evidence cannot be updated'; END $$;
CREATE TRIGGER source_records_immutable BEFORE UPDATE OR DELETE ON maintenance_records FOR EACH ROW EXECUTE FUNCTION prevent_immutable_update();
CREATE TRIGGER source_corpus_immutable BEFORE UPDATE OR DELETE ON corpus_versions FOR EACH ROW EXECUTE FUNCTION prevent_immutable_update();
CREATE TRIGGER evidence_immutable BEFORE UPDATE ON evidence_snapshots FOR EACH ROW EXECUTE FUNCTION prevent_immutable_update();
CREATE TRIGGER receipts_immutable BEFORE UPDATE ON computed_receipts FOR EACH ROW EXECUTE FUNCTION prevent_immutable_update();
CREATE TRIGGER events_immutable BEFORE UPDATE ON run_events FOR EACH ROW EXECUTE FUNCTION prevent_immutable_update();
CREATE TRIGGER answers_immutable BEFORE UPDATE ON answers FOR EACH ROW EXECUTE FUNCTION prevent_immutable_update();
CREATE FUNCTION prevent_domain_change() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN IF NEW.domain<>OLD.domain THEN RAISE EXCEPTION 'domain change requires new session'; END IF; RETURN NEW; END $$;
CREATE TRIGGER session_domain_immutable BEFORE UPDATE ON sessions FOR EACH ROW EXECUTE FUNCTION prevent_domain_change();
