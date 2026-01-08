import sys
import os
import json
from pathlib import Path

# ensure local package is importable
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import run_prompt_comparison as rpc


def test_generate_report_writes_files(monkeypatch, tmp_path):
    # monkeypatch summarize to avoid external LLM calls
    monkeypatch.setattr('run_prompt_comparison.summarize', lambda t: {'learn_points': ['dummy'], 'confusions': []})

    # prepare saved examples under package outputs that summarize_saved_examples will read
    pkg_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    outputs_dir_pkg = os.path.join(pkg_dir, 'outputs')
    os.makedirs(outputs_dir_pkg, exist_ok=True)
    saved_file = os.path.join(outputs_dir_pkg, 'deepseek_success_examples.json')
    saved_entry = [{'format': 'text', 'body': {'text': 'replay'}, 'response_snippet': 'replay', 'timestamp': '2026-01-01T00:00:00Z'}]
    with open(saved_file, 'w', encoding='utf-8') as f:
        json.dump(saved_entry, f, ensure_ascii=False, indent=2)

    out_dir = str(tmp_path / 'outputs')
    res = rpc.generate_report(out_dir=out_dir)

    # check JSON output
    out_json = os.path.join(out_dir, 'prompt_comparison.json')
    assert os.path.exists(out_json)
    with open(out_json, 'r', encoding='utf-8') as f:
        doc = json.load(f)
    assert 'results' in doc and 'saved_examples' in doc

    # check report files
    md = os.path.join(out_dir, 'deepseek_examples_report.md')
    csv = os.path.join(out_dir, 'deepseek_examples.csv')
    html = os.path.join(out_dir, 'deepseek_examples_report.html')
    assert os.path.exists(md)
    assert os.path.exists(csv)
    assert os.path.exists(html)
    # ensure HTML contains sample payload 'replay'
    with open(html, 'r', encoding='utf-8') as h:
        content = h.read()
    assert 'replay' in content
    # ensure copy button and clipboard JS exist
    assert 'class="copy-btn"' in content
    assert 'navigator.clipboard.writeText' in content
    # ensure the SVG icon and copied-state styles exist
    assert '<svg' in content
    assert 'class="icon-svg"' in content
    assert 'aria-label="Copy cURL"' in content
    assert '.copy-btn.copied' in content
    # ensure theme toggle, theme-transition and prefers-color-scheme CSS present
    assert 'id="theme-toggle"' in content
    assert 'prefers-color-scheme' in content
    assert 'theme-transition' in content
    assert 'matchMedia' in content
    # ensure the new animation cubic-bezier timing and button cubic-bezier are present
    assert 'cubic-bezier(0.4,0,0.2,1)' in content
    assert 'cubic-bezier(0.2,0,0.2,1)' in content
    assert ('0.16s' in content or '160ms' in content)

    # cleanup
    try:
        os.remove(saved_file)
    except Exception:
        pass
