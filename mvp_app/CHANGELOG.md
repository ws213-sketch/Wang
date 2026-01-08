# Changelog

## 2026-01-08 — Feature & Reliability Improvements ✅

- **DeepSeek client**
  - 优先使用最小/简洁 payload（例如 `text` / `prompt` / `input`），避免先发送 `model` 导致的 `Model does not exist` 错误。
  - 增加对多种 payload 的自动探测与解析（OpenAI-style variants、prompt、input、wrapped 等）。
  - **持久化成功样例**到 `outputs/deepseek_success_examples.json`，包含 `format`、`body`、`headers`、`status_code`、`response_snippet`、`timestamp` 等元数据。
  - 添加 **优先回放**逻辑：按成功频次与新鲜度给样例加权排序（score = freq + freshness），优先尝试高权重样例以提高成功率。
  - 对 `403`（RPM limit）实现指数退避（带抖动），并在多次失败后给出明确错误；对 400 型参数错误则尝试更简洁的 payload。

- **Reporting & UX**
  - 增加 `run_prompt_comparison.generate_report()`，输出：
    - `outputs/prompt_comparison.json`（对比结果）
    - `outputs/deepseek_examples_report.md`（Markdown 报告）
    - `outputs/deepseek_examples.csv`（CSV 导出）
    - `outputs/deepseek_examples_report.html`（HTML 报告，含可复制的 `curl` 示例）
  - HTML 报告增强：可复制 `curl` 的 **Copy 按钮**（含内联 SVG 图标、无障碍 `aria-label`）、复制成功视觉反馈、以及主题切换（亮/暗）和动画效果（平滑过渡）。
  - 视觉微调：按钮与页面使用不同的缓动曲线以获得更自然的交互体验（页面过渡 `cubic-bezier(0.4,0,0.2,1)`；按钮 `cubic-bezier(0.2,0,0.2,1)`；主题动画时长已调整为 460ms）。

- **Tests & Quality**
  - 新增/扩展单元测试：覆盖 DeepSeek payload 探测、403/backoff、保存与回放、报告导出与 HTML 内容（`tests/test_deepseek_formats.py`, `tests/test_run_prompt_comparison.py` 等）。
  - 全量测试通过：**18 passed**。

- **Files changed / added (关键列表)**
  - Modified: `deepseek_client.py` (payload probing, persistence, backoff, summarize logic)
  - Modified: `run_prompt_comparison.py` (report generation, HTML/MD/CSV/HTML exports, copy buttons, theme toggle, animations)
  - Modified: `tests/test_deepseek_formats.py`, `tests/test_run_prompt_comparison.py` (新增/扩展测试)
  - Added: `outputs/deepseek_success_examples.json` (runtime artifact when runs succeed)
  - Added: `CHANGELOG.md` (本条目)

---

### Suggested Git commit

```bash
git add deepseek_client.py run_prompt_comparison.py tests/test_deepseek_formats.py tests/test_run_prompt_comparison.py mvp_app/CHANGELOG.md
git commit -m "feat(deepseek): robust payload probing, success example persistence, backoff; add reporting and HTML UI improvements"
```

### Test & Usage

- 运行测试：

```bash
pytest -q
```

- 生成报告并查看 HTML：

```bash
python -m mvp_app.run_prompt_comparison
# 打开 mvp_app/outputs/deepseek_examples_report.html
```

---

需要我现在为你执行 `git add` + `git commit`（使用上面建议的 commit message）并 push 到远程分支吗？如果需要，请确认（我将执行并回复结果）。