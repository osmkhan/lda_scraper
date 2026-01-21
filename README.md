# LDA Transparency Database

A searchable database of Lahore Development Authority (LDA) planning meetings, decisions, regulations, and documents. Built to support advocacy for walkable Lahore and sustainable urban development.

## Overview

This project scrapes documents from the LDA website (lda.gop.pk), extracts text using OCR when needed, automatically tags documents with advocacy-relevant topics, and presents everything in a searchable web interface.

**Inspired by Matt Bruenig's NLRB Research model**: Python scrapers → SQLite database → Datasette web interface.

## Features

- **Automated Scraping**: Scrapes multiple document types from LDA website
- **OCR Support**: Handles scanned PDFs using Tesseract (English + Urdu)
- **Full-Text Search**: SQLite FTS5 search across all documents
- **Auto-Tagging**: Automatically identifies advocacy topics:
  - Walkability & pedestrian infrastructure
  - Traffic congestion
  - Public transport
  - Parking policies
  - Density & zoning
  - Sustainability & green spaces
  - Housing schemes
  - Urban planning
- **Web Interface**: Browse and search via Datasette
- **100% Free/Open Source**: No paid APIs or services

## Document Types

- **Meeting Minutes**: Authority meeting records (1970-2026) - scanned PDFs
- **Building Regulations**: Searchable regulation PDFs
- **Land Use Rules**: Planning and zoning documents
- **Housing Schemes**: Private development approvals
- **Tenders**: Procurement documents

## Installation

### 1. System Requirements

**Ubuntu/Debian:**
```bash
sudo apt-get update
sudo apt-get install -y python3 python3-pip tesseract-ocr tesseract-ocr-urd poppler-utils
```

**macOS:**
```bash
brew install python tesseract tesseract-lang poppler
```

### 2. Python Dependencies

```bash
# Clone or navigate to the repository
cd lda_scraper

# Install Python packages
pip install -r requirements.txt
```

### 3. Initialize Database

```bash
python lda_cli.py init
```

### 4. Verify Setup

```bash
python lda_cli.py check
```

This will verify:
- ✓ Database created
- ✓ Tesseract OCR installed
- ✓ Configuration files present
- ✓ Data directories created

## Quick Start

### Scrape Documents

The scrapers need to be customized based on the actual LDA website structure. Here's the general workflow:

**1. Scrape Building Regulations (searchable PDFs):**
```bash
python scrapers/scrape_regulations.py
```

**2. Scrape Meeting Minutes (scanned PDFs with OCR):**
```bash
python scrapers/scrape_meetings.py --limit 5  # Test with 5 first
```

**3. View in Web Interface:**
```bash
./run_datasette.sh
```

Then open http://localhost:8001 in your browser.

### Search Documents

**Command line search:**
```bash
python lda_cli.py search "pedestrian walkway"
python lda_cli.py search "parking density"
```

**View statistics:**
```bash
python lda_cli.py stats
```

## Usage

### CLI Tool

The main CLI tool provides easy access to all functionality:

```bash
# Initialize database
python lda_cli.py init

# Check system setup
python lda_cli.py check

# Scrape documents (requires URL and CSS selector)
python lda_cli.py scrape \
    --url https://lda.gop.pk/regulations \
    --selector "a[href$='.pdf']" \
    --type regulation

# Search documents
python lda_cli.py search "walkability"
python lda_cli.py search "bus rapid transit"

# View statistics
python lda_cli.py stats
```

### Individual Scrapers

Each document type has a dedicated scraper:

```bash
# Regulations (searchable PDFs)
python scrapers/scrape_regulations.py

# Meeting minutes (scanned PDFs - slow, uses OCR)
python scrapers/scrape_meetings.py

# Meeting minutes by year range
python scrapers/scrape_meetings.py --by-year --start-year 2020 --end-year 2023

# Housing schemes
python scrapers/scrape_housing_schemes.py

# Tenders
python scrapers/scrape_tenders.py
```

**Note**: Before running scrapers, update the URLs and CSS selectors in each script based on the actual LDA website structure.

### Web Interface (Datasette)

Launch the Datasette web interface:

```bash
./run_datasette.sh
```

Features:
- Browse all documents by type
- Full-text search across all content
- Filter by advocacy topics (walkability, transport, etc.)
- Export results as CSV/JSON
- Custom SQL queries
- Timeline views for meetings

Pre-configured queries:
- Documents by advocacy topic
- Recent documents
- Full-text search
- Walkability documents
- Public transport documents
- Meeting timeline

## Customization

### Update URLs and Selectors

Before scraping, update the URLs and CSS selectors in each scraper file:

1. **Reconnaissance**: Browse lda.gop.pk to find document listing pages
2. **Identify Selectors**: Use browser dev tools to find CSS selectors for PDF links
3. **Update Scrapers**: Edit the scraper files in `scrapers/` directory
4. **Test**: Run with `--limit 5` first to test

Example in `scrapers/scrape_regulations.py`:
```python
# UPDATE THESE based on actual site structure
regulations_url = "https://lda.gop.pk/regulations"  # Your URL
link_selector = "a[href$='.pdf']"  # Your CSS selector
```

### Add Custom Advocacy Topics

Edit `config/config.yaml` to add more keywords:

```yaml
advocacy_topics:
  your_topic:
    - "keyword1"
    - "keyword2"
    - "phrase to match"
```

### OCR Configuration

Adjust OCR settings in `config/config.yaml`:

