"""
Scraper for LDA building regulations and bylaws.
These are typically searchable PDFs with text.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from scrapers.lda_scraper import LDAScraper
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def scrape_regulations():
    """Scrape building regulations from LDA website."""

    # Initialize scraper
    scraper = LDAScraper()

    # Example URLs and selectors - UPDATE THESE based on actual site structure
    # After reconnaissance, update these values:

    # Option 1: If regulations are listed on a single page
    regulations_url = "https://lda.gop.pk/regulations"
    link_selector = "a[href$='.pdf']"  # Links ending with .pdf

    # Option 2: If there's a specific regulations page
    # regulations_url = "https://lda.gop.pk/building-regulations"
    # link_selector = ".regulation-list a"

    try:
        logger.info("Starting regulations scraper...")

        # Scrape and process (regulations are typically searchable PDFs)
        doc_ids = scraper.scrape_and_process(
            list_url=regulations_url,
            link_selector=link_selector,
            document_type="regulation",
            force_ocr=False,  # Try direct extraction first
            limit=None  # Process all
        )

        logger.info(f"Successfully scraped {len(doc_ids)} regulations")

        # Show statistics
        stats = scraper.get_statistics()
        logger.info(f"Total documents in database: {stats['total_documents']}")

        return doc_ids

    except Exception as e:
        logger.error(f"Error scraping regulations: {e}", exc_info=True)
        return []

    finally:
        scraper.close()


if __name__ == "__main__":
    """
    Usage:
        python scrapers/scrape_regulations.py

    Before running:
        1. Initialize database: python database/schema.py
        2. Update regulations_url and link_selector above
        3. Ensure Tesseract is installed for OCR fallback
    """

    doc_ids = scrape_regulations()

    if doc_ids:
        print(f"\nSuccessfully processed {len(doc_ids)} regulations")
        print("\nTo view in Datasette:")
        print("  datasette lda_transparency.db")
    else:
        print("\nNo documents processed. Check logs for errors.")
