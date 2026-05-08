"""OCR text extraction from justification images.
Uses pytesseract if available, falls back to image metadata.
"""

import subprocess
import os

try:
    import pytesseract
    from PIL import Image
    HAS_TESSERACT = True
except ImportError:
    HAS_TESSERACT = False


def extract_text(image_path):
    """Extract text from an image using OCR. Returns empty string if OCR unavailable."""
    if not os.path.isfile(image_path):
        return ""

    if HAS_TESSERACT:
        try:
            img = Image.open(image_path)
            text = pytesseract.image_to_string(img, lang="por")
            return text.strip()
        except Exception:
            pass

    # Fallback: use tesseract CLI
    try:
        result = subprocess.run(
            ["tesseract", image_path, "stdout", "-l", "por"],
            capture_output=True, text=True, timeout=30
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except Exception:
        pass

    return ""


def extract_all_texts(image_paths):
    """Extract text from multiple images. Returns concatenated text."""
    texts = []
    for path in image_paths:
        text = extract_text(path)
        if text:
            texts.append(text)
    return "\n".join(texts)
