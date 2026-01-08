import os
import json
from dotenv import load_dotenv
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader

# Load .env if present so OPENAI_API_KEY can be read when the module is imported
load_dotenv()
OPENAI_KEY = os.getenv('OPENAI_API_KEY')

# 尝试调用 OpenAI（可选），否则使用本地回退逻辑

def summarize(text):
    text = (text or '').strip()
    if not text:
        return {
            'learn_points': ['无法从图片中提取出明确的学习点，请拍清晰图片或补充文字。'],
            'confusions': []
        }

    # Determine backend: environment variable LLM_BACKEND can be 'deepseek' or 'openai'.
    backend = os.getenv('LLM_BACKEND', 'openai').lower()

    if backend == 'deepseek':
        try:
            from deepseek_client import call_deepseek
            # build prompt using the same few-shot examples
            examples = build_few_shot_examples()
            system = (
                "你是一个教学助理。输入是学生拍摄的题目或课堂笔记经 OCR 提取的文本。你的任务：\n"
                "1) 提取最多 6 条 `learn_points`（中文每条不超过 15 个字，或等价简短英文）；\n"
                "2) 提取 `confusions` 列表，项为 {left,right,explain,example}，其中 explain 不超过两行；\n"
                "严格要求：只返回一个有效的 JSON 对象，只包含顶层键 `learn_points` 和 `confusions`。输出语言：中文。"
            )
            user = '请仅以 JSON 返回分析结果；以下是几个示例（输入 → 输出）：\n'
            for inp, outp in examples:
                user += '输入：' + inp + '\n输出：' + json.dumps(outp, ensure_ascii=False) + '\n---\n'
            user += '\n现在请分析下面文本并仅返回 JSON：\n' + text

            content = call_deepseek(system + '\n' + user, max_tokens=800, temperature=0.0)
            parsed = try_extract_json(content) or try_brutal_json_search(content)
            if parsed is None:
                return normalize_result(fallback_summarize(text))
            return normalize_result(parsed)
        except Exception as e:
            print('DeepSeek 调用失败，使用回退算法：', e)
            return normalize_result(fallback_summarize(text))
    else:
        # fallback to OpenAI if configured
        if OPENAI_KEY:
            try:
                import openai
                openai.api_key = OPENAI_KEY

                def build_for_openai():
                    examples = build_few_shot_examples()
                    system = (
                        "你是一个教学助理。输入是学生拍摄的题目或课堂笔记经 OCR 提取的文本。你的任务：\n"
                        "1) 提取最多 6 条 `learn_points`（中文每条不超过 15 个字，或等价简短英文）；\n"
                        "2) 提取 `confusions` 列表，项为 {left,right,explain,example}，其中 explain 不超过两行；\n"
                        "严格要求：只返回一个有效的 JSON 对象，只包含顶层键 `learn_points` 和 `confusions`。输出语言：中文。"
                    )
                    examples = build_few_shot_examples()
                    user = '请仅以 JSON 返回分析结果；以下是几个示例（输入 → 输出）：\n'
                    for inp, outp in examples:
                        user += '输入：' + inp + '\n输出：' + json.dumps(outp, ensure_ascii=False) + '\n---\n'
                    user += '\n现在请分析下面文本并仅返回 JSON：\n' + text
                    return system, user

                system, user = build_for_openai()
                resp = openai.ChatCompletion.create(
                    model="gpt-4o-mini",
                    messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
                    max_tokens=800,
                    temperature=0.0
                )
                content = resp['choices'][0]['message']['content']
                parsed = try_extract_json(content) or try_brutal_json_search(content)
                if parsed is None:
                    follow = "请严格且仅输出一个有效的 JSON 对象，且不要附加任何解释或非 JSON 文本。"
                    resp2 = openai.ChatCompletion.create(
                        model="gpt-4o-mini",
                        messages=[{"role": "system", "content": system}, {"role": "user", "content": user}, {"role":"user","content":follow}],
                        max_tokens=400,
                        temperature=0.0
                    )
                    parsed = try_extract_json(resp2['choices'][0]['message']['content']) or try_brutal_json_search(resp2['choices'][0]['message']['content'])

                if parsed is None:
                    return normalize_result(fallback_summarize(text))
                return normalize_result(parsed)
            except Exception as e:
                print('OpenAI 调用失败，使用回退算法：', e)
                return normalize_result(fallback_summarize(text))
        else:
            return normalize_result(fallback_summarize(text))


