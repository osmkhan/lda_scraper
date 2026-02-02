"""
EasyOCR processor for scanned PDFs.
Converts PDF pages to images and extracts text using EasyOCR (no system dependencies!).
"""

import easyocr
from pdf2image import convert_from_path
from PIL import Image
import numpy as np
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from tqdm import tqdm

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class OCRProcessor:
    """Process scanned PDFs using EasyOCR (no Tesseract needed!)."""

    def __init__(
        self,
        pdf_path: str,
        languages: List[str] = None,
        dpi: int = 300,
        gpu: bool = False
    ):
        """
        Initialize OCR processor with EasyOCR.

        Args:
            pdf_path: Path to PDF file
            languages: List of language codes (default: ['en', 'ur'] for English + Urdu)
            dpi: DPI for PDF to image conversion (higher = better quality but slower)
            gpu: Use GPU acceleration if available (default: False for compatibility)
        """
        self.pdf_path = Path(pdf_path)
        if not self.pdf_path.exists():
            raise FileNotFoundError(f"PDF not found: {pdf_path}")

        # Default to English and Urdu
        if languages is None:
            languages = ['en', 'ur']

        self.languages = languages
        self.dpi = dpi
        self.gpu = gpu

        # Initialize EasyOCR reader (downloads models on first use)
        logger.info(f"Initializing EasyOCR reader with languages: {languages}")
        self.reader = easyocr.Reader(languages, gpu=gpu)

    def pdf_to_images(self, page_range: Optional[Tuple[int, int]] = None) -> List[Image.Image]:
        """
        Convert PDF pages to images.

        Args:
            page_range: Optional tuple of (first_page, last_page) (1-indexed)

        Returns:
            List of PIL Image objects
        """
        logger.info(f"Converting PDF to images at {self.dpi} DPI...")

        try:
            if page_range:
                first_page, last_page = page_range
                images = convert_from_path(
                    self.pdf_path,
                    dpi=self.dpi,
                    first_page=first_page,
                    last_page=last_page
                )
            else:
                images = convert_from_path(self.pdf_path, dpi=self.dpi)

            logger.info(f"Converted {len(images)} pages to images")
            return images

        except Exception as e:
            logger.error(f"Error converting PDF to images: {e}")
            raise

    def ocr_image(self, image: Image.Image, page_num: int) -> Tuple[int, str, Dict]:
        """
        Perform OCR on a single image using EasyOCR.

        Args:
            image: PIL Image object
            page_num: Page number (1-indexed)

        Returns:
            Tuple of (page_num, text, ocr_data)
        """
        try:
            # Convert PIL Image to numpy array
            image_array = np.array(image)

            # Perform OCR
            results = self.reader.readtext(image_array)

            # Extract text and confidence scores
            text_lines = []
            confidences = []

            for detection in results:
                # Each detection is: (bbox, text, confidence)
                _, text, confidence = detection
                text_lines.append(text)
                confidences.append(confidence * 100)  # Convert to percentage

            # Combine all text
            full_text = '\n'.join(text_lines)

            # Calculate average confidence
            avg_confidence = sum(confidences) / len(confidences) if confidences else 0

            return page_num, full_text.strip(), {
                'confidence': avg_confidence,
                'word_count': len(text_lines)
            }

        except Exception as e:
            logger.error(f"Error processing page {page_num}: {e}")
            return page_num, "", {'confidence': 0, 'word_count': 0}

    def process_pdf(
        self,
        max_workers: int = 2,
        page_range: Optional[Tuple[int, int]] = None
    ) -> Dict[int, Dict]:
        """
        Process entire PDF with OCR.

        Args:
            max_workers: Number of parallel workers (default: 2, EasyOCR is heavy)
            page_range: Optional tuple of (first_page, last_page) to process

        Returns:
            Dictionary mapping page numbers to extracted data
        """
        # Convert PDF to images
        images = self.pdf_to_images(page_range=page_range)

        if not images:
            logger.warning("No images extracted from PDF")
            return {}

        # Calculate starting page number
        start_page = page_range[0] if page_range else 1

        # Process pages in parallel (but fewer workers than Tesseract since EasyOCR is heavier)
        results = {}
        logger.info(f"Processing {len(images)} pages with EasyOCR...")

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Submit all tasks
            future_to_page = {
                executor.submit(self.ocr_image, img, start_page + i): start_page + i
                for i, img in enumerate(images)
            }

            # Process completed tasks with progress bar
            with tqdm(total=len(images), desc="OCR Progress") as pbar:
                for future in as_completed(future_to_page):
                    page_num, text, ocr_data = future.result()
                    results[page_num] = {
                        'text': text,
                        'confidence': ocr_data['confidence'],
                        'word_count': ocr_data['word_count']
                    }
                    pbar.update(1)

        logger.info(f"OCR completed for {len(results)} pages")
        return results

    def process_single_page(self, page_num: int) -> Dict:
        """
        Process a single page with OCR.

        Args:
            page_num: Page number (1-indexed)

        Returns:
            Dictionary with extracted text and metadata
        """
        images = self.pdf_to_images(page_range=(page_num, page_num))

        if not images:
            return {'text': '', 'confidence': 0, 'word_count': 0}

        _, text, ocr_data = self.ocr_image(images[0], page_num)

        return {
            'text': text,
            'confidence': ocr_data['confidence'],
            'word_count': ocr_data['word_count']
        }


def process_scanned_pdf(
    pdf_path: str,
    languages: List[str] = None,
    dpi: int = 300,
    max_workers: int = 2
) -> Dict[int, str]:
    """
    Convenience function to process a scanned PDF with OCR.

    Args:
        pdf_path: Path to PDF file
        languages: List of language codes (default: ['en', 'ur'])
        dpi: DPI for image conversion
        max_workers: Number of parallel workers

    Returns:
        Dictionary mapping page numbers to extracted text
    """
    processor = OCRProcessor(pdf_path, languages=languages, dpi=dpi)
    results = processor.process_pdf(max_workers=max_workers)

    # Return simplified dict with just text
    return {page_num: data['text'] for page_num, data in results.items()}


def check_easyocr_installation() -> bool:
    """Check if EasyOCR is properly installed."""
    try:
        # Try to import and create a simple reader
        import easyocr
        logger.info("EasyOCR is installed")
        logger.info("Note: Language models will be downloaded on first use")
        return True
    except Exception as e:
        logger.error(f"EasyOCR not found: {e}")
        logger.error("Please install EasyOCR:")
        logger.error("  pip install easyocr")
        return False


if __name__ == "__main__":
    import sys

    # Check EasyOCR installation
    if not check_easyocr_installation():
        sys.exit(1)

    if len(sys.argv) < 2:
        print("Usage: python ocr_processor.py <pdf_file> [page_num]")
        sys.exit(1)

    pdf_path = sys.argv[1]

    if len(sys.argv) > 2:
        # Process single page
        page_num = int(sys.argv[2])
        processor = OCRProcessor(pdf_path)
        result = processor.process_single_page(page_num)

        print(f"\nPage {page_num}:")
        print(f"Confidence: {result['confidence']:.2f}%")
        print(f"Word count: {result['word_count']}")
        print(f"\nText:\n{result['text']}")
    else:
        # Process entire PDF
        text_by_page = process_scanned_pdf(pdf_path)

        print(f"\nProcessed {len(text_by_page)} pages")
        print("\nFirst page preview:")
        if text_by_page:
            first_page = text_by_page.get(1, "")
            print(first_page[:500])
