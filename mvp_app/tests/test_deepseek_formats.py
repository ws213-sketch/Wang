import sys
import os
import json
import requests
# ensure local package directory is on sys.path for imports when running tests from repo root
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from deepseek_client import call_deepseek

class DummyResp:
    def __init__(self, status_code=200, text='', j=None):
        self.status_code = status_code
        self._text = text
        self._json = j
    def json(self):
        if self._json is None:
            raise ValueError('No JSON')
        return self._json
    @property
    def text(self):
        return self._text


def test_try_prompt_then_openai(monkeypatch):
    # First format (openai_chat) returns 400, second (prompt) returns JSON with text
    calls = {'count':0}
    def fake_post(url, headers=None, json=None, timeout=None):
        calls['count'] += 1
        if calls['count'] == 1:
            return DummyResp(status_code=400, text='bad')
        # second attempt returns expected json
        return DummyResp(status_code=200, j={'text':'ok prompt'})

    monkeypatch.setenv('DEEPSEEK_URL','http://fake')
    monkeypatch.setenv('DEEPSEEK_API_KEY','fake')
    monkeypatch.setenv('DEEPSEEK_MODEL','deepseek-r1')
    monkeypatch.setattr(requests, 'post', fake_post)

    out = call_deepseek('hello')
    assert out == 'ok prompt'


def test_openai_style_returns_choices(monkeypatch):
    def fake_post(url, headers=None, json=None, timeout=None):
        return DummyResp(status_code=200, j={'choices':[{'message':{'content':'reply from choices'}}]})
    monkeypatch.setenv('DEEPSEEK_URL','http://fake')
    monkeypatch.setenv('DEEPSEEK_API_KEY','fake')
    monkeypatch.setenv('DEEPSEEK_MODEL','deepseek-r1')
    monkeypatch.setattr(requests, 'post', fake_post)
    out = call_deepseek('hello2')
    assert 'reply from choices' in out


def test_minimal_text_payload_tried_first_and_persist(monkeypatch, tmp_path):
    # Ensure DEEPSEEK_MODEL is not set so we try minimal payloads first
    monkeypatch.setenv('DEEPSEEK_URL','http://fake')
    monkeypatch.setenv('DEEPSEEK_API_KEY','fake')
    monkeypatch.delenv('DEEPSEEK_MODEL', raising=False)

    # Remove any existing success file
    import os
    success_file = os.path.join(os.path.dirname(__file__), '..', 'deepseek_success_examples.json')
    success_file = os.path.abspath(success_file)
    try:
        if os.path.exists(success_file):
            os.remove(success_file)
    except Exception:
        pass

    calls = {'bodies': []}
    def fake_post(url, headers=None, json=None, timeout=None):
        calls['bodies'].append(json)
        # succeed on first minimal 'text' payload
        if json and 'text' in json:
            return DummyResp(status_code=200, text='plain reply')
        return DummyResp(status_code=400, text='bad')

    monkeypatch.setattr(requests, 'post', fake_post)

    out = call_deepseek('sample prompt')
    assert out == 'plain reply'
    # ensure at least one attempted payload included the minimal 'text' key
    assert any(isinstance(b, dict) and 'text' in b for b in calls['bodies'])

    # check persisted file exists and contains an entry with format 'text'
    # success file is located under package outputs; adjust path
    pkg_dir = os.path.dirname(os.path.dirname(__file__))
    persisted = os.path.join(pkg_dir, 'outputs', 'deepseek_success_examples.json')
    assert os.path.exists(persisted)
    with open(persisted, 'r', encoding='utf-8') as f:
        data = json.load(f)
    assert any(e.get('format') == 'text' for e in data)


