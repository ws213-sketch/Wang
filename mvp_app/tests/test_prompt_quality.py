from summarizer import build_few_shot_examples, normalize_result, try_extract_json


def test_few_shot_examples_exist():
    exs = build_few_shot_examples()
    assert isinstance(exs, list)
    assert len(exs) >= 2


def test_normalize_on_bad_input():
    bad = 'not json'
    nr = normalize_result(bad)
    assert 'learn_points' in nr and 'confusions' in nr


def test_try_extract_json_from_text():
    s = 'abc {"learn_points":["点1"], "confusions":[]} xyz'
    parsed = try_extract_json(s)
    assert parsed and 'learn_points' in parsed
