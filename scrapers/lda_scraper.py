"""
Main LDA scraper that coordinates document scraping, extraction, and database storage.
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from scrapers.base_scraper import BaseScraper
from scrapers.tagger import DocumentTagger
from database.schema import LDADatabase
from ocr.document_processor import process_document
import logging
from typing import Dict, List, Optional
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class LDAScraper(BaseScraper):
    """Main scraper for LDA website with integrated processing."""

    def __init__(self, config_path: str = "config/config.yaml"):
        super().__init__(config_path)
        self.db = LDADatabase(self.config['database_path'])
        self.db.connect()
        self.tagger = DocumentTagger(config_path)

    def scrape_document_list(self, url: str, link_selector: str) -> List[Dict]:
        """
        Scrape a list of document links from a page.

        Args:
            url: URL of the page with document links
            link_selector: CSS selector for document links

        Returns:
            List of document metadata dicts
        """
        logger.info(f"Scraping document list from: {url}")

        response = self.get_page(url)
        if not response:
            return []

        soup = self.parse_html(response.text)
        links = self.extract_links(soup, link_selector)

        logger.info(f"Found {len(links)} documents")
        return links

    def process_and_store_document(
        self,
        url: str,
        title: str,
        document_type: str,
        metadata: Optional[Dict] = None,
        force_ocr: bool = False
    ) -> Optional[int]:
        """
        Download, process, and store a document in the database.

        Args:
            url: URL of the PDF document
            title: Document title
            document_type: Type of document (meeting_minutes, regulation, etc.)
            metadata: Additional metadata
            force_ocr: Force OCR even if PDF is searchable

        Returns:
            Document ID if successful, None otherwise
        """
        logger.info(f"Processing: {title}")

        # Check if already processed
        cursor = self.db.conn.cursor()
        cursor.execute("SELECT id FROM documents WHERE url = ?", (url,))
        existing = cursor.fetchone()

        if existing:
            logger.info(f"Document already exists (ID: {existing[0]})")
            return existing[0]

        # Download PDF
        pdf_path = self.download_file(url)
        if not pdf_path:
            logger.error(f"Failed to download: {url}")
            return None

        try:
            # Extract text and metadata
            text_by_page, pdf_metadata = process_document(
                str(pdf_path),
                force_ocr=force_ocr
            )

            if not text_by_page:
                logger.warning(f"No text extracted from: {title}")
                return None

            # Insert document record
            doc_id = self.db.insert_document(
                document_type=document_type,
                title=title,
                url=url,
                file_path=str(pdf_path),
                page_count=pdf_metadata.get('page_count'),
                file_size=pdf_metadata.get('file_size'),
                is_scanned=pdf_metadata.get('is_scanned', False),
                extraction_method=pdf_metadata.get('extraction_method'),
                metadata=str(metadata) if metadata else None
            )

            if not doc_id:
                logger.error(f"Failed to insert document: {title}")
                return None

            # Insert page content
            for page_num, text in text_by_page.items():
                self.db.insert_content(
                    document_id=doc_id,
                    content=text,
                    page_number=page_num,
                    ocr_confidence=pdf_metadata.get('ocr_confidence')
                )

            # Auto-tag document
            tag_details = self.tagger.tag_document(text_by_page, min_mentions=2)

            for category, details in tag_details.items():
                # Get or create tag
                tag_id = self.db.insert_tag(
                    name=category,
                    category='advocacy',
                    description=f"Auto-tagged for {category}"
                )

                # Calculate confidence based on mention density
                total_text = ' '.join(text_by_page.values())
                confidence = min(1.0, details['total_mentions'] / (len(total_text) / 1000))

                # Associate tag with document
                self.db.tag_document(doc_id, tag_id, confidence)

            logger.info(f"Successfully processed document (ID: {doc_id})")
            logger.info(f"Tags: {', '.join(tag_details.keys())}")

            return doc_id

        except Exception as e:
            logger.error(f"Error processing {title}: {e}", exc_info=True)
            return None

    def scrape_and_process(
        self,
        list_url: str,
        link_selector: str,
        document_type: str,
        force_ocr: bool = False,
        limit: Optional[int] = None
    ) -> List[int]:
        """
        Scrape a list of documents and process them.

        Args:
            list_url: URL of page with document links
            link_selector: CSS selector for links
            document_type: Type of documents
            force_ocr: Force OCR for all documents
            limit: Maximum number of documents to process

        Returns:
            List of successfully processed document IDs
        """
        # Get document list
        documents = self.scrape_document_list(list_url, link_selector)

        if limit:
            documents = documents[:limit]

        # Process each document
        doc_ids = []

        for i, doc in enumerate(documents, 1):
            logger.info(f"Processing {i}/{len(documents)}: {doc['text']}")

            doc_id = self.process_and_store_document(
                url=doc['url'],
                title=doc['text'],
                document_type=document_type,
                force_ocr=force_ocr
            )

            if doc_id:
                doc_ids.append(doc_id)

        logger.info(f"Successfully processed {len(doc_ids)} documents")
        return doc_ids

    def get_statistics(self) -> Dict:
        """Get database statistics."""
        return self.db.get_document_stats()

    def close(self):
        """Close database connection."""
        self.db.close()


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="LDA Transparency Database Scraper")
    parser.add_argument('--url', required=True, help='URL of document list page')
    parser.add_argument('--selector', required=True, help='CSS selector for document links')
    parser.add_argument('--type', required=True, help='Document type')
    parser.add_argument('--force-ocr', action='store_true', help='Force OCR for all documents')
    parser.add_argument('--limit', type=int, help='Maximum number of documents to process')

    args = parser.parse_args()

    # Initialize scraper
    scraper = LDAScraper()

    try:
        # Scrape and process documents
        doc_ids = scraper.scrape_and_process(
            list_url=args.url,
            link_selector=args.selector,
            document_type=args.type,
            force_ocr=args.force_ocr,
            limit=args.limit
        )

        # Show statistics
        print("\nDatabase Statistics:")
        stats = scraper.get_statistics()
        print(f"Total documents: {stats['total_documents']}")
        print(f"\nBy type:")
        for doc_type, count in stats['by_type'].items():
            print(f"  {doc_type}: {count}")

        if stats['top_tags']:
            print(f"\nTop tags:")
            for tag_name, tag_category, count in stats['top_tags']:
                print(f"  {tag_name} ({tag_category}): {count} documents")

    finally:
        scraper.close()
