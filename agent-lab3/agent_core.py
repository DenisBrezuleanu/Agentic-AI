import json
import os
import time
from collections import Counter
from dataclasses import dataclass, field
from typing import Callable
from dotenv import load_dotenv
from google import genai
from google.genai import errors, types

load_dotenv()
MODEL = os.getenv('LAB_MODEL', 'gemini-3.5-flash-lite')


@dataclass
class AgentResult:
    answer: str
    stop_reason: str
    steps: int
    prompt_tokens_per_step: list[int] = field(default_factory=list)

    @property
    def total_prompt_tokens(self) -> int:
        return sum(self.prompt_tokens_per_step)


@dataclass
class Decision:
    approved: bool
    args: dict | None = None
    feedback: str = ''


Approver = Callable[[str, dict], Decision]


def call_llm(contents, config, retries: int = 5):
    client = genai.Client()
    for attempt in range(retries):
        try:
            return client.models.generate_content(model=MODEL, contents=contents, config=config)
        except errors.APIError as e:
            if e.code not in (429, 500, 502, 503, 504) or attempt == retries - 1:
                raise
            delay = min(5 * 2 ** attempt, 40)
            print(f'Provider {e.code}; retrying in {delay}s')
            time.sleep(delay)


def execute_tool(tools_map: dict[str, Callable], name: str, args: dict) -> str:
    fn = tools_map.get(name)
    if fn is None:
        return f"ERROR: Unknown tool '{name}'. Available tools: {', '.join(sorted(tools_map))}."
    try:
        return str(fn(**args))
    except TypeError as e:
        return f'ERROR: Bad arguments for {name}: {e}'
    except Exception as e:
        return f'ERROR: {name} failed: {e}'


def run_agent(user_prompt: str, tools: list[Callable], system_instruction: str,
              max_steps: int = 8, requires_approval: frozenset[str] = frozenset(),
              approver: Approver | None = None, show_thoughts: bool = False,
              verbose: bool = True) -> AgentResult:
    if max_steps < 1:
        raise ValueError('max_steps must be >= 1')
    tools_map = {fn.__name__: fn for fn in tools}
    config = types.GenerateContentConfig(
        system_instruction=system_instruction,
        tools=tools,
        automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True),
        thinking_config=(types.ThinkingConfig(include_thoughts=True, thinking_level='high')
                         if show_thoughts else None),
    )
    messages = [types.Content(role='user', parts=[types.Part.from_text(text=user_prompt)])]
    token_counts = []
    seen = Counter()

    for step in range(1, max_steps + 1):
        try:
            response = call_llm(messages, config)
        except errors.APIError as e:
            return AgentResult(f'STOPPED: provider error {e.code}: {e.message}', 'provider_error', step, token_counts)

        usage = getattr(response, 'usage_metadata', None)
        count = getattr(usage, 'prompt_token_count', 0) or 0
        token_counts.append(count)
        if verbose:
            print(f'\n--- [Step {step}/{max_steps}] input tokens: {count:,} ---')

        content = response.candidates[0].content
        if show_thoughts and verbose:
            for part in content.parts or []:
                if getattr(part, 'thought', False) and getattr(part, 'text', None):
                    print(f'[Thought] {part.text.strip()[:300]}')

        calls = response.function_calls or []
        if not calls:
            return AgentResult(response.text or '', 'done', step, token_counts)

        messages.append(content)
        parts = []
        for call in calls:
            args = dict(call.args or {})
            name = call.name
            key = (name, json.dumps(args, sort_keys=True, default=str))
            seen[key] += 1
            if verbose:
                print(f'-> {name}({json.dumps(args, default=str)[:200]})')

            if seen[key] >= 3:
                return AgentResult(f"STOPPED: tool '{name}' called with identical arguments three times.",
                                   'stuck', step, token_counts)
            if seen[key] == 2:
                output = 'NOTE: Repeated call with identical arguments. Use the earlier result instead.'
            elif name in requires_approval:
                if approver is None:
                    decision = Decision(False, feedback='No operator approver configured')
                else:
                    try:
                        decision = approver(name, args)
                    except (EOFError, KeyboardInterrupt):
                        decision = Decision(False, feedback='Operator approval interrupted')
                if not decision.approved:
                    output = f'DENIED BY OPERATOR: {decision.feedback or "Write rejected"}. Adjust your plan.'
                else:
                    actual_args = args if decision.args is None else decision.args
                    output = execute_tool(tools_map, name, actual_args)
                    if actual_args != args:
                        output = f'OPERATOR EDITED ARGUMENTS to {json.dumps(actual_args, default=str)}. {output}'
            else:
                output = execute_tool(tools_map, name, args)

            if verbose:
                print(f'<- {output[:200]}')
            parts.append(types.Part(function_response=types.FunctionResponse(
                id=call.id, name=name, response={'result': output}
            )))
        messages.append(types.Content(role='user', parts=parts))

    return AgentResult(f'STOPPED after {max_steps} steps without a final answer.',
                       'max_steps', max_steps, token_counts)
