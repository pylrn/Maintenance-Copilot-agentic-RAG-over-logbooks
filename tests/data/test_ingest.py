import hashlib

import pytest

from maintenance.ingest.aviation import parse_aviation
from maintenance.ingest.facility import parse_facility
from maintenance.ingest.normalize import normalize


def test_raw_text_bom_quoted_newline_and_duplicate_rows_survive():
    raw = '\ufeffIDENT,PROBLEM,ACTION\r\n1,"CYL #2 intake leaking\nNO CRACK",REPL GSKT\r\n2,"CYL #2 intake leaking\nNO CRACK",REPL GSKT\r\n'.encode()
    corpus = parse_aviation(raw)
    assert len(corpus.records) == 2
    assert corpus.records[0].problem_raw == "CYL #2 intake leaking\nNO CRACK"
    assert corpus.records[0].record_id == "aviation:1"
    assert corpus.records[0].duplicate_key == corpus.records[1].duplicate_key
    assert corpus.manifest.sha256 == hashlib.sha256(raw).hexdigest()
    assert corpus.manifest.distinct_pairs == 1
    assert parse_aviation(raw).manifest.corpus_id == corpus.manifest.corpus_id


@pytest.mark.parametrize(
    "raw",
    [
        b"ID,PROBLEM,ACTION\n1,a,b",
        b"IDENT,PROBLEM,ACTION\n1,a,b\n1,c,d",
        b"IDENT,PROBLEM,ACTION\n,a,b",
        b"IDENT,PROBLEM,ACTION\n1,a,b,extra",
    ],
)
def test_invalid_source_is_rejected(raw):
    with pytest.raises(ValueError):
        parse_aviation(raw)


def test_checksum_mismatch_is_not_silently_imported():
    with pytest.raises(ValueError, match="checksum"):
        parse_aviation(b"IDENT,PROBLEM,ACTION\n1,a,b", expected_sha256="0" * 64)


def test_expansion_preserves_negation_number_laterality_and_part():
    assert (
        normalize("CYL #2 NO LEAK R/H P/N 12-34 GSKT", "aviation")
        == "cylinder #2 no leak r/h p/n 12-34 gasket"
    )
    assert normalize("CYLINDER", "aviation") == "cylinder"
    assert normalize("cyl", "facility") == "cyl"


def test_facility_never_invents_action_and_keeps_literal_nan():
    raw = b"WORK_ID,SITE_ID,DATE_REQUESTED,PROB_TYPE,DATE_COMPLETED,DESCRIPTION\n1,NAN,12/27/18,H,12/27/18,Leak\n"
    row = parse_facility(raw).records[0]
    assert row.action_raw is None
    assert row.original_fields["SITE_ID"] == "NAN"
    assert row.annotations["site_uncertain"] is True
    assert row.annotations["date_requested"] == "2018-12-27"


def test_facility_explicit_midnight_format_is_accepted():
    raw = b"WORK_ID,SITE_ID,DATE_REQUESTED,PROB_TYPE,DATE_COMPLETED,DESCRIPTION\n1,A,12/27/18 0:00,H,12/27/18 0:00,Leak\n"
    assert parse_facility(raw).records[0].annotations["date_requested"] == "2018-12-27"


def test_suspected_truncation_is_flagged_without_completing_text():
    problem = "X" * 60
    c = parse_aviation(("IDENT,PROBLEM,ACTION\n1," + problem + ",REPL\n").encode())
    assert c.records[0].problem_raw == problem
    assert c.records[0].annotations["possible_truncation_fields"] == ["PROBLEM"]
