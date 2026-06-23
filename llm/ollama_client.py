import requests
import json
import time
from typing import Optional

DEFAULT_HOST = 'http://127.0.0.1:11434'


def call_ollama(model: str, prompt: str, host: str = DEFAULT_HOST, max_tokens: int = 1024, temperature: float = 0.0, attempts: int = 3, backoff_factor: float = 1.0, timeout: int = 30) -> str:
    """Call local Ollama HTTP API /api/generate with retries.

    Attempts the request up to `attempts` times with exponential backoff.
    Returns the raw text output or raises RuntimeError after all retries fail.
    """
    url = f"{host}/api/generate"
    payload = {
        'model': model,
        'prompt': prompt,
        'max_tokens': max_tokens,
        'temperature': temperature,
    }

    last_exc: Optional[Exception] = None
    for attempt in range(1, attempts + 1):
        try:
            resp = requests.post(url, json=payload, timeout=timeout)
            resp.raise_for_status()
            data = resp.json()
            # Ollama responses may contain `choices` with `content` fields or `text`
            if isinstance(data, dict):
                if 'choices' in data and len(data['choices']) > 0:
                    c = data['choices'][0]
                    return c.get('content') or c.get('message') or json.dumps(c)
                if 'text' in data:
                    return data['text']
            return resp.text
        except Exception as e:
            last_exc = e
            if attempt < attempts:
                sleep_for = backoff_factor * (2 ** (attempt - 1))
                time.sleep(sleep_for)
                continue
            else:
                raise RuntimeError(f'Ollama call failed after {attempts} attempts: {e}') from e
