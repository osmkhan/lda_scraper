"""
Unified document processor that handles both searchable and scanned PDFs.
"""

from pathlib import Path
from typing import Dict, Tuple
import logging

from .pdf_extractor import PDFExtractor
from .ocr_processor import OCRProcessor

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class DocumentProcessor:
    """Unified processor for all PDF types."""

    def __init__(
        self,
        pdf_path: str,
        ocr_languages: list = None,
        ocr_dpi: int = 300,
        max_workers: int = 2
    ):
        self.pdf_path = Path(pdf_path)
        # Default to English and Urdu
        self.ocr_languages = ocr_languages if ocr_languages else ['en', 'ur']
        self.ocr_dpi = ocr_dpi
        self.max_workers = max_workers

    def process(self, force_ocr: bool = False) -> Tuple[Dict[int, str], Dict]:
        """
        Process a PDF document, automatically detecting if OCR is needed.

        Args:
            force_ocr: Force OCR even if PDF is searchable

        Returns:
            Tuple of (text_by_page dict, metadata dict)
        """
        logger.info(f"Processing: {self.pdf_path.name}")

        # First, try direct extraction
        extractor = PDFExtractor(str(self.pdf_path))
        metadata = extractor.extract_metadata()

        # Auto-detect if scanned
        if not force_ocr:
            is_scanned = extractor.detect_scanned()
        else:
            is_scanned = True

        if is_scanned or force_ocr:
            logger.info("PDF is scanned or OCR forced - using EasyOCR")
            metadata['extraction_method'] = 'ocr'
            metadata['is_scanned'] = True

            # Process with OCR
            ocr_processor = OCRProcessor(
                str(self.pdf_path),
                languages=self.ocr_languages,
                dpi=self.ocr_dpi
            )

            results = ocr_processor.process_pdf(max_workers=self.max_workers)

            # Extract text and calculate average confidence
            text_by_page = {}
            confidences = []

            for page_num, data in results.items():
                text_by_page[page_num] = data['text']
                if data['confidence'] > 0:
                    confidences.append(data['confidence'])

            avg_confidence = sum(confidences) / len(confidences) if confidences else 0
            metadata['ocr_confidence'] = avg_confidence

            logger.info(f"OCR completed with {avg_confidence:.2f}% average confidence")

        else:
            logger.info("PDF is searchable - extracting text directly")
            metadata['extraction_method'] = 'direct'
            metadata['is_scanned'] = False

            text_by_page = extractor.extract_text_searchable()

        total_chars = sum(len(text) for text in text_by_page.values())
        logger.info(f"Extracted {total_chars:,} characters from {len(text_by_page)} pages")

        return text_by_page, metadata


def process_document(
    pdf_path: str,
    force_ocr: bool = False,
    ocr_languages: list = None,
    ocr_dpi: int = 300,
    max_workers: int = 2
) -> Tuple[Dict[int, str], Dict]:
    """
    Convenience function to process any PDF document.

    Args:
        pdf_path: Path to PDF file
        force_ocr: Force OCR even if PDF is searchable
        ocr_languages: EasyOCR language codes (default: ['en', 'ur'])
        ocr_dpi: DPI for OCR image conversion
        max_workers: Number of parallel workers for OCR

    Returns:
        Tuple of (text_by_page dict, metadata dict)
    """
    processor = DocumentProcessor(
        pdf_path,
        ocr_languages=ocr_languages,
        ocr_dpi=ocr_dpi,
        max_workers=max_workers
    )

    return processor.process(force_ocr=force_ocr)


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python document_processor.py <pdf_file> [--force-ocr]")
        sys.exit(1)

    pdf_path = sys.argv[1]
    force_ocr = "--force-ocr" in sys.argv

    text_by_page, metadata = process_document(pdf_path, force_ocr=force_ocr)

    print(f"\nMetadata:")
    for key, value in metadata.items():
        print(f"  {key}: {value}")

    print(f"\nExtracted {len(text_by_page)} pages")

    if text_by_page:
        print("\nFirst page preview:")
        first_page = text_by_page.get(1, "")
        print(first_page[:500])
