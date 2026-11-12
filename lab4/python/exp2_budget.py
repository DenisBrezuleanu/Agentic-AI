import ast
import operator
import re
import sys
from collections import Counter
from fractions import Fraction
from llm import ask

TRIP = ('Two friends fly from Iasi to Rome. Flights cost EUR 129 per person, each way. '
        'They share one hotel room at EUR 85 per night, arriving on 12 May and leaving on 16 May. '
        'The city tax is EUR 2.50 per person per night. Each buys a EUR 45 museum pass. '
        'Their total budget is EUR 1000. Does the trip fit the budget, and by how much?')
EXPECTED = ('yes', 34.0)
SHORT = TRIP + '\nReply with exactly one line and nothing else: Answer: <yes|no>, <difference in EUR>'
BETTER = TRIP + ('\nFirst work through the cost categories: number of people and return flights, '
                 'number of hotel nights for one shared room, tax per person per night, and two passes. '
                 'Calculate total and compare with 1000 EUR. Finish with EXACTLY this final line: '
                 'Answer: <yes|no>, <difference in EUR>. The difference is an unsigned numeric amount.')
EXPRESSION_ONLY = TRIP + ('\nDo not calculate a total or give a verdict. Write exactly one arithmetic '
                          'expression that adds the flights, hotel, tax and passes, using only '
                          'numbers, parentheses, +, -, *, /; end with one line: Total: <expression>')
ANSWER_RE = re.compile(r'Answer:\s*(yes|no)\s*,\s*(?:EUR|€)?\s*([\d.,]+)', re.I)
OPS = {ast.Add: operator.add, ast.Sub: operator.sub, ast.Mult: operator.mul,
       ast.Div: operator.truediv}


def number(value):
    if re.fullmatch(r'\d+,\d{1,2}', value):
        value = value.replace(',', '.')
    return float(value.replace(',', ''))


def parse(text):
    match = ANSWER_RE.search(text.replace('*', ''))
    return (match.group(1).lower(), number(match.group(2).rstrip('.'))) if match else None


def evaluate(expression):
    def walk(node):
        if isinstance(node, ast.BinOp) and type(node.op) in OPS:
            return OPS[type(node.op)](walk(node.left), walk(node.right))
        if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.USub):
            return -walk(node.operand)
        if isinstance(node, ast.Constant) and type(node.value) in (float, int):
            return Fraction(str(node.value))
        raise ValueError('Unsupported expression')
    try:
        result = walk(ast.parse(expression, mode='eval').body)
        if abs(result) > 1_000_000_000:
            return None
        return result
    except (SyntaxError, ValueError, ZeroDivisionError, OverflowError, RecursionError):
        return None


def run(prompt, times=5):
    rows = []
    for _ in range(times):
        reply = ask(prompt, temperature=0.7)
        rows.append((parse(reply.text), reply.out_tokens, reply.text.strip().splitlines()[-1] if reply.text.strip() else ''))
    return rows


def vote(rows):
    frequencies = Counter(row[0] for row in rows if row[0] is not None)
    return frequencies.most_common(1)[0][0] if frequencies else None


def run_code(times=5):
    correct, tokens = 0, 0
    for _ in range(times):
        reply = ask(EXPRESSION_ONLY, temperature=0.7)
        tokens += reply.out_tokens
        match = re.search(r'^Total:\s*(.+)$', reply.text.replace('**', '').replace('×', '*'), re.M | re.I)
        total = evaluate(match.group(1).strip().strip('`')) if match else None
        verdict = None if total is None else ('yes' if total <= 1000 else 'no', float(abs(1000 - total)))
        correct += verdict == EXPECTED
        print(f'{verdict}  total={total}  tokens={reply.out_tokens}')
    print(f'code: {correct}/{times}; avg out tokens={tokens / times:.1f}')


if __name__ == '__main__':
    if '--code' in sys.argv:
        run_code()
    else:
        print('| prompt | correct / 5 | avg output tokens | majority vote |')
        print('|---|---:|---:|---|')
        for name, prompt in [('short', SHORT), ('better', BETTER)]:
            rows = run(prompt)
            print(f'| {name} | {sum(p == EXPECTED for p, _, _ in rows)}/5 | '
                  f'{sum(t for _, t, _ in rows) / len(rows):.1f} | {vote(rows)} |')
