import pytest
from summarizer import try_extract_json, try_brutal_json_search, fallback_summarize


def test_try_extract_json_basic():
    s = 'Here is some text {"learn_points": ["点1"], "confusions": []} end'
    parsed = try_extract_json(s)
    assert parsed is not None
    assert 'learn_points' in parsed


def test_try_brutal_json_search_codeblock():
    s = '```json\n{"learn_points":["a"]}\n```'
    parsed = try_brutal_json_search(s)
    assert parsed is not None
    assert parsed['learn_points'][0] == 'a'


def test_fallback_summarize_minimal():
    s = '这是一个测试题目：求导数的定义并举例。'
    res = fallback_summarize(s)
    assert 'learn_points' in res
    assert 'confusions' in res
