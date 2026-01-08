from summarizer import try_extract_json, try_brutal_json_search, normalize_result


def test_try_extract_json_with_text():
    s = '前面是文字，下面是结果：{"learn_points": ["点1"], "confusions": []} 结束'
    parsed = try_extract_json(s)
    assert parsed is not None
    assert 'learn_points' in parsed


def test_normalize_result_empty_or_bad():
    bad = 'not a json'
    nr = normalize_result(bad)
    assert 'learn_points' in nr and isinstance(nr['learn_points'], list)


def test_normalize_truncation():
    obj = {'learn_points': ['这是一个很长的学习点，需要被截断以确保输出不要太长'*2], 'confusions':[{'left':'A','right':'B','explain':'解释'*100,'example':'例子'*100}]}
    nr = normalize_result(obj)
    assert len(nr['learn_points']) == 1
    assert len(nr['confusions']) == 1
    assert len(nr['confusions'][0]['explain']) < 200
