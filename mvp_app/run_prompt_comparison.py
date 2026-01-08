import os
import json
from summarizer import summarize

BASE = os.path.dirname(__file__)
OUT = os.path.join(BASE, 'outputs', 'prompt_comparison.json')
texts = [
    "求导数的定义并举例。",
    "偏导数和全导数有什么不同？请说明并举例。",
    "解释行列式和矩阵的区别，给出一个类比帮助记忆。"
]

def generate_report(out_dir: str | None = None, texts_list=None):
    """Generate prompt comparison and saved example reports into out_dir (defaults to package outputs).

    Returns a dict with results and saved_examples summary.
    """
    if texts_list is None:
        texts_list = texts
    BASE_OUT = out_dir or os.path.join(BASE, 'outputs')
    os.makedirs(BASE_OUT, exist_ok=True)

    results = []
    for t in texts_list:
        res = summarize(t)
        results.append({'text': t, 'result': res})

    # include saved example summary for debugging and suggestions
    try:
        from deepseek_client import summarize_saved_examples
        saved = summarize_saved_examples(limit=10)
        saved_summary = [{'format': e['format'], 'freq': e['freq'], 'latest_ts': e['latest_ts'], 'score': e['score'], 'body': e['body']} for e in saved]
    except Exception:
        saved_summary = []

    out_json = os.path.join(BASE_OUT, 'prompt_comparison.json')
    with open(out_json, 'w', encoding='utf-8') as f:
        json.dump({'results': results, 'saved_examples': saved_summary}, f, ensure_ascii=False, indent=2)

    # produce human-friendly markdown, CSV and HTML reports
    report_md = os.path.join(BASE_OUT, 'deepseek_examples_report.md')
    report_csv = os.path.join(BASE_OUT, 'deepseek_examples.csv')
    report_html = os.path.join(BASE_OUT, 'deepseek_examples_report.html')
    try:
        # Markdown
        with open(report_md, 'w', encoding='utf-8') as m:
            m.write('# DeepSeek Discovered Payload Examples and Recommendations\n\n')
            m.write('This report lists saved payload examples discovered during probing runs, scored by frequency and freshness.\n\n')
            if not saved_summary:
                m.write('No saved examples found.\n')
            else:
                for e in saved_summary:
                    m.write(f"## Format: {e['format']} (score={e['score']:.3f})\n")
                    m.write(f"- Frequency: {e['freq']}\n")
                    m.write(f"- Latest seen: {e['latest_ts']}\n")
                    m.write('\n')
                    m.write('Sample payload:\n')
                    m.write('```json\n')
                    m.write(json.dumps(e['body'], ensure_ascii=False, indent=2))
                    m.write('\n```\n\n')
                m.write('**Recommendation:** Prefer high-score payloads first; if these fail, try simpler payloads (e.g., `text` or `prompt` without `model`).\n')
                m.write('\nContact DeepSeek support with an example payload and the `response_snippet` if you see repeated 400/403 errors.\n')

        # write CSV
        import csv
        with open(report_csv, 'w', encoding='utf-8', newline='') as c:
            writer = csv.writer(c)
            writer.writerow(['format','freq','latest_ts','score','body_json'])
            for e in saved_summary:
                writer.writerow([e['format'], e['freq'], e['latest_ts'], f"{e['score']:.6f}", json.dumps(e['body'], ensure_ascii=False)])

        # write HTML
        try:
            import html
            with open(report_html, 'w', encoding='utf-8') as h:
                h.write('<!doctype html>\n<html><head><meta charset="utf-8"><title>DeepSeek Examples Report</title>')
                h.write('<style>/* layout */table{border-collapse:collapse;width:100%}td,th{border:1px solid var(--border);padding:8px;vertical-align:top}th{background:var(--th-bg);text-align:left} pre{white-space:pre-wrap;word-break:break-word}/* buttons */ .copy-btn{background:var(--btn-bg);border:1px solid var(--btn-border);padding:6px 10px;border-radius:6px;cursor:pointer;font-size:13px;display:inline-flex;align-items:center;gap:8px;color:var(--btn-color)} .copy-btn .icon-svg{width:18px;height:18px;display:inline-block;vertical-align:middle} .copy-btn.copied{background:#28a745;color:#fff;border-color:#28a745;box-shadow:0 2px 6px rgba(40,167,69,0.2)} .copy-btn.copied .icon-svg{filter:brightness(0) invert(1)} .copy-btn:focus{outline:2px solid #69c;outline-offset:2px} button.copy-btn{transition:all 0.16s cubic-bezier(0.2,0,0.2,1)}/* transitions for theme changes */ .theme-transition, .theme-transition *{transition:background-color 0.4s cubic-bezier(0.4,0,0.2,1),color 0.4s cubic-bezier(0.4,0,0.2,1),border-color 0.4s cubic-bezier(0.4,0,0.2,1),box-shadow 0.4s cubic-bezier(0.4,0,0.2,1)}/* theming */:root{--bg:#ffffff;--text:#111111;--border:#ddd;--th-bg:#f7f7f7;--btn-bg:#fff;--btn-border:#ccc;--btn-color:#111}@media (prefers-color-scheme: dark){:root{--bg:#0e0f11;--text:#e6e6e6;--border:#222;--th-bg:#131416;--btn-bg:#0f1720;--btn-border:#2b3036;--btn-color:#e6e6e6}}body.dark{--bg:#0e0f11;--text:#e6e6e6;--border:#222;--th-bg:#131416;--btn-bg:#0f1720;--btn-border:#2b3036;--btn-color:#e6e6e6}body{background:var(--bg);color:var(--text);font-family:Segoe UI,Roboto,Arial,Helvetica,sans-serif;margin:18px;transition:background-color .4s cubic-bezier(0.4,0,0.2,1),color .4s cubic-bezier(0.4,0,0.2,1)}#theme-toggle{position:fixed;right:18px;top:18px;background:transparent;border:1px solid var(--btn-border);padding:6px 10px;border-radius:6px;color:var(--btn-color);cursor:pointer}#theme-toggle:focus{outline:2px solid #69c;outline-offset:2px}</style>')
                h.write('</head><body>')
                h.write('<h1>DeepSeek Discovered Payload Examples and Recommendations</h1>')
                h.write('<p>This report lists saved payload examples discovered during probing runs, scored by frequency and freshness.</p>')
                # theme toggle button
                h.write('<button id="theme-toggle" aria-label="Toggle light/dark theme">🌗 Theme</button>')
                if not saved_summary:
                    h.write('<p>No saved examples found.</p>')
                else:
                    h.write('<table>')
                    h.write('<thead><tr><th>format</th><th>freq</th><th>latest_ts</th><th>score</th><th>sample payload</th><th>curl</th><th>copy</th></tr></thead>')
                    h.write('<tbody>')
                    idx = 0
                    for e in saved_summary:
                        body_json = json.dumps(e['body'], ensure_ascii=False)
                        body_escaped = html.escape(body_json)
                        # curl snippet with placeholders (compact JSON)
                        body_json_compact = json.dumps(e['body'], ensure_ascii=False, separators=(',', ':'))
                        curl = f"curl -X POST 'https://YOUR_DEEPSEEK_ENDPOINT' -H 'Authorization: Bearer YOUR_API_KEY' -H 'Content-Type: application/json' -d '{body_json_compact}'"
                        curl_escaped = html.escape(curl)
                        curl_id = f'curl-{idx}'
                        btn_id = f'copy-btn-{idx}'
                        h.write('<tr>')
                        h.write(f"<td>{html.escape(str(e['format']))}</td>")
                        h.write(f"<td>{e['freq']}</td>")
                        h.write(f"<td>{html.escape(str(e['latest_ts']))}</td>")
                        h.write(f"<td>{e['score']:.6f}</td>")
                        h.write(f"<td><pre>{body_escaped}</pre></td>")
                        h.write(f"<td><pre id=\"{curl_id}\">{curl_escaped}</pre></td>")
                        # prettier button with icon + label
                        h.write(f"<td><button class=\"copy-btn\" id=\"{btn_id}\" data-target=\"{curl_id}\" aria-label=\"Copy cURL\"><svg class=\"icon-svg\" viewBox=\"0 0 24 24\" aria-hidden=\"true\" focusable=\"false\" xmlns=\"http://www.w3.org/2000/svg\"><path fill=\"currentColor\" d=\"M19 3h-4.18C14.4 1.84 13.3 1 12 1s-2.4.84-2.82 2H5a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2V5a2 2 0 0 0-2-2zM12 3c.55 0 1 .45 1 1s-.45 1-1 1-1-.45-1-1 .45-1 1-1zM7 7h10v2H7V7z\"></path></svg><span class=\"label\">Copy</span></button></td>")
                        h.write('</tr>')
                        idx += 1
                    h.write('</tbody></table>')
                    h.write('<p><strong>Recommendation:</strong> Prefer high-score payloads first; if these fail, try simpler payloads (e.g., <code>text</code> or <code>prompt</code> without <code>model</code>).')
                    h.write('<br>Contact DeepSeek support with an example payload and the response snippet if you see repeated 400/403 errors.</p>')
                    # add improved JS to implement copy-to-clipboard behavior with visual state
                    h.write("<script>\n")
                    h.write("document.addEventListener('click', function(ev){\n")
                    h.write("  const btn = ev.target.closest('.copy-btn');\n")
                    h.write("  if(!btn) return;\n")
                    h.write("  const targetId = btn.getAttribute('data-target');\n")
                    h.write("  if(!targetId) return;\n")
                    h.write("  const pre = document.getElementById(targetId);\n")
                    h.write("  if(!pre) return;\n")
                    h.write("  const text = pre.innerText;\n")
                    h.write("  // visual feedback: add copied class and change label\n")
                    h.write("  const label = btn.querySelector('.label');\n")
                    h.write("  const origLabel = label ? label.innerText : '';\n")
                    h.write("  function showCopied(){ btn.classList.add('copied'); if(label) label.innerText='Copied!'; setTimeout(()=>{ btn.classList.remove('copied'); if(label) label.innerText=origLabel; },1500); }\n")
                    h.write("  if(navigator && navigator.clipboard && navigator.clipboard.writeText){\n")
                    h.write("    navigator.clipboard.writeText(text).then(()=>{ showCopied(); }).catch(()=>{\n")
                    h.write("      // fallback to execCommand\n")
                    h.write("      const ta = document.createElement('textarea'); ta.value=text; document.body.appendChild(ta); ta.select(); try{document.execCommand('copy'); showCopied();}catch(e){} ta.remove();\n")
                    h.write("    });\n")
                    h.write("  }else{\n")
                    h.write("    const ta = document.createElement('textarea'); ta.value=text; document.body.appendChild(ta); ta.select(); try{document.execCommand('copy'); showCopied();}catch(e){} ta.remove();\n")
                    h.write("  }\n")
                    h.write("});\n")
                    # theme toggle script: remember in localStorage
                    h.write("(function(){ const tbtn=document.getElementById('theme-toggle'); if(!tbtn) return; function setDark(d){ if(d){document.body.classList.add('dark'); tbtn.innerText='🌙 Dark'; }else{document.body.classList.remove('dark'); tbtn.innerText='🌗 Theme'; } } try{ const pref=localStorage.getItem('ds_theme'); if(pref){ setDark(pref==='dark'); } else if(window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches){ setDark(true); } }catch(e){}\n")
                    h.write("  function animateTheme(){ document.body.classList.add('theme-transition'); setTimeout(()=>document.body.classList.remove('theme-transition'),460); }\n")
                    h.write("  // listen to system theme changes\n")
                    h.write("  try{ if(window.matchMedia){ const mq=window.matchMedia('(prefers-color-scheme: dark)'); if(mq.addEventListener){ mq.addEventListener('change', function(ev){ animateTheme(); setDark(ev.matches); }); } else if(mq.addListener){ mq.addListener(function(ev){ animateTheme(); setDark(ev.matches); }); } } }catch(e){}\n")
                    h.write("  tbtn.addEventListener('click', ()=>{ try{ animateTheme(); const willDark = !document.body.classList.contains('dark'); localStorage.setItem('ds_theme', willDark? 'dark':'light'); setDark(willDark); }catch(e){} }); })();\n")
                    h.write("</script>\n")
                h.write('</body></html>')
        except Exception as e:
            print('Failed to write HTML report:', repr(e))

    except Exception as e:
        print('Failed to write examples report:', repr(e))

    print('Prompt comparison written to', out_json)
    print('Examples report written to', report_md)
    return {'results': results, 'saved_examples': saved_summary}


if __name__ == '__main__':
    generate_report()

