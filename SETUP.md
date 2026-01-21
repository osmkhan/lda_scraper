# LDA Transparency Database - Setup Guide

Complete step-by-step setup guide for the LDA Transparency Database.

## Prerequisites

- Python 3.8 or higher
- Git (for cloning)
- Ubuntu/Debian or macOS (Windows may work with WSL)

## Step 1: Install System Dependencies

### Ubuntu/Debian

```bash
# Update package list
sudo apt-get update

# Install required packages
sudo apt-get install -y \
    python3 \
    python3-pip \
    tesseract-ocr \
    tesseract-ocr-urd \
    poppler-utils \
    git
```

### macOS

```bash
# Install Homebrew if not already installed
# /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# Install required packages
brew install python tesseract tesseract-lang poppler git
```

## Step 2: Verify Tesseract Installation

```bash
# Check Tesseract version
tesseract --version

# Check available languages (should include eng and urd)
tesseract --list-langs
```

Expected output should show English (eng) and Urdu (urd) languages.

## Step 3: Clone or Setup Repository

If you haven't already:

```bash
# Clone the repository
git clone https://github.com/yourusername/lda_scraper.git
cd lda_scraper

# Or if starting from scratch, you already have the files
cd lda_scraper
```

## Step 4: Install Python Dependencies

```bash
# Upgrade pip
pip3 install --upgrade pip

# Install required Python packages
pip3 install -r requirements.txt
```

This will install:
- requests, beautifulsoup4 (web scraping)
- PyPDF2, pdfplumber, pdf2image (PDF processing)
- pytesseract, Pillow (OCR)
- datasette, sqlite-utils (database and web interface)
- pandas, PyYAML, tqdm (utilities)

## Step 5: Initialize Database

```bash
# Create the SQLite database with schema
python3 lda_cli.py init
```

This creates `lda_transparency.db` with all necessary tables.

## Step 6: Verify Setup

```bash
# Run system check
python3 lda_cli.py check
```

You should see:
- ✓ Database found
- ✓ Tesseract OCR is installed
- ✓ Configuration file found
- ✓ Directory exists: data/pdfs
- ✓ Directory exists: data/cache

If all checks pass, you're ready to start scraping!

## Step 7: Test with Sample Extraction

Before scraping, test the extraction utilities:

### Test PDF Extraction (Searchable PDF)

```bash
# Download a sample searchable PDF first
wget https://example.com/sample.pdf -O test_searchable.pdf

# Test extraction
python3 ocr/pdf_extractor.py test_searchable.pdf
```

### Test OCR (Scanned PDF)

```bash
# Test with a scanned PDF
python3 ocr/ocr_processor.py test_scanned.pdf
```

### Test Auto-Tagging

```bash
# Test the tagging system
python3 scrapers/tagger.py
```

## Step 8: Customize for LDA Website

Before scraping actual data, you need to do reconnaissance of lda.gop.pk:

### 8.1 Explore the LDA Website

1. Open https://lda.gop.pk in your browser
2. Find pages that list documents:
   - Regulations/bylaws
   - Meeting minutes
   - Housing schemes
   - Tenders
3. Note the URLs of these listing pages

### 8.2 Find CSS Selectors

For each document listing page:

1. Open browser Developer Tools (F12)
2. Inspect the PDF links
3. Find a CSS selector that matches all PDF links

Example:
- If links are: `<a class="doc-link" href="doc.pdf">Document</a>`
- Selector could be: `.doc-link` or `a[href$='.pdf']`

### 8.3 Update Scraper Scripts

Edit each scraper file in `scrapers/` directory:

**Example for `scrapers/scrape_regulations.py`:**

```python
# UPDATE THESE lines based on your reconnaissance
regulations_url = "https://lda.gop.pk/regulations"  # Actual URL
link_selector = "a[href$='.pdf']"  # Actual CSS selector
```

Do this for:
- `scrape_regulations.py`
- `scrape_meetings.py`
- `scrape_housing_schemes.py`
- `scrape_tenders.py`

## Step 9: Test Scraping (Small Sample)

Start with a small test to verify everything works:

```bash
# Test regulations scraper with limit
python3 scrapers/scrape_regulations.py
# (edit the script to add limit=5 for testing)

# Check database
python3 lda_cli.py stats
```

## Step 10: Launch Web Interface

```bash
# Start Datasette
./run_datasette.sh
```

Open http://localhost:8001 in your browser to explore the data.

## Step 11: Full Scraping

