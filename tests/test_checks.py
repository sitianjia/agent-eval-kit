from aek.schema import Case, Trace, Step, ToolCall
from aek.checks import (answer_matches, used_expected_tools,
                        no_failed_tool_calls, under_n_steps)


def _case(**kw):
    return Case(id="t", instruction="", **kw)


def _trace(answer="", tool_names=(), errors=False, n_assistant=1):
    t = Trace(case_id="t", final_answer=answer)
    for n in tool_names:
        t.steps.append(Step(role="assistant",
                            tool_calls=[ToolCall(name=n)]))
        t.steps.append(Step(role="tool",
                            content="ERROR: boom" if errors else "ok"))
    for _ in range(n_assistant - len(tool_names)):
        t.steps.append(Step(role="assistant", content=""))
    return t


def test_answer_matches_regex():
    case = _case(expected_answer_pattern=r"4\d")
    ok, _, _ = answer_matches(case, _trace(answer="The answer is 42"))
    assert ok


def test_used_expected_tools_unordered():
    case = _case(expected_tools=["a", "b"])
    ok, _, _ = used_expected_tools(case, _trace(tool_names=["b", "a"]))
    assert ok


def test_used_expected_tools_ordered():
    case = _case(expected_tools=["a", "b"])
    ok_a, _, _ = used_expected_tools(case, _trace(tool_names=["a", "b"]),
                                     ordered=True)
    ok_b, _, _ = used_expected_tools(case, _trace(tool_names=["b", "a"]),
                                     ordered=True)
    assert ok_a and not ok_b


def test_no_failed_tool_calls_passes():
    ok, _, _ = no_failed_tool_calls(_case(), _trace(tool_names=["a"]))
    assert ok


def test_no_failed_tool_calls_catches_errors():
    ok, _, _ = no_failed_tool_calls(_case(),
                                    _trace(tool_names=["a"], errors=True))
    assert not ok


def test_under_n_steps():
    ok, _, _ = under_n_steps(_case(), _trace(n_assistant=3), n=5)
    assert ok
    ok, _, _ = under_n_steps(_case(), _trace(n_assistant=8), n=5)
    assert not ok
