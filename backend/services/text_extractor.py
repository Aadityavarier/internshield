"""
InternShield — Text Extraction Service

Handles PDF, image, DOCX, TXT extraction with OCR fallback.
"""

import io
import re
import hashlib
from typing import Tuple

import pdfplumber
from PIL import Image, ImageEnhance, ImageFilter

try:
    import pytesseract
    TESSERACT_AVAILABLE = True
except Exception:
    TESSERACT_AVAILABLE = False

try:
    from docx import Document as DocxDocument
    DOCX_AVAILABLE = True
except Exception:
    DOCX_AVAILABLE = False


def extract_from_pdf(file_bytes: bytes) -> Tuple[str, str]:
    """
    Extract text from PDF. Uses pdfplumber first, falls back to OCR.
    Returns (extracted_text, method_used).
    """
    text = ""
    method = "pdfplumber"

    try:
        with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n"
    except Exception:
        pass

    # If direct extraction failed or returned too little, try OCR
    if len(text.strip()) < 50 and TESSERACT_AVAILABLE:
        try:
            from pdf2image import convert_from_bytes
            images = convert_from_bytes(file_bytes, dpi=300)
            ocr_text = ""
            for img in images:
                img = _preprocess_image(img)
                ocr_text += pytesseract.image_to_string(img, config="--psm 6") + "\n"
            if len(ocr_text.strip()) > len(text.strip()):
                text = ocr_text
                method = "ocr"
        except Exception:
            pass

    if not text.strip():
        method = "failed"

    return _sanitize_text(text), method


def extract_from_image(file_bytes: bytes) -> Tuple[str, str]:
    """
    Extract text from image using OCR with preprocessing.
    Returns (extracted_text, method_used).
    """
    if not TESSERACT_AVAILABLE:
        return "", "tesseract_unavailable"

    try:
        img = Image.open(io.BytesIO(file_bytes))
        img = _preprocess_image(img)
        text = pytesseract.image_to_string(img, config="--psm 6")
        return _sanitize_text(text), "ocr"
    except Exception as e:
        return "", f"ocr_error: {str(e)}"


def extract_from_docx(file_bytes: bytes) -> Tuple[str, str]:
    """
    Extract text from DOCX file using python-docx.
    Returns (extracted_text, method_used).
    """
    if not DOCX_AVAILABLE:
        return "", "docx_library_unavailable"

    try:
        doc = DocxDocument(io.BytesIO(file_bytes))
        paragraphs = [para.text for para in doc.paragraphs if para.text.strip()]
        text = "\n".join(paragraphs)
        return _sanitize_text(text), "docx"
    except Exception as e:
        return "", f"docx_error: {str(e)}"


def extract_from_txt(file_bytes: bytes) -> Tuple[str, str]:
    """
    Extract text from plain text / RTF file.
    Returns (extracted_text, method_used).
    """
    try:
        # Try UTF-8 first, then latin-1 as fallback
        try:
            text = file_bytes.decode("utf-8")
        except UnicodeDecodeError:
            text = file_bytes.decode("latin-1", errors="ignore")

        # Strip RTF formatting if present
        if text.strip().startswith("{\\rtf"):
            text = _strip_rtf(text)

        return _sanitize_text(text), "txt"
    except Exception as e:
        return "", f"txt_error: {str(e)}"


def extract_from_text(raw_text: str) -> Tuple[str, str]:
    """
    Sanitize plain text input.
    Returns (sanitized_text, method_used).
    """
    return _sanitize_text(raw_text), "direct"


def compute_file_hash(content: bytes) -> str:
    """Compute SHA-256 hash of file content for dedup."""
    return hashlib.sha256(content).hexdigest()


def _preprocess_image(img: Image.Image) -> Image.Image:
    """
    Preprocess image for better OCR accuracy:
    - Convert to grayscale
    - Boost contrast
    - Apply slight sharpening
    - Denoise
    """
    # Convert to grayscale
    img = img.convert("L")

    # Boost contrast
    enhancer = ImageEnhance.Contrast(img)
    img = enhancer.enhance(2.0)

    # Sharpen
    img = img.filter(ImageFilter.SHARPEN)

    # Denoise with median filter
    img = img.filter(ImageFilter.MedianFilter(size=3))

    return img


def _strip_rtf(text: str) -> str:
    """Basic RTF stripping — removes RTF control words and groups."""
    # Remove RTF header
    text = re.sub(r"\{\\rtf[^}]*\}", "", text)
    # Remove control words
    text = re.sub(r"\\[a-z]+\d*\s?", " ", text)
    # Remove braces
    text = re.sub(r"[{}]", "", text)
    # Clean up
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def _sanitize_text(text: str) -> str:
    """Clean up extracted text."""
    # Normalize unicode
    text = text.encode("utf-8", errors="ignore").decode("utf-8")

    # Remove excessive whitespace but preserve paragraph breaks
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)

    # Strip leading/trailing whitespace per line
    lines = [line.strip() for line in text.split("\n")]
    text = "\n".join(lines)

    return text.strip()