Once testing is successful, run full scrapers:

```bash
# Regulations (usually fast - searchable PDFs)
python3 scrapers/scrape_regulations.py

# Housing schemes
python3 scrapers/scrape_housing_schemes.py

# Tenders
python3 scrapers/scrape_tenders.py

# Meeting minutes (SLOW - uses OCR)
# Start with recent years first
python3 scrapers/scrape_meetings.py --by-year --start-year 2020
```

**Note**: Meeting minutes will be very slow (5-10 minutes per document) due to OCR processing.

## Troubleshooting

### Issue: "Tesseract not found"

**Solution:**
```bash
# Ubuntu/Debian
sudo apt-get install tesseract-ocr tesseract-ocr-urd

# macOS
brew install tesseract tesseract-lang

# Verify
tesseract --version
```

### Issue: "Database not found"

**Solution:**
```bash
python3 lda_cli.py init
```

### Issue: "Module not found" errors

**Solution:**
```bash
pip3 install -r requirements.txt
```

### Issue: OCR produces gibberish

**Possible causes:**
1. DPI too low - increase in `config/config.yaml`
2. Poor scan quality - not much can be done
3. Wrong language - verify Urdu language pack installed

**Try:**
```yaml
# In config/config.yaml
ocr:
  dpi: 400  # Increase from 300
  language: "eng+urd"
```

### Issue: Scraper not finding documents

**Possible causes:**
1. Incorrect URL
2. Wrong CSS selector
3. Website structure changed

**Debug:**
```bash
# Use browser dev tools to verify selector
# Try different selectors:
# - "a[href$='.pdf']"  # All links ending in .pdf
# - ".document-link"   # Links with specific class
# - "table a"          # Links within tables
```

### Issue: "Connection timeout" or network errors

**Solution:**
- Check internet connection
- Increase timeout in `config/config.yaml`:
```yaml
scraper:
  timeout: 60  # Increase from 30
```

## Performance Tips

### For OCR (Meeting Minutes)

1. **Start small**: Test with `--limit 5` first
2. **Use parallel processing**: OCR uses multi-threading by default
3. **Lower DPI for testing**: Set to 200 DPI for initial testing, increase to 300+ for production
4. **Process by year**: Use `--by-year` flag to scrape in chunks

### For Database

1. **Regular backups**: Copy `lda_transparency.db` regularly
2. **Vacuum database**: Run `sqlite3 lda_transparency.db "VACUUM;"` periodically
3. **Monitor size**: Check `du -h lda_transparency.db`

### For Datasette

1. **Limit results**: Use `--setting max_returned_rows 1000`
2. **Cache**: Datasette caches query results automatically
3. **Read-only**: Datasette operates in read-only mode by default

## Next Steps

After setup and initial scraping:

1. **Explore the data**: Use Datasette to browse and search
2. **Refine tagging**: Add more keywords to `config/config.yaml`
3. **Build queries**: Create custom SQL queries for your research
4. **Export data**: Download results as CSV for analysis
5. **Share findings**: Publish important discoveries

## Maintenance

### Regular Updates

```bash
# Update scrapers to get new documents
python3 scrapers/scrape_regulations.py
python3 scrapers/scrape_meetings.py --by-year --start-year 2026

# Check stats
python3 lda_cli.py stats
```

### Backup

```bash
# Backup database
cp lda_transparency.db lda_transparency.db.backup.$(date +%Y%m%d)

# Backup PDFs (if needed)
tar -czf lda_pdfs_backup.tar.gz data/pdfs/
```

### Cleanup

```bash
# Clear cache
rm -rf data/cache/*

# Remove old PDFs (if needed)
# Be careful - this deletes source files!
# rm -rf data/pdfs/*
```

## Getting Help

If you encounter issues:

1. Check this guide
2. Review error messages in console output
3. Run `python3 lda_cli.py check` to verify setup
4. Check logs for specific errors
5. Reduce scope (use `--limit` flags) to isolate issues

## Success Checklist

- [ ] System dependencies installed (Tesseract, poppler)
- [ ] Python packages installed
- [ ] Database initialized
- [ ] System check passes
- [ ] Test extraction works
- [ ] LDA website reconnaissance complete
- [ ] Scraper URLs and selectors updated
- [ ] Test scraping successful (small sample)
- [ ] Datasette launches successfully
- [ ] Full scraping running

Once all items are checked, you have a fully functional LDA Transparency Database!

---

**Ready to start? Run: `python3 lda_cli.py check`**
