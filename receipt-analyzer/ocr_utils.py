import pytesseract
from pdf2image import convert_from_bytes
import cv2
import numpy as np
from PIL import Image
import io

pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

def preprocess_image(image):
    """Enhanced preprocessing for better OCR accuracy"""
    # Convert PIL to OpenCV format
    img_array = np.array(image)
    
    # Convert to grayscale
    gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
    
    # Adjust brightness and contrast
    alpha = 1.5  # Contrast control
    beta = 10    # Brightness control
    adjusted = cv2.convertScaleAbs(gray, alpha=alpha, beta=beta)
    
    # Denoise
    denoised = cv2.fastNlMeansDenoising(adjusted, None, 10, 7, 21)
    
    # Deskew (straighten tilted receipts)
    coords = np.column_stack(np.where(denoised > 0))
    angle = cv2.minAreaRect(coords)[-1]
    if angle < -45:
        angle = 90 + angle
    (h, w) = denoised.shape
    center = (w // 2, h // 2)
    M = cv2.getRotationMatrix2D(center, angle, 1.0)
    rotated = cv2.warpAffine(denoised, M, (w, h), 
                             flags=cv2.INTER_CUBIC, 
                             borderMode=cv2.BORDER_REPLICATE)
    
    # Adaptive thresholding for better text clarity
    thresh = cv2.adaptiveThreshold(rotated, 255, 
                                   cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
                                   cv2.THRESH_BINARY, 11, 2)
    
    return Image.fromarray(thresh)

def extract_text_from_pdf_enhanced(pdf_bytes):
    """Enhanced OCR with preprocessing"""
    images = convert_from_bytes(pdf_bytes, dpi=300)  # Higher DPI
    full_text = ""
    
    for img in images:
        # Preprocess each page
        processed_img = preprocess_image(img)
        
        # Use Tesseract with custom config for receipts
        custom_config = r'--oem 3 --psm 6'  # PSM 6: Assume uniform block of text
        text = pytesseract.image_to_string(processed_img, config=custom_config)
        full_text += text + "\n"
    
    return full_text

def extract_text_from_image(image_bytes):
    """Extract text from image receipts (JPG, PNG)"""
    img = Image.open(io.BytesIO(image_bytes))
    processed_img = preprocess_image(img)
    
    custom_config = r'--oem 3 --psm 6'
    text = pytesseract.image_to_string(processed_img, config=custom_config)
    
    return text
