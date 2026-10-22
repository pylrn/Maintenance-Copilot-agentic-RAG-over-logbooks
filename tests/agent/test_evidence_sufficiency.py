from uuid import uuid4

import pytest

from maintenance.evidence_sufficiency import supporting_evidence


def evidence(*problems):
    result = {}
    for i, problem in enumerate(problems):
        result[uuid4()] = {"record_id": str(i), "field": "PROBLEM", "raw_text": problem}
        result[uuid4()] = {"record_id": str(i), "field": "ACTION", "raw_text": "REPLACED PART."}
    return result


@pytest.mark.parametrize('query,problem', [
    ('CYL #2 intake leak', 'CYL #2 INTAKE LEAKING.'),
    ('baffle crack', 'BAFFLE CRACKED.'),
    ('baffle cracking', 'BAFFLE CRACKED.'),
    ('battery flat', 'BATTERY FLAT.'),
])
def test_direct_problem_matches_keep_paired_actions(query, problem):
    source = evidence(problem)
    assert supporting_evidence(query, source) == source


@pytest.mark.parametrize('query,problems', [
    ('Right main gear brake pedal feels soft and spongy', ['LEFT BRAKE LININGS WORN.']),
    ('CYL #99 intake leak', ['CYL #2 INTAKE LEAKING.']),
    ('right intake leak', ['LEFT INTAKE LEAKING.']),
    ('right intake leak', ['INTAKE LEAKING.']),
    ('right intake leak', ['RIGHT INTAKE LOOSE.', 'LEFT INTAKE LEAKING.']),
    ('intake leak', ['NO INTAKE LEAK.']),
    ('quantum stabilizer resonance', ['INTAKE LEAKING.']),
    ('baffle crack with unfamiliar actuator failure', ['BAFFLE CRACKED.']),
    ('intake leak and unknown sensor malfunction', ['INTAKE LEAKING.']),
    ('intake leak', ['INTAKE REPLACED.']),
])
def test_partial_conflicting_and_unknown_complaints_abstain(query, problems):
    assert supporting_evidence(query, evidence(*problems)) == {}


def test_only_matching_record_actions_are_allowed():
    source = evidence('INTAKE LEAKING.', 'BRAKE LOOSE.')
    selected = supporting_evidence('intake leak', source)
    assert {v['record_id'] for v in selected.values()} == {'0'}
    assert len(selected) == 2


def test_explicit_abstention_cannot_be_overridden_by_nonempty_candidates():
    from maintenance.answer_rendering import render_extractive_answer
    answer = render_extractive_answer(run_id=uuid4(), mode="EVIDENCE", query_raw="brake soft",
        fetched_evidence=evidence("LEFT BRAKE WORN."), state_revision=0,
        status="insufficient_evidence")
    assert answer.status == "insufficient_evidence"
    assert not answer.claims
    assert not answer.visual_refs
