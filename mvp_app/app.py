import os
import uuid
from flask import Flask, render_template, request, redirect, url_for
from PIL import Image
import pytesseract
from summarizer import summarize, generate_pdf
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_FOLDER = os.path.join(BASE_DIR, 'uploads')
OUTPUT_FOLDER = os.path.join(BASE_DIR, 'outputs')

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['OUTPUT_FOLDER'] = OUTPUT_FOLDER

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload():
    if 'image' not in request.files:
        return '没有上传文件', 400
    f = request.files['image']
    if f.filename == '':
        return '没有选中文件', 400

    file_id = str(uuid.uuid4())
    filename = f"{file_id}_{f.filename}"
    path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    f.save(path)

    # OCR：先预处理，再根据配置选择 OCR 引擎（本地 Tesseract 或 Google Vision）
    try:
        from ocr_utils import preprocess_image, tesseract_ocr, google_vision_ocr
        processed_img = preprocess_image(path)
        # 若环境变量指定使用 Google Vision 且可用，则优先使用
        use_google = os.getenv('USE_GOOGLE_VISION','0') == '1'
        ocr_text = ''
        if use_google:
            ocr_text = google_vision_ocr(path)
        if not ocr_text:
            ocr_text = tesseract_ocr(processed_img)
    except Exception as e:
        print('OCR 处理出错：', e)
        ocr_text = ''

    # Summarize (call LLM or fallback)
    result = summarize(ocr_text)

    # Generate PDF
    pdf_name = f"{file_id}.pdf"
    pdf_path = os.path.join(app.config['OUTPUT_FOLDER'], pdf_name)
    generate_pdf(result, path, pdf_path)

    image_url = f"/outputs/{filename}"
    pdf_url = f"/outputs/{pdf_name}"

    return render_template('result.html', image_url=image_url, ocr_text=ocr_text, result=result, pdf_url=pdf_url)

@app.route('/outputs/<path:filename>')
def outputs(filename):
    return app.send_static_file(os.path.join('..', 'outputs', filename))

if __name__ == '__main__':
    app.run(debug=True)