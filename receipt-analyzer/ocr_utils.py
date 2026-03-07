import pytesseract
from pdf2image import convert_from_bytes
import cv2
import numpy as np
from PIL import Image
import io

pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'


def preprocess_image(image):
    """Smart preprocessing - minimal for clean images, enhanced for poor ones"""
    img_array = np.array(image)

    # --- Handle different channel formats ---
    if len(img_array.shape) == 2:
        gray = img_array
    elif img_array.shape[2] == 4:
        rgb = cv2.cvtColor(img_array, cv2.COLOR_RGBA2RGB)
        gray = cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY)
    elif img_array.shape[2] == 3:
        gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
    else:
        gray = np.array(image.convert("L"))

    # --- Check image quality (variance = sharpness/contrast) ---
    variance = cv2.Laplacian(gray, cv2.CV_64F).var()

    if variance > 500:
        # HIGH QUALITY IMAGE - minimal processing, don't destroy it
        # Just upscale slightly if small
        h, w = gray.shape
        if w < 1000:
            scale = 1000 / w
            gray = cv2.resize(gray, None, fx=scale, fy=scale,
                              interpolation=cv2.INTER_CUBIC)
        return Image.fromarray(gray)

    # LOW QUALITY IMAGE - apply full enhancement pipeline
    # Upscale
    h, w = gray.shape
    if w < 1000:
        scale = 1000 / w
        gray = cv2.resize(gray, None, fx=scale, fy=scale,
                          interpolation=cv2.INTER_CUBIC)

    # Mild contrast boost
    adjusted = cv2.convertScaleAbs(gray, alpha=1.2, beta=5)

    # Denoise
    denoised = cv2.fastNlMeansDenoising(adjusted, None, 10, 7, 21)

    # Adaptive threshold
    thresh = cv2.adaptiveThreshold(denoised, 255,
                                   cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                                   cv2.THRESH_BINARY, 11, 2)
    return Image.fromarray(thresh)


def extract_text_from_pdf_enhanced(pdf_bytes):
    images = convert_from_bytes(pdf_bytes, dpi=300)
    full_text = ""
    for img in images:
        processed_img = preprocess_image(img)
        custom_config = r'--oem 3 --psm 6'
        text = pytesseract.image_to_string(processed_img, config=custom_config)
        full_text += text + "\n"
    return full_text


def extract_text_from_image(image_bytes):
    img = Image.open(io.BytesIO(image_bytes))
    processed_img = preprocess_image(img)
    custom_config = r'--oem 3 --psm 6'
    return pytesseract.image_to_string(processed_img, config=custom_config)
