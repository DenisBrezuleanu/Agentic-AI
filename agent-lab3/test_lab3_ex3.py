import json
from types import SimpleNamespace
import pytest
import lab3_ex3_orchestrator as ex3


@pytest.fixture(autouse=True)
def folder(monkeypatch, tmp_path):
    monkeypatch.setattr(ex3, 'WORKDIR', tmp_path)
    ex3.WORKER_TOKENS.clear()
    ex3.make_noisy_log(1000)


def test_log_has_complete_attack_chain():
    text = ex3.read_file('auth.log')
    assert len(text.splitlines()) == 1034
    assert f'Accepted password for root from {ex3.ATTACKER}' in text
    assert 'new user: name=svc-backup, UID=0' in text


def test_path_traversal_blocked():
    assert 'SECURITY VIOLATION' in ex3.read_file('../secret.txt')
    assert 'SECURITY VIOLATION' in ex3.write_incident_report('../attack.md', 'x')


def test_worker_returns_valid_json_and_tracks_tokens(monkeypatch):
    line = ex3.read_file('auth.log').splitlines()[0]
    report = ex3.TriageReport(
        severity=ex3.Severity.CRITICAL,
        is_compromised=True,
        attacker_ips=[ex3.ATTACKER],
        evidence=[line],
        post_exploitation=['New UID=0 user'],
        firewall_rules=[f'ufw deny from {ex3.ATTACKER}'],
    )
    res = SimpleNamespace(text=report.model_dump_json(),
                          usage_metadata=SimpleNamespace(prompt_token_count=1234))
    monkeypatch.setattr(ex3, 'call_llm', lambda contents, config: res)
    data = json.loads(ex3.delegate_log_triage('auth.log'))
    assert data['is_compromised'] and data['severity'] == 'CRITICAL'
    assert ex3.WORKER_TOKENS == [1234]


def test_bad_worker_does_not_fabricate_report(monkeypatch):
    monkeypatch.setattr(ex3, '_structured_worker', lambda text: (_ for _ in ()).throw(ValueError('bad data')))
    assert ex3.delegate_log_triage('auth.log').startswith('ERROR:')
