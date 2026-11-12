import time
import pytest
import exp5_tools as ex5
from exp5_tools import Arg, Plan, Step, execute, sum_eur


@pytest.fixture(autouse=True)
def fast_tools(monkeypatch):
    monkeypatch.setattr(ex5, 'TOOL_LATENCY', 0.3)


def step(sid, tool, **args):
    return Step(id=sid, why='test', tool=tool,
                args=[Arg(name=key, value=str(value)) for key, value in args.items()])


def test_reference_resolves():
    plan = Plan(steps=[step('s1', 'nearest_airport', town='Vaslui'),
                       step('s2', 'flight_price', origin='@s1', destination='Rome', date='12 May')])
    results = execute(plan, False)
    assert results['s1'] == 'Iasi'
    assert '"price_eur": 142' in results['s2']


def test_parallel_is_faster():
    plan = Plan(steps=[step(f's{i}', 'weather', city=city)
                       for i, city in enumerate(['Rome', 'Barcelona', 'Lisbon'], 1)])
    start = time.perf_counter()
    execute(plan, False)
    sequential = time.perf_counter() - start
    start = time.perf_counter()
    results = execute(plan, True)
    parallel = time.perf_counter() - start
    assert sequential >= 0.85 and parallel < 0.6, (sequential, parallel)
    assert results['s3'] == '21 C, windy'


def test_dependent_step_waits():
    plan = Plan(steps=[step('s2', 'flight_price', origin='@s1', destination='Barcelona', date='12 May'),
                       step('s1', 'nearest_airport', town='Botosani')])
    assert '"price_eur": 156' in execute(plan, True)['s2']


def test_missing_ref_does_not_hang():
    plan = Plan(steps=[step('s1', 'weather', city='@s9')])
    assert 'No weather data' in execute(plan, True)['s1']


def test_invalid_args_are_errors():
    plan = Plan(steps=[step('s1', 'hotel_price', city='Rome', nights='three')])
    assert execute(plan, False)['s1'].startswith('ERROR')


def test_exact_euro_sum():
    assert sum_eur([0.1, 0.2, 19.99]) == '20.29'
    assert sum_eur([]) == '0'
    assert sum_eur([float('nan')]).startswith('ERROR')


def test_cycle_finishes():
    plan = Plan(steps=[step('s1', 'weather', city='@s2'), step('s2', 'weather', city='@s1')])
    results = execute(plan, True)
    assert len(results) == 2