def normalize_result(obj):
    """规范化输出：确保包含 learn_points 和 confusions，限制条数与长度，并用中文提示作为回退。"""
    if not isinstance(obj, dict):
        return {'learn_points': ['无法解析模型输出，请重试或补充文本。'], 'confusions': []}

    lp = obj.get('learn_points') if isinstance(obj.get('learn_points'), list) else []
    lp2 = []
    for item in lp[:6]:
        s = str(item).strip()
        if not s:
            continue
        if len(s) > 40:
            s = s[:37] + '...'
        lp2.append(s)
    if not lp2:
        lp2 = ['无法从文本中提取出明确的学习点，请拍清晰图片或补充文字。']

    confs = []
    for c in obj.get('confusions') or []:
        if not isinstance(c, dict):
            continue
        left = str(c.get('left','')).strip()
        right = str(c.get('right','')).strip()
        explain = str(c.get('explain','')).strip()
        example = str(c.get('example','')).strip()
        if len(explain) > 120:
            explain = explain[:116] + '...'
        if len(example) > 120:
            example = example[:116] + '...'
        if left or right:
            confs.append({'left':left,'right':right,'explain':explain,'example':example})
    # 若为空，提供通用示例以便用户查看
    if not confs:
        confs = [{'left':'导数','right':'微分','explain':'导数=瞬时变化率；微分=用于近似的增量。','example':'速度(导数) vs 小路程增量(微分)'}]

    return {'learn_points': lp2, 'confusions': confs}

def try_extract_json(s):
    """尝试定位并解析第一个 JSON 对象（平衡大括号）。"""
    s = s.strip()
    start = s.find('{')
    if start == -1:
        return None
    stack = []
    for i in range(start, len(s)):
        ch = s[i]
        if ch == '{':
            stack.append('{')
        elif ch == '}':
            if not stack:
                return None
            stack.pop()
            if not stack:
                candidate = s[start:i+1]
                try:
                    return json.loads(candidate)
                except Exception:
                    return None
    return None


def try_brutal_json_search(s):
    """更宽松的尝试：提取用反引号或代码块包裹的 JSON。"""
    import re
    # 搜索 ```json ... ``` 或 ``` ... ``` 或单行 `...`
    m = re.search(r'```json\s*(\{[\s\S]*?\})\s*```', s)
    if not m:
        m = re.search(r'```\s*(\{[\s\S]*?\})\s*```', s)
    if not m:
        m = re.search(r'`(\{[\s\S]*?\})`', s)
    if m:
        try:
            return json.loads(m.group(1))
        except Exception:
            return None
    return None


def build_few_shot_examples():
    """返回 few-shot 示例：（输入字符串，期望 JSON 输出 dict）。供 prompt 使用或测试引用。"""
    examples = []
    ex1_in = "定义：导数是函数在某点的瞬时变化率，几何上表示切线斜率。"
    ex1_out = {
        "learn_points": ["导数的几何意义：切线斜率"],
        "confusions": [{"left":"导数","right":"微分","explain":"导数表示瞬时变化率；微分用于近似增量。","example":"速度≈导数，路程小段≈微分"}]
    }
    examples.append((ex1_in, ex1_out))

    ex2_in = "偏导数与全导数：偏导数仅对单个变量求导，全导数考虑所有变量的联合作用。"
    ex2_out = {
        "learn_points": ["偏导数与全导数的含义"],
        "confusions": [{"left":"偏导数","right":"全导数","explain":"偏导数是对单变量求导；全导数包含所有变量的影响。","example":"温度关于时间和位置的全导数 vs 仅对时间的偏导数"}]
    }
    examples.append((ex2_in, ex2_out))

    ex3_in = "行列式与矩阵：矩阵是线性代数的基本对象，行列式是矩阵的一个标量特征。"
    ex3_out = {
        "learn_points": ["矩阵 vs 行列式"],
        "confusions": [{"left":"矩阵","right":"行列式","explain":"矩阵是数据或线性变换；行列式是描述变换体积缩放的数值。","example":"矩阵像变换，行列式像缩放因子"}]
    }
    examples.append((ex3_in, ex3_out))
    return examples

