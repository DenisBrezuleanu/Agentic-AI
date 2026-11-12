import re
from collections import Counter
from pydantic import BaseModel, Field
from llm import ask

DAY_RULES = '''Plan ONE day in Rome. Schedule all five items, each exactly once:
- Borghese Gallery: 2 h. Entry ONLY at 09:00, 11:00, 13:00 or 15:00.
- Colosseum: 2 h. Entry on the hour (xx:00), from 09:00 to 15:00.
- Pantheon: 1 h. Open 09:00-19:00 (must be finished by 19:00).
- Lunch: 1 h. Must START between 12:00 and 14:00.
- Trastevere food walk: 1 h 30 min. Starts ONLY at 17:00 or 18:00.
Moving between two consecutive items takes 30 minutes. The day starts at 09:00 and must end by 20:00.
Return the schedule in time order, times as HH:MM.'''
WITH_HINT = (DAY_RULES + '\nFirst place activities with fixed starting slots, then fit the flexible ones '
             'around them. Ensure 30 minutes between any two activities. Check all constraints before answering.')


class Item(BaseModel):
    name: str = Field(description='One of Borghese Gallery, Colosseum, Pantheon, Lunch, Trastevere food walk')
    start: str
    end: str


class Schedule(BaseModel):
    items: list[Item]


class ScheduleWithPlan(BaseModel):
    plan: str = Field(description='Brief scheduling strategy: fixed entries, gaps, lunch window, and constraints checked')
    items: list[Item]


RULES = {
    'Borghese Gallery': (120, [h * 60 for h in (9, 11, 13, 15)]),
    'Colosseum': (120, [h * 60 for h in range(9, 16)]),
    'Pantheon': (60, list(range(9 * 60, 18 * 60 + 1))),
    'Lunch': (60, list(range(12 * 60, 14 * 60 + 1))),
    'Trastevere food walk': (90, [17 * 60, 18 * 60]),
}


def minutes(value):
    if not re.fullmatch(r'\d{2}:\d{2}', value):
        raise ValueError('bad format')
    h, m = map(int, value.split(':'))
    if h > 23 or m > 59:
        raise ValueError('bad time')
    return 60 * h + m


def check(schedule: Schedule) -> list[str]:
    errors = []
    counts = Counter(item.name for item in schedule.items)
    for name in RULES:
        if counts[name] != 1:
            errors.append(f'{name} appears {counts[name]} times')
    timed = []
    outside = False
    for item in schedule.items:
        name = item.name
        if name not in RULES:
            errors.append(f'unknown item {name!r}')
        try:
            start, end = minutes(item.start), minutes(item.end)
        except (ValueError, AttributeError):
            errors.append(f'{name}: bad time format')
            continue
        if start < 9 * 60 or end > 20 * 60 or end < 9 * 60 or start > 20 * 60:
            outside = True
        if name in RULES:
            duration, slots = RULES[name]
            if end - start != duration:
                errors.append(f'{name}: lasts {end - start} min, must be {duration}')
            if start not in slots:
                errors.append(f'{name}: cannot start at {item.start}')
        timed.append((start, end, name))
    for first, second in zip(sorted(timed), sorted(timed)[1:]):
        if second[0] - first[1] < 30:
            errors.append(f'{first[2]} -> {second[2]}: needs 30 min to move')
    if outside:
        errors.append('outside 09:00-20:00')
    return errors


def sample(prompt, schema=Schedule, n=5):
    out = []
    for _ in range(n):
        reply = ask(prompt, schema=schema, temperature=1.0)
        value = reply.parsed
        out.append((value, check(value) if value is not None else ['unparseable output'], reply.out_tokens))
    return out


def best(samples):
    valid = [item for item, errors, _ in samples if item is not None and not errors]
    return max(valid, key=lambda value: min(minutes(item.start) for item in value.items), default=None)


if __name__ == '__main__':
    runs = [('plain', DAY_RULES, Schedule), ('hint', WITH_HINT, Schedule),
            ('hint + plan field', WITH_HINT, ScheduleWithPlan)]
    print('| variant | valid / 5 | avg out tokens |')
    print('|---|---:|---:|')
    for label, prompt, schema in runs:
        results = sample(prompt, schema)
        print(f'| {label} | {sum(not errs for _, errs, _ in results)}/5 | '
              f'{sum(tokens for _, _, tokens in results) / len(results):.1f} |')
        chosen = best(results)
        if chosen:
            print('chosen:', [(item.start, item.name) for item in sorted(chosen.items, key=lambda i: minutes(i.start))])
