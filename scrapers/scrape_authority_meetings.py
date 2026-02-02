"""
Scraper for LDA Authority Meeting Minutes (Dynamic Table with Pagination)
URL: https://lda.gop.pk/website/authority-meeting.php

This page has a searchable table with pagination that contains meeting minutes.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from scrapers.base_scraper import BaseScraper
from scrapers.lda_scraper import LDAScraper
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import logging
import time
from datetime import datetime

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class AuthorityMeetingScraper(LDAScraper):
    """Specialized scraper for authority meeting minutes with pagination."""

    def __init__(self, config_path: str = "config/config.yaml"):
        super().__init__(config_path)
        self.base_meeting_url = "https://lda.gop.pk/website/authority-meeting.php"

    def scrape_meeting_table(self, year: int = None, page: int = 1):
        """
        Scrape the meeting minutes table for a specific year and page.

        Args:
            year: Year to filter (e.g., 2023, 2024, 2025). None for all years.
            page: Page number (starts at 1)

        Returns:
            List of meeting metadata dictionaries
        """
        logger.info(f"Scraping meetings: Year={year or 'All'}, Page={page}")

        # Build URL with parameters
        params = {}
        if page > 1:
            params['page'] = page
        if year:
            params['year'] = year

        # Construct URL with query parameters
        if params:
            query_string = '&'.join([f"{k}={v}" for k, v in params.items()])
            url = f"{self.base_meeting_url}?{query_string}"
        else:
            url = self.base_meeting_url

        # Fetch page
        response = self.get_page(url)
        if not response:
            logger.error(f"Failed to fetch page: {url}")
            return []

        soup = self.parse_html(response.text)

        # Parse the table
        meetings = []

        # Find the table (look for table with Download column)
        table = soup.find('table')
        if not table:
            logger.warning("No table found on page")
            return []

        # Find all table rows (skip header)
        rows = table.find_all('tr')[1:]  # Skip header row

        for row in rows:
            cells = row.find_all('td')

            if len(cells) < 4:
                continue  # Skip malformed rows

            try:
                # Extract data from cells
                sr_no = cells[0].get_text(strip=True)
                meeting_date = cells[1].get_text(strip=True)
                year = cells[2].get_text(strip=True)

                # Extract PDF link from Download column
                download_cell = cells[3]
                pdf_link = download_cell.find('a')

                if not pdf_link:
                    logger.warning(f"No PDF link found for meeting: {meeting_date}")
                    continue

                # Get the PDF URL
                pdf_href = pdf_link.get('href')
                if not pdf_href:
                    logger.warning(f"PDF link has no href for meeting: {meeting_date}")
                    continue

                # Make URL absolute
                pdf_url = urljoin(self.base_meeting_url, pdf_href)

                # Create meeting metadata
                meeting = {
                    'sr_no': sr_no,
                    'meeting_date': meeting_date,
                    'year': year,
                    'pdf_url': pdf_url,
                    'source_page': url,
                    'title': f"Authority Meeting - {meeting_date}"
                }

                meetings.append(meeting)
                logger.debug(f"Found meeting: {meeting_date} - {pdf_url}")

            except Exception as e:
                logger.error(f"Error parsing row: {e}")
                continue

        logger.info(f"Found {len(meetings)} meetings on page {page}")
        return meetings

    def check_pagination(self, soup):
        """
        Check if there are more pages and return the next page number.

        Args:
            soup: BeautifulSoup object of current page

        Returns:
            Next page number or None if no more pages
        """
        # Look for pagination links
        pagination = soup.find_all('a', string=lambda s: s and 'Next' in s)

        if pagination:
            return True  # More pages exist

        # Also check for numbered page links
        page_links = soup.find_all('a', href=lambda h: h and 'page=' in h)

        return len(page_links) > 0

    def scrape_all_years(self, start_year: int = 2015, end_year: int = 2026, force_ocr: bool = True):
        """
        Scrape all meeting minutes across multiple years with pagination.

        Args:
            start_year: Starting year
            end_year: Ending year (inclusive)
            force_ocr: Force OCR (meeting minutes are typically scanned)

        Returns:
            List of successfully processed document IDs
        """
        all_doc_ids = []

        for year in range(start_year, end_year + 1):
            logger.info(f"\n{'='*70}")
            logger.info(f"Processing Year: {year}")
            logger.info('='*70)

            page = 1
            has_more_pages = True

            while has_more_pages:
                # Scrape current page
                meetings = self.scrape_meeting_table(year=year, page=page)

                if not meetings:
                    logger.info(f"No meetings found for year {year}, page {page}")
                    break

                # Process each meeting
                for meeting in meetings:
                    logger.info(f"\nProcessing: {meeting['title']}")

                    doc_id = self.process_and_store_document(
                        url=meeting['pdf_url'],
                        title=meeting['title'],
                        document_type='meeting_minutes',
                        metadata={
                            'meeting_date': meeting['meeting_date'],
                            'year': meeting['year'],
                            'sr_no': meeting['sr_no'],
                            'source_page': meeting['source_page']
                        },
                        force_ocr=force_ocr
                    )

                    if doc_id:
                        all_doc_ids.append(doc_id)
                        # Store meeting-specific data
                        self._store_meeting_details(doc_id, meeting)

                # Check for more pages
                page += 1

                # Simple check: if we got fewer than expected results, probably last page
                if len(meetings) < 10:  # Assuming ~10 results per page
                    has_more_pages = False
                    logger.info(f"Reached last page for year {year}")
                else:
                    logger.info(f"Moving to page {page} for year {year}")
                    time.sleep(self.delay)  # Rate limiting between pages

        logger.info(f"\n{'='*70}")
        logger.info(f"Total meetings processed: {len(all_doc_ids)}")
        logger.info('='*70)

        return all_doc_ids

    def _store_meeting_details(self, doc_id: int, meeting: dict):
        """Store meeting-specific details in meeting_minutes table."""
        cursor = self.db.conn.cursor()

        try:
            # Parse the meeting date
            meeting_date_str = meeting['meeting_date']
            try:
                # Try common date formats
                for fmt in ['%d %B, %Y', '%d %B %Y', '%B %d, %Y']:
                    try:
                        meeting_date = datetime.strptime(meeting_date_str, fmt).date()
                        break
                    except ValueError:
                        continue
                else:
                    meeting_date = None
            except:
                meeting_date = None

            cursor.execute("""
                INSERT OR IGNORE INTO meeting_minutes
                (document_id, meeting_date, meeting_type)
                VALUES (?, ?, ?)
            """, (doc_id, meeting_date, 'Authority Meeting'))

            self.db.conn.commit()

        except Exception as e:
            logger.error(f"Error storing meeting details: {e}")

    def scrape_recent_meetings(self, num_pages: int = 3, force_ocr: bool = True):
        """
        Scrape recent meetings (useful for regular updates).

        Args:
            num_pages: Number of pages to scrape (most recent first)
            force_ocr: Force OCR for scanned PDFs

        Returns:
            List of document IDs
        """
        logger.info("Scraping recent meetings...")

        all_doc_ids = []

        for page in range(1, num_pages + 1):
            meetings = self.scrape_meeting_table(page=page)

            if not meetings:
                logger.info(f"No meetings found on page {page}")
                break

            for meeting in meetings:
                logger.info(f"Processing: {meeting['title']}")

                doc_id = self.process_and_store_document(
                    url=meeting['pdf_url'],
                    title=meeting['title'],
                    document_type='meeting_minutes',
                    metadata={
                        'meeting_date': meeting['meeting_date'],
                        'year': meeting['year'],
                        'sr_no': meeting['sr_no'],
                        'source_page': meeting['source_page']
                    },
                    force_ocr=force_ocr
                )

                if doc_id:
                    all_doc_ids.append(doc_id)
                    self._store_meeting_details(doc_id, meeting)

        logger.info(f"Processed {len(all_doc_ids)} recent meetings")
        return all_doc_ids


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Scrape LDA Authority Meeting Minutes")
    parser.add_argument(
        '--mode',
        choices=['recent', 'all', 'year'],
        default='recent',
        help='Scraping mode: recent (default, 3 pages), all (all years), year (specific year)'
    )
    parser.add_argument(
        '--year',
        type=int,
        help='Specific year to scrape (use with --mode year)'
    )
    parser.add_argument(
        '--start-year',
        type=int,
        default=2015,
        help='Starting year for all mode (default: 2015)'
    )
    parser.add_argument(
        '--end-year',
        type=int,
        default=2026,
        help='Ending year for all mode (default: 2026)'
    )
    parser.add_argument(
        '--pages',
        type=int,
        default=3,
        help='Number of pages for recent mode (default: 3)'
    )
    parser.add_argument(
        '--no-ocr',
        action='store_true',
        help='Disable OCR (try direct extraction first)'
    )

    args = parser.parse_args()

    """
    Usage Examples:

    # Scrape 3 most recent pages (quick test)
    python scrapers/scrape_authority_meetings.py

    # Scrape 10 recent pages
    python scrapers/scrape_authority_meetings.py --mode recent --pages 10

    # Scrape specific year
    python scrapers/scrape_authority_meetings.py --mode year --year 2024

    # Scrape all years (2015-2026) - SLOW, will take hours!
    python scrapers/scrape_authority_meetings.py --mode all

    # Scrape year range
    python scrapers/scrape_authority_meetings.py --mode all --start-year 2020 --end-year 2025
    """

    scraper = AuthorityMeetingScraper()

    try:
        if args.mode == 'recent':
            logger.info(f"Scraping {args.pages} most recent pages...")
            doc_ids = scraper.scrape_recent_meetings(
                num_pages=args.pages,
                force_ocr=not args.no_ocr
            )

        elif args.mode == 'year' and args.year:
            logger.info(f"Scraping meetings for year {args.year}...")
            doc_ids = scraper.scrape_all_years(
                start_year=args.year,
                end_year=args.year,
                force_ocr=not args.no_ocr
            )

        elif args.mode == 'all':
            logger.info(f"Scraping all meetings from {args.start_year} to {args.end_year}...")
            logger.warning("This will take a LONG time (hours). Press Ctrl+C to cancel.")
            time.sleep(3)

            doc_ids = scraper.scrape_all_years(
                start_year=args.start_year,
                end_year=args.end_year,
                force_ocr=not args.no_ocr
            )

        else:
            parser.print_help()
            sys.exit(1)

        # Show statistics
        print("\n" + "="*70)
        print("RESULTS")
        print("="*70)
        print(f"\nSuccessfully processed: {len(doc_ids)} documents")

        stats = scraper.get_statistics()
        print(f"\nTotal documents in database: {stats['total_documents']}")

        if stats['top_tags']:
            print(f"\nTop advocacy topics found:")
            for tag_name, tag_category, count in stats['top_tags'][:5]:
                print(f"  - {tag_name}: {count} documents")

        print("\nTo view results:")
        print("  python3 lda_cli.py stats")
        print("  ./run_datasette.sh")

    except KeyboardInterrupt:
        print("\n\nScraping interrupted by user")
    finally:
        scraper.close()
