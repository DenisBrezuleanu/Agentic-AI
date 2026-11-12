from homework_b_failed_test import run_tests


def test_valid_implementation_passes():
    code = '''from datetime import datetime

def nights_between(check_in: str, check_out: str) -> int:
    a = datetime.strptime(check_in, '%Y-%m-%d')
    b = datetime.strptime(check_out, '%Y-%m-%d')
    if a.strftime('%Y-%m-%d') != check_in or b.strftime('%Y-%m-%d') != check_out:
        raise ValueError('bad format')
    nights = (b-a).days
    if nights < 0:
        raise ValueError('negative')
    return nights
'''
    ok, result = run_tests(code)
    assert ok, result


def test_incorrect_implementation_is_caught():
    ok, result = run_tests('def nights_between(check_in, check_out):\n    return 1')
    assert not ok
    assert 'expected' in result


def test_untrusted_endless_loop_times_out():
    ok, result = run_tests('while True: pass\n', timeout=1)
    assert not ok
