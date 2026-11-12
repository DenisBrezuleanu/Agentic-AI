import sys
import pytest
import lab3_ex2_hitl as ex2
from agent_core import Decision


@pytest.fixture(autouse=True)
def workspace(monkeypatch, tmp_path):
    monkeypatch.setattr(ex2, 'WORKSPACE', tmp_path)
    monkeypatch.setattr(ex2, 'SANDBOX_DIR', tmp_path / 'sandbox')
    ex2.setup_workspace()


@pytest.mark.parametrize('attack', [
    '../canary_secret.txt', '../../.env', 'subdir/../../canary_secret.txt', '/etc/passwd'
])
def test_read_outside_sandbox_is_blocked(attack):
    out = ex2.read_file(attack)
    assert 'SECURITY VIOLATION' in out
    assert ex2.CANARY not in out


def test_drive_path_depends_on_os():
    output = ex2.read_file('C:/Windows/win.ini')
    assert ex2.CANARY not in output
    if sys.platform == 'win32':
        assert 'SECURITY VIOLATION' in output
    else:
        assert ex2.resolve_in_sandbox('C:/Windows/win.ini').is_relative_to(ex2.SANDBOX_DIR)


def test_write_outside_is_blocked():
    assert 'SECURITY VIOLATION' in ex2.write_file('../pwned.txt', 'x')
    assert not (ex2.WORKSPACE / 'pwned.txt').exists()


def test_normal_files_work():
    assert 'PermitRootLogin yes' in ex2.read_file('sshd_config')
    assert ex2.write_file('new.conf', 'Port 2222\n').startswith('SUCCESS')
    assert ex2.read_file('./new.conf') == 'Port 2222\n'


def test_missing_file_error_lists_real_files():
    assert 'sshd_config' in ex2.read_file('sshd.conf')


def test_approver_yes(monkeypatch):
    monkeypatch.setattr('builtins.input', lambda prompt='': 'yes')
    assert ex2.terminal_approver('write_file', {'filename': 'a', 'content': 'b'}) == Decision(True)


def test_approver_feedback(monkeypatch):
    monkeypatch.setattr('builtins.input', lambda prompt='': 'write to sshd_config.hardened instead')
    decision = ex2.terminal_approver('write_file', {'filename': 'sshd_config', 'content': 'x'})
    assert not decision.approved and 'hardened' in decision.feedback


def test_approver_edit(monkeypatch):
    replies = iter(['e', 'sshd_config.hardened'])
    monkeypatch.setattr('builtins.input', lambda prompt='': next(replies))
    decision = ex2.terminal_approver('write_file', {'filename': 'sshd_config', 'content': 'x'})
    assert decision.approved and decision.args['filename'] == 'sshd_config.hardened'


def test_symlink_outside_is_blocked():
    link = ex2.SANDBOX_DIR / 'escape'
    try:
        link.symlink_to(ex2.WORKSPACE / 'canary_secret.txt')
    except (OSError, NotImplementedError):
        pytest.skip('symlinks unavailable')
    assert 'SECURITY VIOLATION' in ex2.read_file('escape')
