import json
import os
from dotenv import load_dotenv
from google import genai
from google.genai import types

load_dotenv()


def lookup_cve_details(cve_id: str) -> str:
    """Look up the CVSS score and affected software for a known CVE.

    Args:
        cve_id: Official CVE ID such as CVE-2024-3094.
    """
    records = {
        'CVE-2024-3094': {
            'cvss': 10.0,
            'affected': 'xz-utils 5.6.0 and 5.6.1',
            'summary': 'Malicious backdoor in the liblzma build process affecting sshd authentication.'
        },
        'CVE-2021-44228': {
            'cvss': 10.0,
            'affected': 'Apache Log4j2 2.0-beta9 through 2.14.1',
            'summary': 'Remote code execution via untrusted JNDI lookups (Log4Shell).'
        }
    }
    return json.dumps(records.get(cve_id.upper(), {'error': f'No record found for {cve_id}'}))


def run_manual_tool_roundtrip(user_prompt: str) -> str:
    client = genai.Client()
    config = types.GenerateContentConfig(
        system_instruction='You are a cybersecurity assistant. Always use the CVE lookup tool to verify CVE facts.',
        tools=[lookup_cve_details],
        automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True),
        temperature=0.0,
    )
    messages = [types.Content(role='user', parts=[types.Part.from_text(text=user_prompt)])]
    response = client.models.generate_content(
        model=os.getenv('LAB_MODEL', 'gemini-3.5-flash-lite'), contents=messages, config=config
    )
    calls = response.function_calls or []
    if not calls:
        print(response.text or '')
        return response.text or ''

    messages.append(response.candidates[0].content)
    parts = []
    for call in calls:
        if call.name != 'lookup_cve_details':
            output = f"ERROR: Unknown tool '{call.name}'"
        else:
            try:
                output = lookup_cve_details(**dict(call.args or {}))
            except (TypeError, ValueError) as e:
                output = f'ERROR: {e}'
        print(f'[LLM Requested Tool] {call.name} {call.args}')
        print(f'[Local Function Output] {output}')
        parts.append(types.Part(function_response=types.FunctionResponse(
            id=call.id, name=call.name, response={'result': output}
        )))
    messages.append(types.Content(role='user', parts=parts))
    final = client.models.generate_content(
        model=os.getenv('LAB_MODEL', 'gemini-3.5-flash-lite'), contents=messages, config=config
    )
    answer = final.text or ''
    print(answer)
    return answer


if __name__ == '__main__':
    run_manual_tool_roundtrip('What is CVE-2024-3094, what versions are affected, and how severe is it?')
