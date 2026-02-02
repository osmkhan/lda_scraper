#!/usr/bin/env python3
"""
LDA Website Reconnaissance Tool

Run this script to explore lda.gop.pk and find document URLs and selectors.
"""

import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import sys


def explore_page(url, find_pdfs=True):
    """Explore a page and find links (especially PDFs)."""

    headers = {
        'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36'
    }

    print(f"\n{'='*70}")
    print(f"Exploring: {url}")
    print('='*70)

    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, 'lxml')

        # Find all links
        all_links = soup.find_all('a', href=True)

        print(f"\nTotal links found: {len(all_links)}")

        # Find PDF links
        pdf_links = [link for link in all_links if link['href'].lower().endswith('.pdf')]

        if pdf_links:
            print(f"\n🎯 Found {len(pdf_links)} PDF links:")
            for i, link in enumerate(pdf_links[:10], 1):  # Show first 10
                href = link['href']
                text = link.get_text(strip=True)
                full_url = urljoin(url, href)
                print(f"\n  {i}. {text[:60]}...")
                print(f"     URL: {full_url}")

                # Suggest CSS selectors
                classes = link.get('class', [])
                if classes:
                    print(f"     Class selector: .{'.'.join(classes)}")

                parent = link.parent
                if parent and parent.name:
                    print(f"     Parent: <{parent.name}>")

            if len(pdf_links) > 10:
                print(f"\n  ... and {len(pdf_links) - 10} more PDF links")

            # Suggest generic selectors
            print(f"\n📝 Suggested CSS selectors:")
            print(f"   a[href$='.pdf']           # All links ending with .pdf")
            print(f"   a[href*='.pdf']           # All links containing .pdf")

            # Check for common patterns
            if pdf_links:
                first_link = pdf_links[0]
                classes = first_link.get('class', [])
                if classes:
                    print(f"   .{classes[0]}               # First PDF's class")
        else:
            print("\n⚠️  No PDF links found on this page")
            print("\n🔍 Exploring other link types:")

            # Show navigation links that might lead to documents
            nav_keywords = ['document', 'regulation', 'meeting', 'tender', 'scheme',
                           'download', 'file', 'record', 'minute', 'notice']

            interesting_links = []
            for link in all_links[:50]:  # Check first 50 links
                text = link.get_text(strip=True).lower()
                href = link['href'].lower()
                if any(keyword in text or keyword in href for keyword in nav_keywords):
                    interesting_links.append(link)

            if interesting_links:
                print(f"\n📁 Found {len(interesting_links)} potentially interesting links:")
                for i, link in enumerate(interesting_links[:15], 1):
                    text = link.get_text(strip=True)
                    href = link['href']
                    full_url = urljoin(url, href)
                    print(f"  {i}. {text[:50]}")
                    print(f"     {full_url}")
            else:
                print("\n⚠️  No obvious document-related links found")

        # Look for document sections
        print("\n🏗️  Page structure:")

        # Find sections/divs that might contain documents
        for tag in ['section', 'div', 'article', 'main']:
            elements = soup.find_all(tag, class_=True)
            if elements:
                print(f"\n  <{tag}> elements with classes:")
                for el in elements[:5]:
                    classes = ' '.join(el.get('class', []))
                    print(f"    .{classes}")

        return soup, pdf_links

    except requests.RequestException as e:
        print(f"\n❌ Error accessing {url}")
        print(f"   {e}")
        return None, []
    except Exception as e:
        print(f"\n❌ Error parsing page: {e}")
        return None, []


def main():
    """Main reconnaissance function."""

    if len(sys.argv) > 1:
        # User provided specific URL
        urls = sys.argv[1:]
    else:
        # Default URLs to try
        print("No URLs provided. Trying common LDA document pages...")
        print("\nTip: You can provide URLs as arguments:")
        print("  python reconnaissance.py https://lda.gop.pk/regulations\n")

        urls = [
            "https://lda.gop.pk",
            "https://lda.gop.pk/regulations",
            "https://lda.gop.pk/documents",
            "https://lda.gop.pk/downloads",
            "https://lda.gop.pk/meetings",
            "https://lda.gop.pk/tenders",
            "https://lda.gop.pk/housing-schemes",
            "https://lda.gop.pk/land-use",
            "https://lda.gop.pk/bylaws",
        ]

    print("🔍 LDA Website Reconnaissance Tool")
    print("="*70)

    all_pdf_links = []

    for url in urls:
        soup, pdf_links = explore_page(url, find_pdfs=True)
        all_pdf_links.extend(pdf_links)

        if soup:
            print("\n✓ Page successfully explored")
        else:
            print("\n✗ Failed to explore page")

    # Summary
    print("\n" + "="*70)
    print("SUMMARY")
    print("="*70)
    print(f"\nTotal PDF links found: {len(all_pdf_links)}")

    if all_pdf_links:
        print("\n🎉 Success! Found PDF documents.")
        print("\nNext steps:")
        print("1. Note the URLs that have PDFs")
        print("2. Copy the suggested CSS selectors")
        print("3. Update your scraper scripts with these URLs and selectors")
        print("\nExample:")
        print("  # In scrapers/scrape_regulations.py")
        print("  regulations_url = 'https://lda.gop.pk/YOUR-URL-HERE'")
        print("  link_selector = 'a[href$=\".pdf\"]'")
    else:
        print("\n⚠️  No PDFs found. Try:")
        print("1. Browse lda.gop.pk manually in your browser")
        print("2. Find pages with PDF documents")
        print("3. Run this script with those URLs:")
        print("   python reconnaissance.py https://lda.gop.pk/actual-page")


if __name__ == "__main__":
    main()
