import json
from datetime import datetime
import re
import statistics
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from decimal import Decimal, InvalidOperation
from typing import Literal
from pydantic import BaseModel, Field
from llm import ask

TOOL_LATENCY = 1.0
TOOL_WAIT = [0.0]
FLIGHTS = {('Iasi', 'Rome'): 142, ('Iasi', 'Barcelona'): 118,
           ('Iasi', 'Bucharest'): 39, ('Bucharest', 'Lisbon'): 167,
           ('Suceava', 'Rome'): 131, ('Suceava', 'Barcelona'): 156}
HOTEL_PER_NIGHT = {'Rome': 96, 'Barcelona': 121, 'Lisbon': 74}
WEATHER = {'Rome': '24 C, sunny', 'Barcelona': '22 C, cloudy', 'Lisbon': '21 C, windy'}
NEAREST_AIRPORT = {'Vaslui': 'Iasi', 'Botosani': 'Suceava', 'Iasi': 'Iasi'}


def _city(name):
    return re.sub(r'\s*\(.*?\)', '', name).strip().title()


def _wait():
    time.sleep(TOOL_LATENCY)
    TOOL_WAIT[0] += TOOL_LATENCY


def nearest_airport(town: str) -> str:
    """Find the airport city for a Romanian town without an airport, e.g. Vaslui.

    Args:
        town: A town without an airport.
    """
    _wait()
    return NEAREST_AIRPORT.get(_city(town), f'Unknown town {town}.')


def flight_price(origin: str, destination: str, date: str) -> str:
    """Cheapest one-way flight for one adult, in EUR. Use tools for current prices.

    Args:
        origin: Departure city.
        destination: Arrival city.
        date: Flight date, e.g. 12 May.
    """
    _wait()
    price = FLIGHTS.get((_city(origin), _city(destination)))
    if price is None:
        if _city(destination) == 'Lisbon':
            return 'No direct flight Iasi-Lisbon. Connect via Bucharest: price Iasi->Bucharest and Bucharest->Lisbon.'
        return f'No flights found {origin}->{destination}.'
    return json.dumps({'route': f'{origin}->{destination}', 'date': date, 'price_eur': price})


def hotel_price(city: str, nights: int) -> str:
    """Total hotel room price in EUR for a central 3-star double room.

    Args:
        city: Destination city.
        nights: Number of nights.
    """
    _wait()
    per_night = HOTEL_PER_NIGHT.get(_city(city))
    if per_night is None:
        return f'No hotels found in {city}.'
    return json.dumps({'city': city, 'nights': int(nights), 'total_eur': per_night * int(nights)})


def weather(city: str) -> str:
    """Look up the current weather in a city.

    Args:
        city: City for the weather lookup.
    """
    _wait()
    return WEATHER.get(_city(city), f'No weather data for {city}.')


def sum_eur(amounts: list[float]) -> str:
    """Add EUR amounts exactly using decimal arithmetic. Use this tool for totals.

    Args:
        amounts: List of numeric prices in EUR to sum.
    """
    try:
        total = sum((Decimal(str(amount)) for amount in amounts), Decimal('0'))
        if not total.is_finite():
            raise ValueError('Amount must be finite')
        return str(total)
    except (TypeError, ValueError, InvalidOperation) as e:
        return f'ERROR: invalid EUR amount: {e}'


TOOLS = {fn.__name__: fn for fn in (nearest_airport, flight_price, hotel_price, weather)}
QUESTIONS = {
    1: ('From Iasi on 12 May: is Rome or Barcelona cheaper for one person, flight plus 3 hotel nights?', '430'),
    2: ('What is the weather right now in Rome, Barcelona and Lisbon?', 'windy'),
    3: ('What does it cost one person to get from Iasi to Lisbon on 12 May, plus 3 hotel nights?', '428'),
    4: ('I live in Vaslui. On 12 May, is it cheaper to fly from my nearest airport to Rome or to Barcelona?', '118'),
}
SYSTEM = (f'You are a travel assistant. Today is {datetime.now().astimezone().date().isoformat()}. '
          'Obtain every price and weather report with tools, never guess numerical facts. '
          'When a year is missing, use the next occurrence of that date after today; never use a past date.')
VERBOSE = '--verbose' in sys.argv


class Arg(BaseModel):
    name: str
    value: str = Field(description='Literal argument or @s1 for a previous single-value result')


class Step(BaseModel):
    id: str
    why: str
    tool: Literal['nearest_airport', 'flight_price', 'hotel_price', 'weather']
    args: list[Arg]


