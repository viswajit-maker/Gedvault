import pytesseract
import re
from pathlib import Path
from PIL import Image, ImageEnhance, ImageFilter
import pdf2image
import os

# Tell pytesseract where Tesseract is installed
pytesseract.pytesseract.tesseract_cmd = \
    r'C:\Program Files\Tesseract-OCR\tesseract.exe'

def preprocess_image(image_path):
    """
    Improve image quality before OCR.
    Better image = more accurate text reading.
    """
    img = Image.open(image_path)

    # Convert to grayscale (black & white reads better)
    img = img.convert('L')

    # Increase sharpness
    enhancer = ImageEnhance.Sharpness(img)
    img = enhancer.enhance(2.0)

    # Increase contrast
    enhancer = ImageEnhance.Contrast(img)
    img = enhancer.enhance(2.0)

    # Apply slight blur to reduce noise
    img = img.filter(ImageFilter.MedianFilter())

    return img

def extract_text_from_image(image_path):
    """Extract text from image using Tesseract."""
    img = preprocess_image(image_path)

    # PSM 6 = assume a uniform block of text
    # Good for prescription layouts
    text = pytesseract.image_to_string(
        img,
        config='--psm 6 --oem 3'
    )
    return text

def extract_text_from_pdf(pdf_path):
    """Convert PDF pages to images then extract text."""
    images = pdf2image.convert_from_path(pdf_path, dpi=300)
    all_text = []

    for i, img in enumerate(images):
        temp_path = f"uploads/temp_page_{i}.jpg"
        img.save(temp_path, 'JPEG')
        text = extract_text_from_image(temp_path)
        all_text.append(text)
        os.remove(temp_path)

    return '\n'.join(all_text)

def extract_medicines(text):
    """Find medicine names from raw OCR text."""
    medicines = []
    lines = text.split('\n')

    for line in lines:
        line = line.strip()
        if not line:
            continue

        # Look for dosage patterns — strong signal of medicine line
        if re.search(
            r'\d+\s*(mg|ML|mcg|IU|gm|g|tablet|tab|cap|syrup)',
            line, re.IGNORECASE
        ):
            # Take text before the first digit = medicine name
            medicine_name = re.split(r'\d', line)[0].strip()
            medicine_name = re.sub(r'[^a-zA-Z\s\-]', '', medicine_name).strip()

            if len(medicine_name) > 2:
                medicines.append(medicine_name.title())

    # Remove duplicates
    seen = set()
    unique = []
    for m in medicines:
        if m.lower() not in seen:
            seen.add(m.lower())
            unique.append(m)

    return unique

def process_prescription(file_path):
    """Main entry point — takes file path, returns result."""
    ext = Path(file_path).suffix.lower()

    if ext == '.pdf':
        raw_text = extract_text_from_pdf(file_path)
    elif ext in ['.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.webp']:
        raw_text = extract_text_from_image(file_path)
    else:
        raise ValueError(f"Unsupported file type: {ext}")

    medicines = extract_medicines(raw_text)

    return {
        "medicines": medicines,
        "raw_text": raw_text,
        "total_found": len(medicines)
    }