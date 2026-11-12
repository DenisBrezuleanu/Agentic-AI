import json
import sys
from agent_core import run_agent

HOSTS = {
    'db-prod-01': {'environment': 'production', 'packages': {'openssh-server': '9.6', 'xz-utils': '5.6.1', 'postgresql': '16.2'}},
    'web-edge-01': {'environment': 'production', 'packages': {'nginx': '1.24.0', 'log4j-core': '2.14.0', 'openjdk': '17.0.9'}},
    'mail-prod-02': {'environment': 'production', 'packages': {'postfix': '3.8.4', 'openssl': '3.0.13', 'xz-utils': '5.4.6'}},
    'ci-runner-03': {'environment': 'staging', 'packages': {'xz-utils': '5.6.0', 'docker-ce': '26.1.0'}},
}

CVE_DB = [
    {'id': 'CVE-2024-3094', 'package': 'xz-utils', 'min': '5.6.0', 'max': '5.6.1', 'cvss': 10.0, 'summary': 'Backdoor in liblzma.'},
    {'id': 'CVE-2021-44228', 'package': 'log4j-core', 'min': '2.0.0', 'max': '2.14.1', 'cvss': 10.0, 'summary': 'Log4Shell remote code execution.'},
    {'id': 'CVE-2024-6387', 'package': 'openssh-server', 'min': '8.5', 'max': '9.7', 'cvss': 8.1, 'summary': 'sshd race condition.'},
    {'id': 'CVE-2024-7347', 'package': 'nginx', 'min': '1.5.13', 'max': '1.27.0', 'cvss': 4.7, 'summary': 'mp4 module out-of-bounds read.'},
]


def parse_version(version: str) -> tuple[int, ...]:
    return tuple(int(n) for n in version.split('.'))


def list_hosts() -> str:
    """List managed server hostnames and whether each is production or staging."""
    return json.dumps([{'hostname': host, 'environment': data['environment']}
                       for host, data in HOSTS.items()])


def get_installed_packages(hostname: str) -> str:
    """Look up the installed packages and versions on a managed server.

    Args:
        hostname: Exact hostname returned by list_hosts.
    """
    host = HOSTS.get(hostname)
    if host is None:
        return f"ERROR: Host '{hostname}' not found. Known hosts: {', '.join(HOSTS)}."
    return json.dumps(host['packages'])


def find_cves_for_package(package: str, version: str) -> str:
    """Find known CVEs and CVSS scores affecting a specific installed package version.

    Args:
        package: Installed package name such as xz-utils.
        version: Installed package version such as 5.6.1.
    """
    try:
        target = parse_version(version)
    except ValueError:
        return f"ERROR: Version '{version}' is not numeric (expected e.g. '5.6.1')."
    results = [{'id': item['id'], 'cvss': item['cvss'], 'summary': item['summary']}
               for item in CVE_DB if item['package'] == package
               and parse_version(item['min']) <= target <= parse_version(item['max'])]
    return json.dumps(results)


SYSTEM = ('You are a security infrastructure agent. Discover the hosts, their packages, and CVEs through tools; never guess. '
          'Investigate only production hosts and filter CVSS >= 9.0. '
          'Call independent lookups in parallel. In the final answer list affected hosts and packages, '
          'CVE IDs, CVSS scores, plus production hosts checked and found clean.')

if __name__ == '__main__':
    result = run_agent('Which of our PRODUCTION hosts are exposed to a vulnerability with CVSS >= 9.0?',
                       tools=[list_hosts, get_installed_packages, find_cves_for_package],
                       system_instruction=SYSTEM, max_steps=8, show_thoughts='--thoughts' in sys.argv)
    print(f'\n[Final Agent Answer] (stop_reason={result.stop_reason}, steps={result.steps})\n{result.answer}')
    print(f'Input tokens: {result.prompt_tokens_per_step}, total={result.total_prompt_tokens}')
