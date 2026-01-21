"""
PDF text extraction utilities for both searchable and scanned PDFs.
"""

import PyPDF2
import pdfplumber
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class PDFExtractor:
    """Extract text from PDF files, detecting if they're searchable or scanned."""

    def __init__(self, pdf_path: str):
        self.pdf_path = Path(pdf_path)
        if not self.pdf_path.exists():
            raise FileNotFoundError(f"PDF not found: {pdf_path}")

        self.page_count = self._get_page_count()
        self.is_scanned = None

    def _get_page_count(self) -> int:
        """Get the number of pages in the PDF."""
        with open(self.pdf_path, 'rb') as file:
            reader = PyPDF2.PdfReader(file)
            return len(reader.pages)

    def detect_scanned(self, sample_pages: int = 3) -> bool:
        """
        Detect if PDF is scanned by checking if it has extractable text.

        Args:
            sample_pages: Number of pages to sample for detection

        Returns:
            True if PDF appears to be scanned (no extractable text)
        """
        pages_to_check = min(sample_pages, self.page_count)

        with pdfplumber.open(self.pdf_path) as pdf:
            for i in range(pages_to_check):
                page = pdf.pages[i]
                text = page.extract_text() or ""

                # If we find more than 50 characters on any page, it's searchable
                if len(text.strip()) > 50:
                    self.is_scanned = False
                    return False

        # If no significant text found on sampled pages, likely scanned
        self.is_scanned = True
        return True

    def extract_text_searchable(self) -> Dict[int, str]:
        """
        Extract text from a searchable PDF.

        Returns:
            Dictionary mapping page numbers (1-indexed) to extracted text
        """
        text_by_page = {}

        try:
            with pdfplumber.open(self.pdf_path) as pdf:
                for i, page in enumerate(pdf.pages):
                    page_num = i + 1
                    text = page.extract_text() or ""
                    text_by_page[page_num] = text.strip()

                    logger.debug(f"Extracted {len(text)} chars from page {page_num}")

            logger.info(f"Extracted text from {len(text_by_page)} pages")
            return text_by_page

        except Exception as e:
            logger.error(f"Error extracting text from {self.pdf_path}: {e}")
            # Fallback to PyPDF2
            return self._extract_with_pypdf2()

    def _extract_with_pypdf2(self) -> Dict[int, str]:
        """Fallback extraction method using PyPDF2."""
        text_by_page = {}

        with open(self.pdf_path, 'rb') as file:
            reader = PyPDF2.PdfReader(file)

            for i in range(len(reader.pages)):
                page_num = i + 1
                page = reader.pages[i]
                text = page.extract_text() or ""
                text_by_page[page_num] = text.strip()

        logger.info(f"Extracted text using PyPDF2 from {len(text_by_page)} pages")
        return text_by_page

    def extract_metadata(self) -> Dict[str, any]:
        """Extract PDF metadata."""
        metadata = {
            'page_count': self.page_count,
            'file_size': self.pdf_path.stat().st_size,
            'is_scanned': self.is_scanned
        }

        try:
            with open(self.pdf_path, 'rb') as file:
                reader = PyPDF2.PdfReader(file)
                pdf_metadata = reader.metadata

                if pdf_metadata:
                    metadata.update({
                        'title': pdf_metadata.get('/Title'),
                        'author': pdf_metadata.get('/Author'),
                        'subject': pdf_metadata.get('/Subject'),
                        'creator': pdf_metadata.get('/Creator'),
                        'producer': pdf_metadata.get('/Producer'),
                        'creation_date': pdf_metadata.get('/CreationDate'),
                        'modification_date': pdf_metadata.get('/ModDate')
                    })
        except Exception as e:
            logger.warning(f"Could not extract metadata: {e}")

        return metadata

    def extract(self, force_ocr: bool = False) -> Tuple[Dict[int, str], str]:
        """
        Main extraction method that automatically detects PDF type.

        Args:
            force_ocr: Force OCR even if PDF appears searchable

        Returns:
            Tuple of (text_by_page dict, extraction_method string)
        """
        # Auto-detect if not already determined
        if self.is_scanned is None:
            self.detect_scanned()

        if force_ocr or self.is_scanned:
            return {}, "ocr_required"
        else:
            text_by_page = self.extract_text_searchable()
            return text_by_page, "direct_extraction"


def extract_text_from_pdf(
    pdf_path: str,
    force_ocr: bool = False
) -> Tuple[Dict[int, str], Dict[str, any]]:
    """
    Convenience function to extract text and metadata from a PDF.

    Args:
        pdf_path: Path to the PDF file
        force_ocr: Force OCR extraction even if PDF is searchable

    Returns:
        Tuple of (text_by_page dict, metadata dict)
    """
    extractor = PDFExtractor(pdf_path)
    text_by_page, extraction_method = extractor.extract(force_ocr=force_ocr)
    metadata = extractor.extract_metadata()
    metadata['extraction_method'] = extraction_method

    return text_by_page, metadata


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python pdf_extractor.py <pdf_file>")
        sys.exit(1)

    pdf_path = sys.argv[1]
    text_by_page, metadata = extract_text_from_pdf(pdf_path)

    print(f"\nMetadata: {metadata}")
    print(f"\nExtraction method: {metadata['extraction_method']}")
    print(f"\nTotal pages: {len(text_by_page)}")

    if text_by_page:
        print("\nFirst page preview:")
        first_page = text_by_page.get(1, "")
        print(first_page[:500])
    else:
        print("\nNo text extracted - OCR required for this PDF")
