from PIL import Image, ImageFilter, ImageOps
import os
import pytesseract

try:
    from google.cloud import vision
    GOOGLE_VISION_AVAILABLE = True
except Exception:
    GOOGLE_VISION_AVAILABLE = False


def preprocess_image(path):
    """简单预处理：灰度 + 二值化 + 去噪滤波，返回 PIL.Image 对象"""
    img = Image.open(path)
    # 转 RGB/灰度
    img = img.convert('L')
    # 自适应阈值的替代（Pillow 没有自适应直方图阈值）
    img = ImageOps.autocontrast(img)
    img = img.filter(ImageFilter.MedianFilter(size=3))
    return img


def tesseract_ocr(img):
    """对 PIL.Image 调用 pytesseract，返回识别文本"""
    try:
        # 指定简体中文和英文
        text = pytesseract.image_to_string(img, lang='chi_sim+eng')
        return text
    except Exception as e:
        print('Tesseract 识别失败：', e)
        return ''


def google_vision_ocr(path):
    """可选：调用 Google Vision OCR（需要安装 google-cloud-vision 并设置 GOOGLE_APPLICATION_CREDENTIALS）"""
    if not GOOGLE_VISION_AVAILABLE:
        print('Google Vision 客户端不可用（未安装 google-cloud-vision）')
        return ''
    try:
        client = vision.ImageAnnotatorClient()
        with open(path, 'rb') as f:
            content = f.read()
        image = vision.Image(content=content)
        response = client.document_text_detection(image=image)
        if response.error.message:
            print('Google Vision 返回错误：', response.error.message)
            return ''
        return response.full_text_annotation.text
    except Exception as e:
        print('调用 Google Vision OCR 失败：', e)
        return ''