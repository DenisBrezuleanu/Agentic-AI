from fractions import Fraction
from homework_a_vouchers import arithmetic, combine, offline_solver, Node, Move


def test_puzzle_1_has_solution():
    values = [4, 9, 10, 13]
    assert arithmetic(offline_solver(values), values) == 24


def test_fraction_puzzle_has_solution():
    values = [1, 5, 5, 5]
    assert arithmetic(offline_solver(values), values) == 24


def test_rejects_missing_or_extra_values():
    assert arithmetic('(4 + 9) + 13', [4, 9, 10, 13]) is None
    assert arithmetic('4 * 9 + 10 + 13 + 1', [4, 9, 10, 13]) is None
    assert arithmetic('__import__("os")', [4, 9, 10, 13]) is None


def test_division_by_zero_is_ignored():
    assert combine((Node(Fraction(1), '1'), Node(Fraction(0), '0')),
                   Move(first=0, second=1, op='/')) is None
