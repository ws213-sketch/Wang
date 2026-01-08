import os
from PIL import Image, ImageDraw, ImageFont
from ocr_utils import preprocess_image, tesseract_ocr
from summarizer import summarize, generate_pdf

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
IMG_DIR = os.path.join(BASE_DIR, 'demo_images')
OUT_DIR = os.path.join(BASE_DIR, 'outputs')
os.makedirs(IMG_DIR, exist_ok=True)
os.makedirs(OUT_DIR, exist_ok=True)

printed_text = (
    "导数的定义：函数在某点的瞬时变化率，表示曲线在该点的切线斜率。\n"
    "基本例子：设 s(t) 表示路程，速度 v(t)=s'(t)。\n"
    "注意：导数与微分的区别，导数是瞬时变化率，微分用于近似小增量。"
)

handwritten_text = (
    "偏导数和全导数的区别：偏导数针对单个变量，全导数考虑多个变量的联合变化。\n"
    "例子：温度随时间和位置变化时，全导数包含时间和位置的贡献。"
)

# Helper to draw multiline text
def create_image_with_text(text, path, font=None, size=(800,400), handwritten=False):
    img = Image.new('RGB', size, color='white')
    draw = ImageDraw.Draw(img)
    # Attempt to load a truetype font; fallback to default
    try:
        if font and os.path.exists(font):
            fnt = ImageFont.truetype(font, 20)
        else:
            # Common Windows font path
            fnt = ImageFont.truetype('arial.ttf', 20)
    except Exception:
        fnt = ImageFont.load_default()

    x, y = 20, 20
    for line in text.split('\n'):
        if handwritten:
            # introduce slight jitter for handwritten feel
            for i, ch in enumerate(line):
                draw.text((x + i*12 + (i%3-1), y + (i%2)), ch, font=fnt, fill=(0,0,0))
            y += 28
        else:
            draw.text((x, y), line, font=fnt, fill=(0,0,0))
            y += 28
    img.save(path)
    return path

# Create images
printed_path = os.path.join(IMG_DIR, 'printed_text.png')
handwritten_path = os.path.join(IMG_DIR, 'handwritten.png')
create_image_with_text(printed_text, printed_path, handwritten=False)
create_image_with_text(handwritten_text, handwritten_path, handwritten=True)

examples = [
    ('打印文本样张', printed_path, printed_text),
    ('手写样张(模拟)', handwritten_path, handwritten_text)
]

results = []
for name, path, ground_truth in examples:
    print('---')
    print('样张：', name, path)
    img = preprocess_image(path)
    ocr_res = tesseract_ocr(img)
    if not ocr_res or ocr_res.strip()=='' :
        print('OCR 结果为空，使用 Ground Truth 作为输入（可能是因为未安装 tesseract）。')
        ocr_res = ground_truth
    print('OCR 文本：\n', ocr_res)

    res = summarize(ocr_res)
    print('模型输出：', res)

    pdf_name = os.path.basename(path).replace('.png', '.pdf')
    pdf_path = os.path.join(OUT_DIR, 'demo_' + pdf_name)
    generate_pdf(res, path, pdf_path)
    print('生成 PDF：', pdf_path)
    results.append((name, path, ocr_res, res, pdf_path))

# 写入一个小报告文件
report = os.path.join(OUT_DIR, 'demo_report.txt')
with open(report, 'w', encoding='utf-8') as f:
    for (name, path, ocr_res, res, pdf_path) in results:
        f.write('样张: ' + name + '\n')
        f.write('图片: ' + path + '\n')
        f.write('OCR:\n' + ocr_res + '\n')
        f.write('结果:\n' + str(res) + '\n')
        f.write('PDF: ' + pdf_path + '\n')
        f.write('\n---\n\n')

print('\nDone. 报告写入：', report)
