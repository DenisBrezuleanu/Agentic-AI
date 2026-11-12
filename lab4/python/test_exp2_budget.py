from fractions import Fraction
from exp2_budget import parse, evaluate, vote


def test_parse_answers():
    assert parse('Answer: yes, 34') == ('yes', 34.0)
    assert parse('**Answer:** yes, €34') == ('yes', 34.0)
    assert parse('Answer: YES, 34,00') == ('yes', 34.0)
    assert parse('Answer: no, 1,034.') == ('no', 1034.0)
    assert parse('34') is None


def test_calculator_is_safe():
    assert evaluate('2*2*129 + 4*85 + 2*4*2.5 + 2*45') == Fraction(966)
    assert evaluate('1/0') is None
    assert evaluate('__import__("os")') is None
    assert evaluate('2**30') is None
    assert evaluate('(1+2)*3') == Fraction(9)


def test_majority_vote():
    assert vote([(('yes', 34.0), 1, ''), (None, 2, ''), (('yes', 34.0), 3, ''), (('no', 20.0), 2, '')]) == ('yes', 34.0)
    assert vote([(None, 1, '')]) is None
