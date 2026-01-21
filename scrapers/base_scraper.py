"""
Base scraper class with common functionality for all LDA scrapers.
"""

import requests
from bs4 import BeautifulSoup
from pathlib import Path
from typing import Dict, List, Optional
import time
import logging
import hashlib
from urllib.parse import urljoin, urlparse
import yaml

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class BaseScraper:
    """Base class for all LDA website scrapers."""

    def __init__(self, config_path: str = "config/config.yaml"):
        """
        Initialize scraper with configuration.

        Args:
            config_path: Path to configuration file
        """
        self.config = self._load_config(config_path)
        self.base_url = self.config['base_url']
        self.data_dir = Path(self.config['data_dir'])
        self.cache_dir = Path(self.config['cache_dir'])

        # Create directories if they don't exist
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        # Set up session with retry logic
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': self.config['scraper']['user_agent']
        })

        self.timeout = self.config['scraper']['timeout']
        self.max_retries = self.config['scraper']['max_retries']
        self.delay = self.config['scraper']['delay_between_requests']

    def _load_config(self, config_path: str) -> Dict:
        """Load configuration from YAML file."""
        with open(config_path, 'r') as f:
            return yaml.safe_load(f)

    def get_page(self, url: str, retries: int = 0) -> Optional[requests.Response]:
        """
        Fetch a page with retry logic.

        Args:
            url: URL to fetch
            retries: Current retry count

        Returns:
            Response object or None if failed
        """
        try:
            time.sleep(self.delay)  # Rate limiting

            response = self.session.get(url, timeout=self.timeout)
            response.raise_for_status()

            logger.debug(f"Successfully fetched: {url}")
            return response

        except requests.RequestException as e:
            if retries < self.max_retries:
                logger.warning(f"Error fetching {url}, retry {retries + 1}/{self.max_retries}: {e}")
                time.sleep(2 ** retries)  # Exponential backoff
                return self.get_page(url, retries + 1)
            else:
                logger.error(f"Failed to fetch {url} after {self.max_retries} retries: {e}")
                return None

    def parse_html(self, html: str) -> BeautifulSoup:
        """Parse HTML content."""
        return BeautifulSoup(html, 'lxml')

    def download_file(self, url: str, filename: Optional[str] = None) -> Optional[Path]:
        """
        Download a file and save to data directory.

        Args:
            url: URL of file to download
            filename: Optional custom filename

        Returns:
            Path to downloaded file or None if failed
        """
        # Make URL absolute
        if not url.startswith('http'):
            url = urljoin(self.base_url, url)

        # Generate filename if not provided
        if not filename:
            filename = self._generate_filename(url)

        file_path = self.data_dir / filename

        # Check if already downloaded
        if file_path.exists():
            logger.info(f"File already exists: {filename}")
            return file_path

        logger.info(f"Downloading: {url}")

        try:
            time.sleep(self.delay)  # Rate limiting

            response = self.session.get(url, timeout=self.timeout, stream=True)
            response.raise_for_status()

            with open(file_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)

            logger.info(f"Saved to: {file_path}")
            return file_path

        except requests.RequestException as e:
            logger.error(f"Error downloading {url}: {e}")
            return None

    def _generate_filename(self, url: str) -> str:
        """
        Generate a unique filename from URL.

        Args:
            url: URL to generate filename from

        Returns:
            Generated filename
        """
        parsed = urlparse(url)
        path = parsed.path

        # Try to extract original filename
        if path.endswith('.pdf'):
            filename = Path(path).name
        else:
            # Generate hash-based filename
            url_hash = hashlib.md5(url.encode()).hexdigest()[:8]
            filename = f"{url_hash}.pdf"

        return filename

    def extract_links(self, soup: BeautifulSoup, selector: str) -> List[Dict]:
        """
        Extract links matching a CSS selector.

        Args:
            soup: BeautifulSoup object
            selector: CSS selector for links

        Returns:
            List of dicts with link text and URL
        """
        links = []

        for link in soup.select(selector):
            href = link.get('href')
            text = link.get_text(strip=True)

            if href:
                # Make URL absolute
                if not href.startswith('http'):
                    href = urljoin(self.base_url, href)

                links.append({
                    'text': text,
                    'url': href
                })

        return links

    def cache_exists(self, cache_key: str) -> bool:
        """Check if cached data exists."""
        cache_file = self.cache_dir / f"{cache_key}.cache"
        return cache_file.exists()

    def save_cache(self, cache_key: str, data: str):
        """Save data to cache."""
        cache_file = self.cache_dir / f"{cache_key}.cache"
        with open(cache_file, 'w', encoding='utf-8') as f:
            f.write(data)

    def load_cache(self, cache_key: str) -> Optional[str]:
        """Load data from cache."""
        cache_file = self.cache_dir / f"{cache_key}.cache"
        if cache_file.exists():
            with open(cache_file, 'r', encoding='utf-8') as f:
                return f.read()
        return None

    def scrape(self):
        """
        Main scraping method to be implemented by subclasses.

        Should return a list of scraped documents.
        """
        raise NotImplementedError("Subclasses must implement scrape() method")


if __name__ == "__main__":
    # Test the base scraper
    scraper = BaseScraper()
    print(f"Base URL: {scraper.base_url}")
    print(f"Data directory: {scraper.data_dir}")
    print(f"Cache directory: {scraper.cache_dir}")
