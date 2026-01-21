"""
Scraper for LDA private housing schemes approvals.
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


def scrape_housing_schemes():
    """Scrape private housing schemes from LDA website."""

    scraper = LDAScraper()

    # UPDATE based on actual site structure
    housing_url = "https://lda.gop.pk/housing-schemes"
    link_selector = "a[href$='.pdf']"

    try:
        logger.info("Starting housing schemes scraper...")

        doc_ids = scraper.scrape_and_process(
            list_url=housing_url,
            link_selector=link_selector,
            document_type="housing_scheme",
            force_ocr=False,  # Auto-detect
            limit=None
        )

        logger.info(f"Successfully scraped {len(doc_ids)} housing schemes")
        return doc_ids

    except Exception as e:
        logger.error(f"Error scraping housing schemes: {e}", exc_info=True)
        return []

    finally:
        scraper.close()


if __name__ == "__main__":
    doc_ids = scrape_housing_schemes()

    if doc_ids:
        print(f"\nSuccessfully processed {len(doc_ids)} housing schemes")
    else:
        print("\nNo documents processed. Check logs for errors.")
