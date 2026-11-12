from types import SimpleNamespace
import exp3_interview as ex3
from exp3_interview import TravelBrief, missing_required


def test_missing_required_order():
    assert missing_required(TravelBrief()) == ex3.REQUIRED
    b = TravelBrief(origin='Iasi', destination='open', dates='12-16 May', travelers=2,
                    budget_eur=1000, interests=['food'])
    assert missing_required(b) == []
    assert missing_required(b, strict=True) == ['pace', 'avoid']


def test_empty_string_is_missing():
    b = TravelBrief(origin='  ', destination='', dates='May', travelers=0, budget_eur=-1)
    assert 'origin' in missing_required(b)
    assert 'travelers' in missing_required(b)
    assert 'dates' in missing_required(b, strict=True)


def test_harness_stops_even_when_model_still_asks(monkeypatch):
    brief = TravelBrief(origin='Iasi', destination='Rome', dates='12-16 May 2027', travelers=2,
                         budget_eur=1000, interests=['history'])
    monkeypatch.setattr(ex3, 'ask', lambda *a, **k: SimpleNamespace(parsed=SimpleNamespace(
        brief=brief, next_question='What is your favorite color?')))
    result, questions = ex3.interview('Plan my trip', lambda _t, _q: 'no')
    assert questions == 0 and result == brief


def test_harness_recovers_empty_question(monkeypatch):
    answers = []
    turns = [TravelBrief(), TravelBrief(origin='Iasi', destination='open', dates='12-16 May',
                                        travelers=2, budget_eur=1000, interests=['food'])]
    def mock_ask(*args, **kwargs):
        return SimpleNamespace(parsed=SimpleNamespace(brief=turns.pop(0), next_question=''))
    monkeypatch.setattr(ex3, 'ask', mock_ask)
    brief, count = ex3.interview('Plan my trip', lambda _t, question: answers.append(question) or 'Iasi')
    assert count == 1 and answers == [ex3.PROMPTS['origin']]
    assert missing_required(brief) == []
