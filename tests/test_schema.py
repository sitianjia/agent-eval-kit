from aek.schema import Case, Trace, Step, ToolCall


def test_trace_aggregates():
    t = Trace(case_id="x")
    t.steps.append(Step(role="user", content="hi"))
    t.steps.append(Step(role="assistant", tool_calls=[
        ToolCall(name="add", arguments={"a": 1, "b": 2}),
        ToolCall(name="mul", arguments={"a": 3, "b": 4}),
    ]))
    assert t.n_tool_calls() == 2
    assert t.tool_names() == ["add", "mul"]


def test_step_to_dict_omits_empty():
    s = Step(role="assistant", content="ok")
    d = s.to_dict()
    assert "tool_calls" not in d
    assert "tool_call_id" not in d
