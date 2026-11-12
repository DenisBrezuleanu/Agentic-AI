import os
import pytest
from module2_structured import LogAnalysis, SeverityLevel, parse_server_log


def test_schema_fields():
    assert set(LogAnalysis.model_fields) == {'severity', 'error_code', 'is_compromised', 'summary', 'recommended_fix'}
    assert {e.value for e in SeverityLevel} == {'LOW', 'MEDIUM', 'HIGH', 'CRITICAL'}


@pytest.mark.skipif(not os.getenv("GEMINI_API_KEY"), reason="Integration test requires Gemini API key")
def test_log_parsing():
    sample = ('2026-10-15 02:11:44 [ALERT] sshd[9012]: Accepted password for root '
              'from 198.51.100.77 port 44122 ssh2 (ErrorCode=401 bypassed via PAM bug)')
    result = parse_server_log(sample)
    assert result.severity in (SeverityLevel.HIGH, SeverityLevel.CRITICAL)
    assert result.error_code == 401
    assert result.is_compromised is True
    assert result.recommended_fix
