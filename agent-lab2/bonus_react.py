import json
import os
from dotenv import load_dotenv
from google import genai
from google.genai import types
from module3_tools import lookup_cve_details

load_dotenv()


def get_installed_packages(hostname: str) -> str:
    """Return packages installed on a server.

    Args:
        hostname: Managed host name, e.g. db-prod-01.
    """
    hosts = {'db-prod-01': ['openssh-server 9.6', 'xz-utils 5.6.1', 'postgresql 16']}
    return json.dumps(hosts.get(hostname, {'error': f'Unknown host: {hostname}'}))


def run_react(prompt: str, max_iterations: int = 5) -> str:
    client = genai.Client()
    tools = {fn.__name__: fn for fn in [lookup_cve_details, get_installed_packages]}
    config = types.GenerateContentConfig(
        system_instruction='Use tools to check CVEs and installed packages. Do not invent vulnerability facts. Answer after inspecting the tool results.',
        tools=list(tools.values()),
        automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True),
    )
    messages = [types.Content(role='user', parts=[types.Part.from_text(text=prompt)])]
    for step in range(max_iterations):
        response = client.models.generate_content(
            model=os.getenv('LAB_MODEL', 'gemini-3.5-flash-lite'), contents=messages, config=config
        )
        calls = response.function_calls or []
        if not calls:
            return response.text or ''
        messages.append(response.candidates[0].content)
        parts = []
        for call in calls:
            fn = tools.get(call.name)
            try:
                output = str(fn(**dict(call.args or {}))) if fn else f"ERROR: Unknown tool '{call.name}'"
            except Exception as e:
                output = f'ERROR: {e}'
            print(f'[{step + 1}] {call.name} -> {output}')
            parts.append(types.Part(function_response=types.FunctionResponse(
                id=call.id, name=call.name, response={'result': output}
            )))
        messages.append(types.Content(role='user', parts=parts))
    return f'STOPPED: maximum {max_iterations} iterations reached'


if __name__ == '__main__':
    print(run_react('Compare CVE-2024-3094 and CVE-2021-44228, then check whether db-prod-01 has an affected package.'))
