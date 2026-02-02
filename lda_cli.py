#!/usr/bin/env python3
"""
LDA Transparency Database CLI Tool

Main command-line interface for scraping, processing, and searching
LDA documents.
"""

import sys
import argparse
from pathlib import Path

from database.schema import LDADatabase, create_database
from scrapers.lda_scraper import LDAScraper
from ocr.ocr_processor import check_easyocr_installation
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def init_database(args):
    """Initialize the database schema."""
    logger.info("Initializing database...")

    db_path = args.db or "lda_transparency.db"
    create_database(db_path)

    logger.info(f"Database initialized at: {db_path}")
    logger.info("You can now start scraping documents.")


def check_setup(args):
    """Check if the system is properly set up."""
    logger.info("Checking system setup...")

    issues = []

    # Check database
    db_path = args.db or "lda_transparency.db"
    if not Path(db_path).exists():
        issues.append(f"Database not found at {db_path}")
        logger.warning(f"❌ Database not found. Run: lda_cli.py init")
    else:
        logger.info(f"✓ Database found at {db_path}")

    # Check EasyOCR
    if not check_easyocr_installation():
        issues.append("EasyOCR not installed")
        logger.warning("❌ EasyOCR not found. Install with:")
        logger.warning("   pip install easyocr")
        logger.warning("   (Language models will download automatically on first use)")
    else:
        logger.info("✓ EasyOCR is installed")

    # Check config
    if not Path("config/config.yaml").exists():
        issues.append("Configuration file not found")
        logger.warning("❌ Config file not found at config/config.yaml")
    else:
        logger.info("✓ Configuration file found")

    # Check data directories
    for directory in ["data/pdfs", "data/cache"]:
        if not Path(directory).exists():
            issues.append(f"Directory {directory} not found")
            logger.warning(f"❌ Directory not found: {directory}")
        else:
            logger.info(f"✓ Directory exists: {directory}")

    if issues:
        logger.error(f"\n{len(issues)} issues found. Please fix them before proceeding.")
        return False
    else:
        logger.info("\n✓ All checks passed! System is ready.")
        return True


def scrape_documents(args):
    """Scrape documents from LDA website."""
    logger.info(f"Scraping {args.type} documents...")

    scraper = LDAScraper()

    try:
        doc_ids = scraper.scrape_and_process(
            list_url=args.url,
            link_selector=args.selector,
            document_type=args.type,
            force_ocr=args.force_ocr,
            limit=args.limit
        )

        logger.info(f"Successfully processed {len(doc_ids)} documents")

        # Show statistics
        stats = scraper.get_statistics()
        print(f"\nDatabase Statistics:")
        print(f"  Total documents: {stats['total_documents']}")
        print(f"\n  By type:")
        for doc_type, count in stats['by_type'].items():
            print(f"    {doc_type}: {count}")

        if stats['top_tags']:
            print(f"\n  Top advocacy topics:")
            for tag_name, tag_category, count in stats['top_tags'][:5]:
                print(f"    {tag_name}: {count} documents")

    finally:
        scraper.close()


def search_documents(args):
    """Search documents in the database."""
    db = LDADatabase(args.db or "lda_transparency.db")
    db.connect()

    try:
        results = db.search_documents(args.query, limit=args.limit or 20)

        if not results:
            print(f"No results found for: {args.query}")
            return

        print(f"\nFound {len(results)} results for: {args.query}\n")

        for result in results:
            print(f"[{result['document_type']}] {result['title']}")
            print(f"  Date: {result['date_published'] or 'Unknown'}")
            print(f"  URL: {result['url']}")
            if result['snippet']:
                print(f"  Snippet: {result['snippet']}")
            print()

    finally:
        db.close()


def stats(args):
    """Show database statistics."""
    db = LDADatabase(args.db or "lda_transparency.db")
    db.connect()

    try:
        stats = db.get_document_stats()

        print("\n=== LDA Transparency Database Statistics ===\n")
        print(f"Total documents: {stats['total_documents']}")

        if stats['by_type']:
            print(f"\nDocuments by type:")
            for doc_type, count in stats['by_type'].items():
                print(f"  {doc_type}: {count}")

        print(f"\nTotal tags: {stats['total_tags']}")

        if stats['top_tags']:
            print(f"\nTop advocacy topics:")
            for tag_name, tag_category, count in stats['top_tags']:
                print(f"  {tag_name} ({tag_category}): {count} documents")

    finally:
        db.close()


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="LDA Transparency Database CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Initialize database
  python lda_cli.py init

  # Check system setup
  python lda_cli.py check

  # Scrape regulations
  python lda_cli.py scrape --url https://lda.gop.pk/regulations \\
                            --selector "a[href$='.pdf']" \\
                            --type regulation

  # Search documents
  python lda_cli.py search "pedestrian walkway"

  # View statistics
  python lda_cli.py stats

  # Launch web interface
  ./run_datasette.sh
        """
    )

    parser.add_argument(
        '--db',
        default='lda_transparency.db',
        help='Path to database file (default: lda_transparency.db)'
    )

    subparsers = parser.add_subparsers(dest='command', help='Command to run')

    # Init command
    init_parser = subparsers.add_parser('init', help='Initialize database')

    # Check command
    check_parser = subparsers.add_parser('check', help='Check system setup')

    # Scrape command
    scrape_parser = subparsers.add_parser('scrape', help='Scrape documents')
    scrape_parser.add_argument('--url', required=True, help='URL of document list page')
    scrape_parser.add_argument('--selector', required=True, help='CSS selector for document links')
    scrape_parser.add_argument('--type', required=True, help='Document type')
    scrape_parser.add_argument('--force-ocr', action='store_true', help='Force OCR for all documents')
    scrape_parser.add_argument('--limit', type=int, help='Maximum number of documents')

    # Search command
    search_parser = subparsers.add_parser('search', help='Search documents')
    search_parser.add_argument('query', help='Search query')
    search_parser.add_argument('--limit', type=int, default=20, help='Maximum results')

    # Stats command
    stats_parser = subparsers.add_parser('stats', help='Show database statistics')

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return

    # Dispatch to appropriate function
    commands = {
        'init': init_database,
        'check': check_setup,
        'scrape': scrape_documents,
        'search': search_documents,
        'stats': stats
    }

    command_func = commands.get(args.command)
    if command_func:
        command_func(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
