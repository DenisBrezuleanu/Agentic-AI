import os
import time
from dataclasses import dataclass
from typing import Any

from dotenv import load_dotenv

load_dotenv()
MODEL = os.getenv('LAB_MODEL', 'gemini-3.5-flash-lite')
TIMEOUT = float(os.getenv('LAB_TIMEOUT', '30'))


class QuotaExhausted(RuntimeError):
    pass


@dataclass
class Reply:
    text: str
    parsed: Any
    in_tokens: int
    out_tokens: int
    seconds: float


def ask(prompt: str, *, system: str | None = None, temperature: float | None = None,
        schema: Any = None, contents: list | None = None) -> Reply:
    from google import genai
    from google.genai import types, errors
    import httpx
    if not os.getenv('GEMINI_API_KEY'):
        raise RuntimeError('GEMINI_API_KEY is missing. Create .env in project root.')
    client = genai.Client(http_options=types.HttpOptions(
        timeout=int(TIMEOUT * 1000), retry_options=types.HttpRetryOptions(
            attempts=3, initial_delay=2.0, http_status_codes=[408, 500, 502, 503, 504])))
    config = types.GenerateContentConfig(
        system_instruction=system, temperature=temperature,
        response_mime_type='application/json' if schema else None, response_schema=schema)
    start = time.perf_counter()
    for attempt in range(3):
        try:
            response = client.models.generate_content(model=MODEL, contents=contents or prompt, config=config)
            usage = response.usage_metadata
            return Reply(response.text or '', response.parsed if schema else None,
                         (usage.prompt_token_count or 0) if usage else 0,
                         ((usage.candidates_token_count or 0) + (usage.thoughts_token_count or 0)) if usage else 0,
                         time.perf_counter() - start)
        except errors.ClientError as e:
            if e.code != 429:
                raise
            if 'PerDay' in str(e):
                raise QuotaExhausted('Daily Gemini quota exhausted; switch LAB_MODEL or retry tomorrow') from e
            if attempt == 2:
                raise
            time.sleep(20 * (attempt + 1))
        except httpx.TimeoutException as e:
            raise TimeoutError('Gemini timed out; increase LAB_TIMEOUT') from e