def test_saved_example_playback(monkeypatch, tmp_path):
    monkeypatch.setenv('DEEPSEEK_URL','http://fake')
    monkeypatch.setenv('DEEPSEEK_API_KEY','fake')
    monkeypatch.delenv('DEEPSEEK_MODEL', raising=False)

    # create a saved example file under package outputs
    pkg_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    outputs_dir = os.path.join(pkg_dir, 'outputs')
    os.makedirs(outputs_dir, exist_ok=True)
    saved_file = os.path.join(outputs_dir, 'deepseek_success_examples.json')
    saved_entry = [{'format': 'saved_text', 'body': {'text': 'replay'}, 'response_snippet': 'replay snippet', 'timestamp': '2026-01-01T00:00:00Z'}]
    with open(saved_file, 'w', encoding='utf-8') as f:
        json.dump(saved_entry, f, ensure_ascii=False, indent=2)

    calls = {'bodies': []}
    def fake_post(url, headers=None, json=None, timeout=None):
        calls['bodies'].append(json)
        # if the body matches saved example, return success
        if json and json.get('text') == 'replay':
            return DummyResp(status_code=200, text='ok from saved')
        return DummyResp(status_code=400, text='bad')

    monkeypatch.setattr(requests, 'post', fake_post)

    out = call_deepseek('ignored prompt')
    assert out == 'ok from saved'
    # ensure first request used the saved example body
    assert calls['bodies'] and calls['bodies'][0].get('text') == 'replay'

    # cleanup
    try:
        os.remove(saved_file)
    except Exception:
        pass


def test_saved_example_scoring_and_order(monkeypatch):
    monkeypatch.setenv('DEEPSEEK_URL','http://fake')
    monkeypatch.setenv('DEEPSEEK_API_KEY','fake')
    monkeypatch.delenv('DEEPSEEK_MODEL', raising=False)

    pkg_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    outputs_dir = os.path.join(pkg_dir, 'outputs')
    os.makedirs(outputs_dir, exist_ok=True)
    saved_file = os.path.join(outputs_dir, 'deepseek_success_examples.json')

    # create entries: two identical 'old' bodies (freq=2, older ts), and one recent body (freq=1, recent ts)
    old_entry1 = {'format': 'old', 'body': {'text': 'old'}, 'response_snippet': 'old1', 'timestamp': '2025-12-01T00:00:00Z'}
    old_entry2 = {'format': 'old', 'body': {'text': 'old'}, 'response_snippet': 'old2', 'timestamp': '2025-12-05T00:00:00Z'}
    recent_entry = {'format': 'recent', 'body': {'text': 'recent'}, 'response_snippet': 'recent', 'timestamp': '2026-01-01T00:00:00Z'}
    with open(saved_file, 'w', encoding='utf-8') as f:
        json.dump([old_entry1, old_entry2, recent_entry], f, ensure_ascii=False, indent=2)

    calls = {'bodies': []}
    def fake_post(url, headers=None, json=None, timeout=None):
        calls['bodies'].append(json)
        # succeed only if body matches the top-ranked example; we expect 'old' to have higher score (freq 2)
        if json and json.get('text') == 'old':
            return DummyResp(status_code=200, text='ok old')
        if json and json.get('text') == 'recent':
            return DummyResp(status_code=200, text='ok recent')
        return DummyResp(status_code=400, text='bad')

    monkeypatch.setattr(requests, 'post', fake_post)

    out = call_deepseek('ignored')
    # the first attempted saved example should be the 'old' one (higher freq)
    assert calls['bodies'] and calls['bodies'][0].get('text') == 'old'
    assert out == 'ok old'

    # cleanup
    try:
        os.remove(saved_file)
    except Exception:
        pass


def test_403_backoff_then_success(monkeypatch):
    monkeypatch.setenv('DEEPSEEK_URL','http://fake')
    monkeypatch.setenv('DEEPSEEK_API_KEY','fake')
    monkeypatch.delenv('DEEPSEEK_MODEL', raising=False)

    calls = {'count':0}
    def fake_post(url, headers=None, json=None, timeout=None):
        calls['count'] += 1
        if calls['count'] < 3:
            return DummyResp(status_code=403, text='RPM limit exceeded')
        return DummyResp(status_code=200, j={'text':'ok after backoff'})

    monkeypatch.setattr(requests, 'post', fake_post)
    # speed up backoff
    monkeypatch.setattr('time.sleep', lambda s: None)

    out = call_deepseek('prompt')
    assert out == 'ok after backoff'


def test_403_give_up(monkeypatch):
    monkeypatch.setenv('DEEPSEEK_URL','http://fake')
    monkeypatch.setenv('DEEPSEEK_API_KEY','fake')
    monkeypatch.delenv('DEEPSEEK_MODEL', raising=False)

    def fake_post(url, headers=None, json=None, timeout=None):
        return DummyResp(status_code=403, text='RPM limit exceeded')

    monkeypatch.setattr(requests, 'post', fake_post)
    monkeypatch.setattr('time.sleep', lambda s: None)

    import pytest
    with pytest.raises(Exception) as excinfo:
        call_deepseek('prompt')
    assert '403' in str(excinfo.value)
