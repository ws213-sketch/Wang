# 学习卡片生成器（MVP）

一个最简可运行的原型：用户上传一张图片 → OCR 提取文字 → 用大模型（或回退算法）抽取“不会的知识点”和“混淆点并举例” → 生成可打印 PDF。

## 特点
- 后端：Flask
- OCR：pytesseract（需要本机安装 Tesseract）
- LLM：支持 `OPENAI_API_KEY`（可选），若未配置则使用本地回退的简易摘要器
- PDF：使用 ReportLab 生成

## 快速开始
1. 安装依赖：
```bash
python -m pip install -r requirements.txt
```
2. 安装 Tesseract：
   - Windows: https://github.com/tesseract-ocr/tesseract/releases 下载对应安装程序并配置 PATH
3. 复制 `.env.example` 为 `.env` 并（可选）设置 `OPENAI_API_KEY`
4. 运行服务：
```bash
set FLASK_APP=app.py
set FLASK_ENV=development
flask run
```
5. 打开浏览器访问 `http://127.0.0.1:5000`，上传图片并查看结果。

可选：启用 Google Vision OCR（更强手写识别与文档理解）
- 安装：`pip install google-cloud-vision`
- 设置环境变量：`set GOOGLE_APPLICATION_CREDENTIALS=C:\path\to\your\key.json`（Windows）
- 启用：设置 `USE_GOOGLE_VISION=1` 环境变量

测试：运行 `pytest tests` 来执行基本的单元测试。

## 说明
- 若你设置了 `OPENAI_API_KEY`，后端会调用 OpenAI API 获取更优结果；否则会使用内置回退算法，确保软件可离线运行。

欢迎告诉我是否要我把这个工程打包成 Docker 或继续改进模型提示和 UI。