def fallback_summarize(text):
    # 极简回退：取前几句作为学习点；尝试基于常见关键词检测混淆
    lines = [l.strip() for l in text.replace('\r','\n').split('\n') if l.strip()]
    cand = []
    for l in lines:
        parts = [p.strip() for p in l.replace('，',' ').split(' ') if p.strip()]
        cand.extend(parts)
        if len(cand) >= 20:
            break
    learn_points = []
    # 选取前 4 条短句作为学习点
    for l in lines[:6]:
        s = l
        if len(s) > 40:
            s = s[:40] + '...'
        if s not in learn_points:
            learn_points.append(s)
    if not learn_points:
        learn_points = ['请明确题目或拍清晰一点的图片，以便提取学习点。']

    # 混淆点检测（增强版）：使用关键词到解释/例子的字典以生成更友好的输出
    common_map = {
        ('导数','微分'):("导数表示瞬时变化率；微分常用于表示小变化的近似。", "速度(导数) vs 小路程增量(微分)"),
        ('偏导数','全导数'):("偏导数针对单个变量的变化；全导数考虑多个变量的联合变化。", "例如：温度关于时间和位置的全导数 vs 仅对时间的偏导数"),
        ('行列式','矩阵'):("矩阵是数据结构，行列式是矩阵的一个数值特征。", "矩阵像变换，行列式像该变换放大缩小的程度"),
        ('概率','频率'):("概率是模型的主观/理论值；频率是实验观察到的比率。", "抛硬币理论概率 0.5 vs 实际抛 10 次出现 7 次的频率 0.7")
    }
    confusions = []
    for (a,b), (ex, examp) in common_map.items():
        if a in text or b in text:
            confusions.append({
                'left': a,
                'right': b,
                'explain': ex,
                'example': examp
            })
    if not confusions:
        confusions = [{
            'left':'导数','right':'微分','explain':'导数=瞬时变化率，微分=用于近似的增量。','example':'速度(导数) vs 小路程增量(微分)'
        }]

    return {'learn_points': learn_points[:6], 'confusions': confusions}


def generate_pdf(result, image_path, pdf_path):
    c = canvas.Canvas(pdf_path, pagesize=A4)
    width, height = A4
    margin = 40

    # 标题
    c.setFont('Helvetica-Bold', 18)
    c.drawString(margin, height - margin, '学习卡片')

    # 原图
    try:
        img = ImageReader(image_path)
        iw, ih = img.getSize()
        max_w = 200
        scale = min(max_w / iw, 120 / ih, 1)
        c.drawImage(img, width - margin - (iw*scale), height - margin - (ih*scale), width=iw*scale, height=ih*scale)
    except Exception as e:
        print('插入图片失败：', e)

    # 学习点
    c.setFont('Helvetica', 12)
    y = height - margin - 40
    c.drawString(margin, y, '精炼学习点：')
    y -= 20
    for i, p in enumerate(result.get('learn_points', []), 1):
        text = f"{i}. {p}"
        c.drawString(margin + 10, y, text)
        y -= 18
        if y < 120:
            c.showPage()
            y = height - margin

    # 混淆点
    c.setFont('Helvetica', 12)
    if y < 160:
        c.showPage()
        y = height - margin
    c.drawString(margin, y, '容易混淆的知识点：')
    y -= 20
    for cpair in result.get('confusions', []):
        left = cpair.get('left','')
        right = cpair.get('right','')
        explain = cpair.get('explain','')
        example = cpair.get('example','')
        c.drawString(margin + 10, y, f"{left} vs {right} - {explain}")
        y -= 18
        c.drawString(margin + 12, y, f"例子：{example}")
        y -= 24
        if y < 100:
            c.showPage()
            y = height - margin

    c.save()