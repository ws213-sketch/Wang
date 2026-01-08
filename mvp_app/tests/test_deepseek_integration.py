from summarizer import summarize
import summarizer


def test_deepseek_flow(monkeypatch):
    # Simulate DeepSeek returning a JSON string
    fake_response = '{"learn_points": ["测试点1"], "confusions": [{"left":"A","right":"B","explain":"区别","example":"例子"}]}'

    def fake_call(prompt, max_tokens=800, temperature=0.0):
        return fake_response

    monkeypatch.setenv('LLM_BACKEND', 'deepseek')
    monkeypatch.setenv('DEEPSEEK_URL', 'http://example')
    monkeypatch.setenv('DEEPSEEK_API_KEY', 'fake')

    monkeypatch.setattr(summarizer, 'build_few_shot_examples', lambda: [("in","out")])
    import deepseek_client
    monkeypatch.setattr(deepseek_client, 'call_deepseek', fake_call)

    res = summarize('任意文本')
    assert isinstance(res, dict)
    assert 'learn_points' in res and res['learn_points'][0] == '测试点1'