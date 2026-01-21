"""OCR and PDF extraction module for LDA Transparency Database."""

from .pdf_extractor import PDFExtractor, extract_text_from_pdf
from .ocr_processor import OCRProcessor, process_scanned_pdf, check_tesseract_installation

__all__ = [
    'PDFExtractor',
    'extract_text_from_pdf',
    'OCRProcessor',
    'process_scanned_pdf',
    'check_tesseract_installation'
]
