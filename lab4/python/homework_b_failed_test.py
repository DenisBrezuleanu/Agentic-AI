import json
import os
import re
import statistics
import subprocess
import sys
import tempfile
from pathlib import Path
from llm import ask

TEST_PROGRAM = '''import runpy
mod = runpy.run_path('solution.py')
f = mod['nights_between']
checks = [
    ('same day', '2026-05-12', '2026-05-12', 0),
    ('ordinary stay', '2026-05-12', '2026-05-16', 4),
    ('month end', '2026-01-31', '2026-02-02', 2),
    ('year end', '2026-12-30', '2027-01-02', 3),
    ('leap day', '2024-02-28', '2024-03-01', 2),
]
failures = []
for name, start, end, expected in checks:
    try:
        received = f(start, end)
        if type(received) is not int or received != expected:
            failures.append(f'{name}: expected {expected!r}, got {received!r}')
    except Exception as e:
        failures.append(f'{name}: unexpected {type(e).__name__}: {e}')
for name, start, end in [
    ('reverse', '2026-05-16', '2026-05-12'),
    ('bad format', '12-05-2026', '2026-05-16'),
    ('bad calendar date', '2026-02-30', '2026-03-01'),
]:
    try:
        f(start, end)
        failures.append(f'{name}: expected an exception')
    except (ValueError, TypeError):
        pass
    except Exception as e:
        failures.append(f'{name}: wrong exception {type(e).__name__}: {e}')
if failures:
    print('\\n'.join(failures))
    raise SystemExit(1)
print('8/8 tests passed')
'''

SYSTEM = ('Write a correct Python function nights_between(check_in: str, check_out: str) -> int. '
          'Dates MUST be in YYYY-MM-DD; count hotel nights with calendar arithmetic. '
          'Same-day is 0; leap years, month and year boundaries must work. '
          'Raise ValueError for invalid dates, wrong date format and checkout before checkin. '
          'Return only runnable Python code; no markdown or explanations.')


def clean_code(text):
    block = re.search(r'```(?:python)?\s*([\s\S]*?)```', text)
    return (block.group(1) if block else text).strip()


def resource_limit():
    try:
        import resource
        resource.setrlimit(resource.RLIMIT_CPU, (2, 3))
        resource.setrlimit(resource.RLIMIT_AS, (256 * 1024 * 1024, 256 * 1024 * 1024))
        resource.setrlimit(resource.RLIMIT_FSIZE, (2 * 1024 * 1024, 2 * 1024 * 1024))
    except (ImportError, ValueError):
        pass


def run_tests(code: str, timeout=4):
    if len(code) > 15000:
        return False, 'Generated code exceeds length limit'
    with tempfile.TemporaryDirectory() as folder:
        Path(folder, 'solution.py').write_text(code, encoding='utf-8')
        kwargs = {'preexec_fn': resource_limit} if os.name == 'posix' else {}
        try:
            result = subprocess.run([sys.executable, '-I', '-S', '-c', TEST_PROGRAM],
                                    cwd=folder, env={}, capture_output=True, text=True,
                                    timeout=timeout, **kwargs)
            output = (result.stdout + '\n' + result.stderr)[-2400:]
            return result.returncode == 0, output.strip()
        except subprocess.TimeoutExpired:
            return False, 'Timed out running tests'


def trial(with_lessons: bool, attempts=3):
    lessons = []
    tokens_in = tokens_out = 0
    for index in range(1, attempts + 1):
        prompt = SYSTEM + ('\nKnown lessons from earlier failures:\n' + '\n'.join(lessons) if lessons else '')
        reply = ask(prompt, temperature=0.7)
        tokens_in += reply.in_tokens
        tokens_out += reply.out_tokens
        code = clean_code(reply.text)
        passed, output = run_tests(code)
        print(f'  attempt {index}: {"pass" if passed else "fail"} {output[:160]!r}')
        if passed:
            return {'passed': True, 'attempts': index, 'input_tokens': tokens_in,
                    'output_tokens': tokens_out, 'lessons': lessons, 'code': code}
        if with_lessons and index < attempts:
            feedback = ask('The code below failed the tests. Why, and what exactly will you change? '
                           'Answer in two short sentences; do not write code yet.\nCODE:\n' + code +
                           '\nTEST OUTPUT:\n' + output)
            tokens_in += feedback.in_tokens
            tokens_out += feedback.out_tokens
            lessons.append(f'{index}: {feedback.text.strip()}')
    return {'passed': False, 'attempts': attempts, 'input_tokens': tokens_in,
            'output_tokens': tokens_out, 'lessons': lessons, 'code': code}


def experiment(runs=5):
    summary = {}
    for mode in ('plain', 'with_lessons'):
        rows = []
        print(f'\n{mode}')
        for i in range(runs):
            print('run', i + 1)
            row = trial(with_lessons=(mode == 'with_lessons'))
            rows.append(row)
            for note in row['lessons']:
                print('  lesson:', note)
        summary[mode] = {
            'successes': sum(row['passed'] for row in rows),
            'runs': runs,
            'mean_attempts': statistics.mean(row['attempts'] for row in rows),
            'mean_total_tokens': statistics.mean(row['input_tokens'] + row['output_tokens'] for row in rows),
        }
    print(json.dumps(summary, indent=2))
    return summary


if __name__ == '__main__':
    runs = int(sys.argv[1]) if len(sys.argv) > 1 else 5
    if runs < 5:
        raise ValueError('The homework requires at least five runs')
    experiment(runs)
