from PIL import Image, ImageDraw, ImageFont
import os

BASE = os.path.dirname(__file__)
IMG_DIR = os.path.join(BASE, 'demo_images')
OUT_DIR = os.path.join(BASE, 'outputs')
os.makedirs(OUT_DIR, exist_ok=True)

items = [
    ('printed_text.png', '导数的定义：函数在某点的瞬时变化率，表示曲线在该点的切线斜率。\n基本例子：设 s(t) 表示路程，速度 v(t)=s\'(t)。\n注意：导数与微分的区别。'),
    ('handwritten.png', '偏导数和全导数的区别：偏导数针对单个变量，全导数考虑多个变量的联合变化。\n例子：温度随时间和位置变化时，全导数包含时间和位置的贡献。')
]

for name, text in items:
    img_path = os.path.join(IMG_DIR, name)
    if not os.path.exists(img_path):
        continue
    img = Image.open(img_path).convert('RGB')
    w, h = img.size
    # create canvas wider to hold text
    new_w = max(800, w + 600)
    new_h = max(600, h)
    canvas = Image.new('RGB', (new_w, new_h), 'white')
    canvas.paste(img, (20, 20))

    draw = ImageDraw.Draw(canvas)
    try:
        font = ImageFont.truetype('arial.ttf', 16)
    except Exception:
        font = ImageFont.load_default()

    x = w + 40
    y = 40
    draw.text((x, y), 'OCR & 分析结果：', fill='black', font=font)
    y += 30
    for line in text.split('\n'):
        draw.text((x, y), line, fill='black', font=font)
        y += 24

    outname = os.path.join(OUT_DIR, name.replace('.png', '_preview.png'))
    canvas.save(outname)
    print('生成预览：', outname)

print('完成预览生成')