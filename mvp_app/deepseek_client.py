import os
import json
import time
import requests
from typing import Optional

# Note: read environment variables at runtime inside call_deepseek to allow tests to monkeypatch env
DEBUG_LOG = os.path.join(os.path.dirname(__file__), 'outputs', 'deepseek_debug.log')


def _log_debug(msg: str):
    try:
        os.makedirs(os.path.join(os.path.dirname(__file__), 'outputs'), exist_ok=True)
        with open(DEBUG_LOG, 'a', encoding='utf-8') as f:
            f.write(msg + '\n')
    except Exception:
        pass


def _parse_response_text(resp_text: str, resp_json: Optional[dict]):
    """Try to extract a useful text from JSON or plain text response."""
    if resp_json and isinstance(resp_json, dict):
        # Common fields
        if 'text' in resp_json and isinstance(resp_json['text'], str):
            return resp_json['text']
        if 'result' in resp_json and isinstance(resp_json['result'], str):
            return resp_json['result']
        if 'choices' in resp_json and isinstance(resp_json['choices'], list) and resp_json['choices']:
            c = resp_json['choices'][0]
            if isinstance(c, dict):
                if 'text' in c and isinstance(c['text'], str):
                    return c['text']
                if 'message' in c and isinstance(c['message'], dict) and 'content' in c['message']:
                    return c['message']['content']
        # sometimes the API returns data: {0: {text:...}} or data[0]
        if 'data' in resp_json:
            d = resp_json['data']
            if isinstance(d, dict):
                for v in d.values():
                    if isinstance(v, dict) and 'text' in v:
                        return v['text']
            if isinstance(d, list) and d and isinstance(d[0], dict) and 'text' in d[0]:
                return d[0]['text']
    # fallback to plain text
    if isinstance(resp_text, str) and resp_text.strip():
        return resp_text.strip()
    return ''


