from aek.schema import Case, Trace
from aek.checks_json import answer_is_valid_json


def test_valid_plain_json():
    case = Case(id="x", instruction="")
    trace = Trace(case_id="x", final_answer='{"a": 1}')
    ok, score, _ = answer_is_valid_json(case, trace)
    assert ok and score == 1.0


def test_fenced_block():
    trace = Trace(case_id="x",
                  final_answer="Here it is:\n```json\n{\"a\": 1}\n```")
    ok, _, _ = answer_is_valid_json(Case(id="x", instruction=""), trace)
    assert ok


def test_invalid_json():
    trace = Trace(case_id="x", final_answer="not json")
    ok, _, note = answer_is_valid_json(Case(id="x", instruction=""), trace)
    assert not ok
    assert "invalid json" in note
