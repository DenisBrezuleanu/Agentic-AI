import argparse
import ast
import operator
from collections import Counter
from dataclasses import dataclass
from fractions import Fraction
from pydantic import BaseModel, Field
from llm import ask

OPERATIONS = {'+': operator.add, '-': operator.sub, '*': operator.mul, '/': operator.truediv}
SYMBOLS = {ast.Add: '+', ast.Sub: '-', ast.Mult: '*', ast.Div: '/'}


@dataclass(frozen=True)
class Node:
    value: Fraction
    expression: str


class DirectAnswer(BaseModel):
    expression: str = Field(description='An arithmetic expression using exactly the four supplied values once')


class Move(BaseModel):
    first: int = Field(description='Zero-based index of first chosen value')
    second: int = Field(description='Zero-based index of second chosen value, different from first')
    op: str = Field(description='One of + - * /')


class Proposed(BaseModel):
    moves: list[Move] = Field(description='Exactly three different candidate moves')


class Rating(BaseModel):
    id: int
    category: str = Field(description='One of sure, likely, impossible')


class Ranking(BaseModel):
    ratings: list[Rating] = Field(description='One rating for each candidate id')


def arithmetic(expression: str, numbers: list[int]) -> Fraction | None:
    leaves = []

    def walk(n):
        if isinstance(n, ast.Constant) and type(n.value) in (int, float):
            val = Fraction(str(n.value))
            leaves.append(val)
            return val
        if isinstance(n, ast.BinOp) and type(n.op) in SYMBOLS:
            return OPERATIONS[SYMBOLS[type(n.op)]](walk(n.left), walk(n.right))
        raise ValueError('Not an arithmetic expression')

    try:
        if len(expression) > 300:
            return None
        value = walk(ast.parse(expression, mode='eval').body)
        if Counter(leaves) != Counter(Fraction(n) for n in numbers):
            return None
        return value
    except (SyntaxError, ValueError, ZeroDivisionError, RecursionError, OverflowError):
        return None


def combine(state: tuple[Node, ...], move: Move) -> tuple[Node, ...] | None:
    a, b = move.first, move.second
    if a == b or min(a, b) < 0 or max(a, b) >= len(state) or move.op not in OPERATIONS:
        return None
    try:
        val = OPERATIONS[move.op](state[a].value, state[b].value)
    except ZeroDivisionError:
        return None
    next_state = [node for idx, node in enumerate(state) if idx not in (a, b)]
    next_state.append(Node(val, f'({state[a].expression}{move.op}{state[b].expression})'))
    return tuple(next_state)


def state_text(state):
    return ', '.join(f'{i}:{node.value}' for i, node in enumerate(state))


def offline_solver(numbers):
    start = tuple(Node(Fraction(n), str(n)) for n in numbers)
    seen = set()

    def visit(state):
        key = tuple(sorted(node.value for node in state))
        if key in seen:
            return None
        seen.add(key)
        if len(state) == 1:
            return state[0].expression if state[0].value == 24 else None
        for i in range(len(state)):
            for j in range(len(state)):
                if i == j:
                    continue
                for op in OPERATIONS:
                    new = combine(state, Move(first=i, second=j, op=op))
                    if new:
                        found = visit(new)
                        if found:
                            return found
        return None

    return visit(start)


def direct(numbers, n=5):
    total_in = total_out = correct = 0
    for index in range(n):
        r = ask(f'Use each number exactly once: {numbers}. Using + - * / and parentheses, '
                f'produce an expression equal to 24. Do not add any other numbers.', schema=DirectAnswer, temperature=0.7)
        total_in += r.in_tokens
        total_out += r.out_tokens
        expr = r.parsed.expression if r.parsed else ''
        result = arithmetic(expr, numbers)
        ok = result == 24
        correct += ok
        print(f'direct {index + 1}: {expr or "unparseable"} -> {result}, valid={ok}')
    return {'correct': correct, 'calls': n, 'input_tokens': total_in, 'output_tokens': total_out}


def search(numbers):
    frontier = [tuple(Node(Fraction(n), str(n)) for n in numbers)]
    calls = in_tokens = out_tokens = 0
    for depth in range(3):
        candidates = []
        for state in frontier:
            prompt = (f'Current arithmetic values with zero-based indices: {state_text(state)}. '
                      'Propose exactly THREE different moves combining any two DISTINCT indexed values '
                      'with one operation + - * /. Return only the operations with indices. '
                      'The goal is 24; no new numbers are allowed.')
            reply = ask(prompt, schema=Proposed, temperature=0.7)
            calls += 1
            in_tokens += reply.in_tokens
            out_tokens += reply.out_tokens
            for move in (reply.parsed.moves if reply.parsed else []):
                next_state = combine(state, move)
                if next_state and next_state not in candidates:
                    candidates.append(next_state)
        if not candidates:
            print(f'No valid candidate at depth {depth + 1}')
            break
        ratings = '\n'.join(f'{i}: {[str(node.value) for node in state]}' for i, state in enumerate(candidates))
        reply = ask('Rank these candidate states by how likely they can still reach exactly 24. '
                    'Rate every candidate as sure, likely or impossible; return its id and rating exactly once. '
                    'Candidate states:\n' + ratings, schema=Ranking)
        calls += 1
        in_tokens += reply.in_tokens
        out_tokens += reply.out_tokens
        scores = {'sure': 0, 'likely': 1, 'impossible': 2}
        ratings = {r.id: scores.get(r.category.lower(), 3) for r in reply.parsed.ratings} if reply.parsed else {}
        ranked = sorted(range(len(candidates)), key=lambda i: (ratings.get(i, 3), i))
        frontier = [candidates[i] for i in ranked[:3]]
        if any(len(state) == 1 and state[0].value == 24 for state in frontier):
            break
    solved = next((state[0].expression for state in frontier
                   if len(state) == 1 and state[0].value == 24), None)
    if solved:
        assert arithmetic(solved, numbers) == 24
    print('search answer:', solved or 'no solution in beam; not proof of impossibility')
    return {'correct': bool(solved), 'calls': calls, 'input_tokens': in_tokens, 'output_tokens': out_tokens}


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('values', type=int, nargs=4, default=[4, 9, 10, 13])
    args = parser.parse_args()
    print('Offline reference:', offline_solver(args.values))
    print('Direct:', direct(args.values))
    print('Model-guided beam:', search(args.values))