def summarize_saved_examples(limit: int = 5):
    """Aggregate saved success examples and return top entries sorted by a score.

    Score = frequency + freshness, where freshness = 1 / (1 + age_days).
    Returns list of aggregated entries: { 'key', 'format', 'body', 'freq', 'latest_ts', 'score' }
    """
    try:
        success_file = os.path.join(os.path.dirname(__file__), 'outputs', 'deepseek_success_examples.json')
        if not os.path.exists(success_file):
            return []
        with open(success_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        # aggregate by body (deterministic key)
        groups = {}
        for e in data:
            body = e.get('body') or {}
            try:
                key = json.dumps(body, sort_keys=True, ensure_ascii=False)
            except Exception:
                key = str(body)
            rec = groups.get(key, {'body': body, 'format': e.get('format'), 'freq': 0, 'latest_ts': e.get('timestamp')})
            rec['freq'] = rec.get('freq', 0) + 1
            # take the latest timestamp
            ts = e.get('timestamp')
            if ts and (not rec.get('latest_ts') or ts > rec.get('latest_ts')):
                rec['latest_ts'] = ts
                rec['format'] = e.get('format')
                rec['body'] = body
            groups[key] = rec
        # compute score
        now = None
        try:
            from datetime import datetime, timezone
            now = datetime.utcnow().replace(tzinfo=timezone.utc)
        except Exception:
            now = None
        entries = []
        for k, rec in groups.items():
            latest_ts = rec.get('latest_ts')
            freshness = 0.0
            if latest_ts and now:
                try:
                    ts = latest_ts.rstrip('Z')
                    from datetime import datetime
                    ts_dt = datetime.fromisoformat(ts)
                    age_days = (now - ts_dt).total_seconds() / 86400.0
                    freshness = 1.0 / (1.0 + max(0.0, age_days))
                except Exception:
                    freshness = 0.0
            score = rec.get('freq', 0) + freshness
            entries.append({'key': k, 'format': rec.get('format'), 'body': rec.get('body'), 'freq': rec.get('freq', 0), 'latest_ts': rec.get('latest_ts'), 'score': score})
        entries_sorted = sorted(entries, key=lambda e: e['score'], reverse=True)
        return entries_sorted[:limit]
    except Exception as e:
        _log_debug(f'Failed to summarize saved examples: {repr(e)}')
        return []


def call_deepseek(prompt: str, max_tokens: int = 800, temperature: float = 0.0) -> str:
    """Call a DeepSeek-compatible LLM endpoint with automatic payload format detection.

    Tries multiple common payload formats (OpenAI chat style, simple prompt, input) and returns
    the first non-empty text extracted from the response. Writes debug log to `outputs/deepseek_debug.log`.

    Raises RuntimeError if DEEPSEEK_URL or DEEPSEEK_API_KEY not configured.
    """
    # Read runtime config to allow tests to override environment
    DEEPSEEK_URL = os.getenv('DEEPSEEK_URL')
    DEEPSEEK_API_KEY = os.getenv('DEEPSEEK_API_KEY')
    DEEPSEEK_MODEL = os.getenv('DEEPSEEK_MODEL')

    if not DEEPSEEK_URL or not DEEPSEEK_API_KEY:
        raise RuntimeError('DeepSeek URL or API key not configured')

    headers = {'Authorization': f'Bearer {DEEPSEEK_API_KEY}', 'Content-Type': 'application/json'}

    import random
    import datetime

    formats = []
    # Minimal/simple payloads first (avoid model unless necessary)
    formats.append(('text', lambda: {'text': prompt}))
    formats.append(('prompt', lambda: {'prompt': prompt, 'max_tokens': max_tokens, 'temperature': temperature}))
    formats.append(('input', lambda: {'input': prompt, 'max_tokens': max_tokens, 'temperature': temperature}))
    formats.append(('input_wrapped', lambda: {'input': {'text': prompt}, 'max_tokens': max_tokens, 'temperature': temperature}))
    # OpenAI-style chat without explicit model
    formats.append(('openai_chat_simple_nomodel', lambda: {'messages': [{'role': 'user', 'content': prompt}], 'temperature': temperature, 'max_tokens': max_tokens}))
    formats.append(('openai_chat_system_nomodel', lambda: {'messages': [{'role': 'system', 'content': '你是教学助理。'}, {'role': 'user', 'content': prompt}], 'temperature': temperature, 'max_tokens': max_tokens}))
    # If a model name is provided, include model-bearing variants last
    if DEEPSEEK_MODEL:
        formats.append(('prompt_with_model', lambda: {'model': DEEPSEEK_MODEL, 'prompt': prompt, 'max_tokens': max_tokens, 'temperature': temperature}))
        formats.append(('openai_chat_simple', lambda: {'model': DEEPSEEK_MODEL, 'messages': [{'role': 'user', 'content': prompt}], 'temperature': temperature, 'max_tokens': max_tokens}))
        formats.append(('openai_chat_system', lambda: {'model': DEEPSEEK_MODEL, 'messages': [{'role': 'system', 'content': '你是教学助理。'}, {'role': 'user', 'content': prompt}], 'temperature': temperature, 'max_tokens': max_tokens}))

    def _persist_success_example(entry: dict):
        try:
            success_file = os.path.join(os.path.dirname(__file__), 'outputs', 'deepseek_success_examples.json')
            os.makedirs(os.path.join(os.path.dirname(__file__), 'outputs'), exist_ok=True)
            existing = []
            if os.path.exists(success_file):
                try:
                    with open(success_file, 'r', encoding='utf-8') as f:
                        existing = json.load(f)
                except Exception:
                    existing = []
            existing.append(entry)
            with open(success_file, 'w', encoding='utf-8') as f:
                json.dump(existing, f, ensure_ascii=False, indent=2)
        except Exception as e:
            _log_debug(f'Failed to persist success example: {repr(e)}')

    last_exc = None

    # First: if there are saved successful examples, try them first (most recent first)
    saved_examples = summarize_saved_examples()
    for example in saved_examples:
        try:
            name = f"saved:{example.get('format') or 'saved'}"
            body = example.get('body') or {}
            _log_debug(f'Trying saved example {name} (score={example.get("score")}) with body keys: {list(body.keys())} and body sample: {str(list(body.items())[:2])}')
            # attempt single request with same 403/backoff logic but limited
            resp = requests.post(DEEPSEEK_URL, headers=headers, json=body, timeout=30)
            _log_debug(f'Saved example {name} -> status {resp.status_code} response_snippet: {resp.text[:200]}')
            if resp.status_code == 403:
                _log_debug(f'Saved example {name} -> 403 (rate limit), will fall through to normal probing')
            elif resp.status_code >= 400:
                _log_debug(f'Saved example {name} -> {resp.status_code} (bad), will fall through to normal probing')
            else:
                try:
                    j = resp.json()
                except ValueError:
                    j = None
                text = _parse_response_text(resp.text, j)
                if text:
                    _log_debug(f'Saved example {name} succeeded, extracted text length {len(text)}')
                    return text
        except Exception as e:
            _log_debug(f'Saved example {example.get("format")} exception: {repr(e)}')

    # If saved examples didn't work, proceed with probing standard formats
    for name, body_fn in formats:
        body = body_fn()
        _log_debug(f'Trying format {name} with body keys: {list(body.keys())} and body sample: {str(list(body.items())[:2])}')
        try:
            # Request with simple retry-on-403/backoff policy
            max_403_retries = 3
            attempt = 0
            while True:
                resp = requests.post(DEEPSEEK_URL, headers=headers, json=body, timeout=30)
                _log_debug(f'Format {name} -> status {resp.status_code} response_snippet: {resp.text[:200]}')
                # 403: rate limiting / account issue -> backoff and retry a few times
                if resp.status_code == 403:
                    attempt += 1
                    if attempt > max_403_retries:
                        last_exc = requests.HTTPError(f'{resp.status_code} {resp.text}')
                        _log_debug(f'Format {name} -> 403 after {attempt} attempts, giving up')
                        break
                    backoff = (2 ** attempt) + random.random() * 0.5
                    _log_debug(f'Format {name} -> 403 detected, backing off {backoff:.2f}s and retrying')
                    time.sleep(backoff)
                    continue
                # 400-level errors (parameter errors) -> try next format
                if resp.status_code >= 400:
                    last_exc = requests.HTTPError(f'{resp.status_code} {resp.text}')
                    break
                # try to parse
                try:
                    j = resp.json()
                except ValueError:
                    j = None
                text = _parse_response_text(resp.text, j)
                if text:
                    _log_debug(f'Format {name} succeeded, extracted text length {len(text)}')
                    # save success example for future reference
                    try:
                        entry = {
                            'format': name,
                            'body': body,
                            'headers': headers,
                            'status_code': resp.status_code,
                            'response_snippet': text[:200],
                            'timestamp': datetime.datetime.utcnow().isoformat() + 'Z'
                        }
                        _persist_success_example(entry)
                    except Exception as e:
                        _log_debug(f'Failed to save success example: {repr(e)}')
                    return text
                last_exc = RuntimeError('No usable text in response')
                break
        except Exception as e:
            last_exc = e
            _log_debug(f'Format {name} exception: {repr(e)}')
        # small backoff before next attempt
        time.sleep(0.3)

    _log_debug(f'All formats failed, last_exc={repr(last_exc)}')
    if last_exc:
        raise last_exc
    return ''
