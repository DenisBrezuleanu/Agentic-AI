from types import SimpleNamespace
import agent_core as core


def test_execute_tool_success_and_errors():
    def double(x: int) -> int:
        return x * 2
    def crash() -> str:
        raise RuntimeError('boom')
    tools = {'double': double, 'crash': crash}
    assert core.execute_tool(tools, 'double', {'x': 3}) == '6'
    assert 'Unknown tool' in core.execute_tool(tools, 'unknown', {})
    assert 'Bad arguments' in core.execute_tool(tools, 'double', {})
    assert 'crash failed' in core.execute_tool(tools, 'crash', {})


def fake_response(calls=None, answer='', tokens=100):
    return SimpleNamespace(
        function_calls=calls or [],
        text=answer,
        candidates=[SimpleNamespace(content=SimpleNamespace(parts=[]))],
        usage_metadata=SimpleNamespace(prompt_token_count=tokens),
    )


def fake_call(name='sample', args=None, call_id='id-1'):
    return SimpleNamespace(name=name, args=args or {}, id=call_id)


def test_multi_tool_calls_one_response_and_history(monkeypatch):
    sent = []
    responses = [fake_response([fake_call('sample', {'value': 2}, 'a'),
                                fake_call('sample', {'value': 4}, 'b')]),
                 fake_response(answer='done', tokens=150)]
    def llm(messages, config):
        sent.append(list(messages))
        return responses.pop(0)
    monkeypatch.setattr(core, 'call_llm', llm)
    def sample(value: int) -> int:
        """Double a number.

        Args:
            value: Number.
        """
        return value * 2
    result = core.run_agent('do', [sample], 'system', verbose=False)
    assert result.answer == 'done'
    assert result.steps == 2 and result.total_prompt_tokens == 250
    assert len(sent[1]) == 3
    assert len(sent[1][-1].parts) == 2
    assert [p.function_response.id for p in sent[1][-1].parts] == ['a', 'b']


def test_denied_write_does_not_run(monkeypatch):
    called = []
    responses = [fake_response([fake_call('write', {'value': 'x'})]), fake_response(answer='rejected')]
    monkeypatch.setattr(core, 'call_llm', lambda messages, config: responses.pop(0))
    def write(value: str) -> str:
        """Write a value.

        Args:
            value: Value.
        """
        called.append(value)
        return 'ok'
    result = core.run_agent('do', [write], 'system', requires_approval=frozenset({'write'}),
                            approver=lambda name, args: core.Decision(False, feedback='not allowed'), verbose=False)
    assert result.stop_reason == 'done' and called == []


def test_stuck_after_three_identical_calls(monkeypatch):
    monkeypatch.setattr(core, 'call_llm', lambda messages, config: fake_response([fake_call('check')]))
    def check() -> str:
        """Run a check."""
        return 'ok'
    result = core.run_agent('do', [check], 'system', max_steps=5, verbose=False)
    assert result.stop_reason == 'stuck' and result.steps == 3


def test_budget_stop(monkeypatch):
    monkeypatch.setattr(core, 'call_llm', lambda messages, config: fake_response([fake_call('check')]))
    def check() -> str:
        """Run a check."""
        return 'ok'
    result = core.run_agent('do', [check], 'system', max_steps=1, verbose=False)
    assert result.stop_reason == 'max_steps'