class Plan(BaseModel):
    steps: list[Step]


PLANNER = (SYSTEM + ' Write ALL tool calls before execution. Tools: '
           'nearest_airport(town) only for towns without an airport, '
           'flight_price(origin,destination,date), hotel_price(city,nights), weather(city). '
           'Give step ids s1, s2, ...; @s1 refers to a previous step returning one string. '
           'When a flight is unavailable, your fixed plan cannot dynamically adapt; include contingency routes '
           'if the question needs them.')
SOLVER = 'Answer using ONLY the tool evidence. If evidence is incomplete, state what is missing.'
REF = re.compile(r'@s\d+')


def run_step(step: Step, results: dict[str, str]) -> str:
    args = {arg.name: REF.sub(lambda m: results.get(m.group()[1:], m.group()), arg.value)
            for arg in step.args}
    try:
        return TOOLS[step.tool](**args)
    except Exception as e:
        return f'ERROR: {step.tool} failed: {type(e).__name__}: {e}'


def execute(plan: Plan, parallel: bool) -> dict[str, str]:
    results = {}
    pending = list(plan.steps)
    while pending:
        ready = [step for step in pending if all(ref[1:] in results
                 for arg in step.args for ref in REF.findall(arg.value))]
        if not ready:
            ready = [pending[0]]
        if parallel and len(ready) > 1:
            with ThreadPoolExecutor(max_workers=min(len(ready), 16)) as pool:
                outputs = list(pool.map(lambda step: run_step(step, results), ready))
            results.update(zip((step.id for step in ready), outputs))
            pending = [step for step in pending if step not in ready]
        else:
            step = ready[0]
            results[step.id] = run_step(step, results)
            pending.remove(step)
    return results


def mode_loop(question):
    from agent_core import run_agent
    tools = list(TOOLS.values())
    system = SYSTEM
    if '--sum' in sys.argv:
        tools.append(sum_eur)
        system += ' Never do addition yourself: use sum_eur with individual numeric price values.'
    TOOL_WAIT[0] = 0.0
    reply = run_agent(question, tools=tools, system_instruction=system, max_steps=8, verbose=VERBOSE)
    return reply.answer, reply.steps, reply.total_prompt_tokens, TOOL_WAIT[0]


def mode_plan(question, parallel):
    planned = ask(question, system=PLANNER, schema=Plan)
    if planned.parsed is None:
        raise RuntimeError('Model did not return a valid plan')
    start = time.perf_counter()
    results = execute(planned.parsed, parallel)
    tool_seconds = time.perf_counter() - start
    lines = [f'{step.id} = {step.tool}({", ".join(f"{arg.name}={arg.value}" for arg in step.args)}) -> {results[step.id]}'
             for step in planned.parsed.steps]
    if VERBOSE:
        print('\n'.join(lines))
    solved = ask(f'Question: {question}\nEvidence:\n' + '\n'.join(lines), system=SOLVER)
    return solved.text, 2, planned.in_tokens + solved.in_tokens, tool_seconds


MODES = {'loop': mode_loop, 'plan': lambda q: mode_plan(q, False),
         'parallel': lambda q: mode_plan(q, True)}


if __name__ == '__main__':
    arguments = [arg for arg in sys.argv[1:] if arg not in ('--verbose', '--sum')]
    runs = 1
    if '--runs' in arguments:
        i = arguments.index('--runs')
        runs = int(arguments[i + 1])
        del arguments[i:i + 2]
    modes = [arguments[0]] if arguments else list(MODES)
    questions = [int(arguments[1])] if len(arguments) > 1 else list(QUESTIONS)
    print('| question | mode | correct | LLM calls | input tokens | tool seconds | total seconds |')
    print('|---|---|---|---:|---:|---:|---:|')
    for index in questions:
        question, expected = QUESTIONS[index]
        for mode in modes:
            rows = []
            for _ in range(runs):
                start = time.perf_counter()
                try:
                    answer, calls, tokens, tool_s = MODES[mode](question)
                except Exception as e:
                    answer, calls, tokens, tool_s = str(e), 0, 0, 0
                good = expected in answer.replace(',', '')
                rows.append((good, calls, tokens, tool_s, time.perf_counter() - start))
                if not good:
                    print('wrong:', answer.strip()[:140].replace('\n', ' '))
            median = lambda index: statistics.median(row[index] for row in rows)
            print(f'| {index} | {mode} | {sum(r[0] for r in rows)}/{runs} | '
                  f'{median(1):g} | {median(2):.0f} | {median(3):.1f} | {median(4):.1f} |')