```yaml
ocr:
  language: "eng+urd"  # Tesseract language codes
  dpi: 300             # Higher = better quality but slower
  tesseract_config: "--psm 6 --oem 3"  # Tesseract parameters
```

## Project Structure

```
lda_scraper/
├── config/
│   └── config.yaml           # Configuration settings
├── database/
│   ├── schema.py             # SQLite schema with FTS5 search
│   └── __init__.py
├── ocr/
│   ├── pdf_extractor.py      # Extract text from searchable PDFs
│   ├── ocr_processor.py      # Tesseract OCR for scanned PDFs
│   ├── document_processor.py # Unified document processor
│   └── __init__.py
├── scrapers/
│   ├── base_scraper.py       # Base scraper class
│   ├── lda_scraper.py        # Main coordinating scraper
│   ├── tagger.py             # Auto-tagging system
│   ├── scrape_regulations.py
│   ├── scrape_meetings.py
│   ├── scrape_housing_schemes.py
│   ├── scrape_tenders.py
│   └── __init__.py
├── data/
│   ├── pdfs/                 # Downloaded PDFs (not in git)
│   └── cache/                # Scraper cache (not in git)
├── lda_cli.py                # Main CLI tool
├── run_datasette.sh          # Launch web interface
├── datasette_metadata.yaml   # Datasette configuration
├── datasette_settings.json   # Datasette settings
├── requirements.txt          # Python dependencies
└── README.md                 # This file
```

## Technical Details

### Database Schema

The database uses SQLite with FTS5 for full-text search:

- **documents**: Main table for all documents
- **document_content**: Extracted text content (page by page)
- **tags**: Advocacy topic tags
- **document_tags**: Document-tag associations
- **meeting_minutes**: Meeting-specific data
- **regulations**: Regulation-specific data
- **housing_schemes**: Housing scheme data
- **tenders**: Tender data
- **documents_fts**: FTS5 virtual table for search

### Extraction Pipeline

1. **Download**: PDF downloaded from LDA website
2. **Detection**: Auto-detect if PDF is searchable or scanned
3. **Extraction**:
   - **Searchable**: Direct text extraction with pdfplumber/PyPDF2
   - **Scanned**: Convert to images → Tesseract OCR (eng+urd)
4. **Tagging**: Auto-tag with advocacy topics based on keywords
5. **Storage**: Store in SQLite with FTS5 indexing

### Auto-Tagging

Documents are automatically tagged based on keyword matching:

- **Walkability**: pedestrian, footpath, sidewalk, walking, etc.
- **Congestion**: traffic jam, congestion, traffic flow, etc.
- **Public Transport**: bus, metro, BRT, transit, etc.
- **Parking**: parking, car park, parking lot, etc.
- **Density**: density, FAR, zoning, mixed use, etc.
- **Sustainability**: green space, park, environment, etc.

See `config/config.yaml` for complete keyword lists.

## Development

### Testing OCR

Test OCR on a single PDF:

```bash
python ocr/ocr_processor.py path/to/scanned.pdf
```

Test extraction on a searchable PDF:

```bash
python ocr/pdf_extractor.py path/to/searchable.pdf
```

### Testing Tagging

Test the auto-tagging system:

```bash
python scrapers/tagger.py
```

### Database Queries

Access the database directly:

```bash
sqlite3 lda_transparency.db

-- Search documents
SELECT * FROM documents_fts WHERE documents_fts MATCH 'pedestrian';

-- Documents by topic
SELECT d.title, t.name
FROM documents d
JOIN document_tags dt ON d.id = dt.document_id
JOIN tags t ON dt.tag_id = t.id
WHERE t.name = 'walkability';
```

## Contributing

Before scraping:
1. Respect robots.txt
2. Use reasonable delays (configured in config.yaml)
3. Cache results to avoid re-downloading
4. Don't overload the LDA servers

Areas for improvement:
- Add more document types
- Improve OCR accuracy for Urdu text
- Add date extraction from meeting minutes
- Build custom Datasette plugins
- Add data visualization

## License

This project is released under the MIT License. The data scraped from LDA is public information from a government agency.

## Acknowledgments

- Inspired by Matt Bruenig's [NLRB Research](https://nlrbedge.org/) project
- Built with [Datasette](https://datasette.io/) by Simon Willison
- OCR powered by [Tesseract](https://github.com/tesseract-ocr/tesseract)

## Support

For issues or questions:
1. Check the logs in the console output
2. Verify setup with `python lda_cli.py check`
3. Test with small samples first (`--limit 5`)
4. Check that URLs and selectors match actual website

## Roadmap

- [ ] Complete reconnaissance of lda.gop.pk to map all document locations
- [ ] Fine-tune CSS selectors for each document type
- [ ] Optimize OCR settings for Urdu text
- [ ] Add date extraction and parsing
- [ ] Build custom Datasette homepage
- [ ] Add export to other formats (markdown, CSV summaries)
- [ ] Create data visualizations (meeting frequency, topic trends)
- [ ] Set up automated scraping schedule
- [ ] Deploy public instance

## Example Queries

Once you have data, try these searches in Datasette:

- Find walkability mentions: `walkability OR pedestrian OR footpath`
- Public transport planning: `bus OR metro OR "mass transit"`
- Parking requirements: `parking AND (requirement OR provision)`
- Density regulations: `density OR FAR OR "floor area ratio"`
- Recent meetings: Sort meeting_minutes by date
- Topic trends: Group by tags and count

---

**Built for a more walkable, sustainable Lahore 🚶🌳🚌**
