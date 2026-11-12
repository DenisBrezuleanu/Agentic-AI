import os
from dotenv import load_dotenv
from google import genai

load_dotenv()

if __name__ == '__main__':
    if not os.getenv('GEMINI_API_KEY'):
        raise RuntimeError('GEMINI_API_KEY missing from environment')
    response = genai.Client().models.generate_content(
        model=os.getenv('LAB_MODEL', 'gemini-3.5-flash-lite'),
        contents="Reply with the exact phrase: 'Telemetry online.'"
    )
    print(response.text)
