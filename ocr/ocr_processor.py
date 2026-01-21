"""
Tesseract OCR processor for scanned PDFs.
Converts PDF pages to images and extracts text using Tesseract.
"""

import pytesseract
from pdf2image import convert_from_path
from PIL import Image
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from tqdm import tqdm

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class OCRProcessor:
    """Process scanned PDFs using Tesseract OCR."""

    def __init__(
        self,
        pdf_path: str,
        languages: str = "eng+urd",
        dpi: int = 300,
        tesseract_config: str = "--psm 6 --oem 3"
    ):
        """
        Initialize OCR processor.

        Args:
            pdf_path: Path to PDF file
            languages: Tesseract language codes (e.g., 'eng', 'eng+urd')
            dpi: DPI for PDF to image conversion (higher = better quality but slower)
            tesseract_config: Tesseract configuration string
                --psm 6: Assume a single uniform block of text
                --oem 3: Default OCR Engine Mode
        """
        self.pdf_path = Path(pdf_path)
        if not self.pdf_path.exists():
            raise FileNotFoundError(f"PDF not found: {pdf_path}")

        self.languages = languages
        self.dpi = dpi
        self.tesseract_config = tesseract_config

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
        Perform OCR on a single image.

        Args:
            image: PIL Image object
            page_num: Page number (1-indexed)

        Returns:
            Tuple of (page_num, text, ocr_data)
        """
        try:
            # Get OCR data with confidence scores
            ocr_data = pytesseract.image_to_data(
                image,
                lang=self.languages,
                config=self.tesseract_config,
                output_type=pytesseract.Output.DICT
            )

            # Extract text
            text = pytesseract.image_to_string(
                image,
                lang=self.languages,
                config=self.tesseract_config
            )

            # Calculate average confidence
            confidences = [
                int(conf) for conf in ocr_data['conf']
                if conf != '-1' and str(conf).isdigit()
            ]
            avg_confidence = sum(confidences) / len(confidences) if confidences else 0

            return page_num, text.strip(), {
                'confidence': avg_confidence,
                'word_count': len([w for w in ocr_data['text'] if w.strip()])
            }

        except Exception as e:
            logger.error(f"Error processing page {page_num}: {e}")
            return page_num, "", {'confidence': 0, 'word_count': 0}

    def process_pdf(
        self,
        max_workers: int = 4,
        page_range: Optional[Tuple[int, int]] = None
    ) -> Dict[int, Dict]:
        """
        Process entire PDF with OCR.

        Args:
            max_workers: Number of parallel workers for OCR processing
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

        # Process pages in parallel
        results = {}
        logger.info(f"Processing {len(images)} pages with OCR...")

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
    languages: str = "eng+urd",
    dpi: int = 300,
    max_workers: int = 4
) -> Dict[int, str]:
    """
    Convenience function to process a scanned PDF with OCR.

    Args:
        pdf_path: Path to PDF file
        languages: Tesseract language codes
        dpi: DPI for image conversion
        max_workers: Number of parallel workers

    Returns:
        Dictionary mapping page numbers to extracted text
    """
    processor = OCRProcessor(pdf_path, languages=languages, dpi=dpi)
    results = processor.process_pdf(max_workers=max_workers)

    # Return simplified dict with just text
    return {page_num: data['text'] for page_num, data in results.items()}


def check_tesseract_installation() -> bool:
    """Check if Tesseract is properly installed."""
    try:
        version = pytesseract.get_tesseract_version()
        logger.info(f"Tesseract version: {version}")
        return True
    except Exception as e:
        logger.error(f"Tesseract not found: {e}")
        logger.error("Please install Tesseract OCR:")
        logger.error("  Ubuntu/Debian: sudo apt-get install tesseract-ocr tesseract-ocr-urd")
        logger.error("  macOS: brew install tesseract tesseract-lang")
        return False


if __name__ == "__main__":
    import sys

    # Check Tesseract installation
    if not check_tesseract_installation():
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
