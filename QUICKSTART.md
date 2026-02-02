# Quick Start Guide - Start Scraping Now!

Your LDA Transparency Database is set up and ready. Here's how to start scraping:

## Step 1: Find Document URLs (5 minutes)

### Option A: Use the Reconnaissance Tool

```bash
# Run the automated reconnaissance tool
python3 reconnaissance.py

# Or provide specific URLs you find
python3 reconnaissance.py https://lda.gop.pk/some-page
```

This will:
- Explore lda.gop.pk for PDF documents
- Show you which pages have PDFs
- Suggest CSS selectors for the links

### Option B: Manual Reconnaissance

1. Open https://lda.gop.pk in your browser
2. Look for pages with document links:
   - Regulations / Bylaws
   - Meeting Minutes
   - Housing Schemes
   - Tenders
   - Downloads / Documents section
3. Right-click on a PDF link → Inspect Element
4. Note the HTML structure and CSS classes

**Example of what you're looking for:**
```html
<a href="/uploads/regulation.pdf" class="doc-link">Regulation Document</a>
```

From this you get:
- **Page URL**: https://lda.gop.pk/regulations (or wherever you found it)
- **CSS Selector**: `.doc-link` or `a[href$='.pdf']`

## Step 2: Update Scraper Scripts (2 minutes)

Edit the scraper files with the URLs you found:

### For Regulations:
Edit `scrapers/scrape_regulations.py` around line 25:

```python
# UPDATE THESE lines
regulations_url = "https://lda.gop.pk/ACTUAL-URL-HERE"
link_selector = "a[href$='.pdf']"  # Or your actual selector
```

### For Housing Schemes:
Edit `scrapers/scrape_housing_schemes.py` similarly:

```python
housing_url = "https://lda.gop.pk/ACTUAL-URL-HERE"
link_selector = "a[href$='.pdf']"
```

### For Tenders:
Edit `scrapers/scrape_tenders.py`:

```python
tenders_url = "https://lda.gop.pk/ACTUAL-URL-HERE"
link_selector = "a[href$='.pdf']"
```

## Step 3: Test Scraping (1 minute)

Start with regulations (usually searchable PDFs - fast):

```bash
# Test with the regulations scraper
python3 scrapers/scrape_regulations.py
```

Watch the output:
- ✓ URLs being fetched
- ✓ PDFs being downloaded
- ✓ Text being extracted
- ✓ Documents being tagged
- ✓ Saved to database

## Step 4: View Results

```bash
# Check what was scraped
python3 lda_cli.py stats

# Search for something
python3 lda_cli.py search "parking"

# Launch web interface
./run_datasette.sh
# Then open http://localhost:8001
```

## Common CSS Selectors

If you're not sure what selector to use, try these common ones:

```css
a[href$='.pdf']           # Any link ending with .pdf
a[href*='.pdf']           # Any link containing .pdf
.document-link            # Links with class "document-link"
.pdf-download             # Links with class "pdf-download"
table a[href$='.pdf']     # PDF links inside tables
ul.documents a            # Links in a <ul> with class "documents"
```

## Example Workflow

Here's a complete example once you have the URLs:

```bash
# 1. Find URLs with reconnaissance
python3 reconnaissance.py

# 2. Update scrapers/scrape_regulations.py with actual URLs
# (Edit the file with your text editor)

# 3. Test with a small sample
# Edit the scraper to add limit=5 for testing
python3 scrapers/scrape_regulations.py

# 4. Check results
python3 lda_cli.py stats

# 5. If successful, remove the limit and run full scrape
python3 scrapers/scrape_regulations.py

# 6. Repeat for other document types
python3 scrapers/scrape_housing_schemes.py
python3 scrapers/scrape_tenders.py

# 7. Launch web interface to explore
./run_datasette.sh
```

## Troubleshooting

### "No documents found"
- Check that the URL is correct (visit it in your browser)
- Try a different CSS selector
- Run reconnaissance.py on that specific URL

### "Failed to download PDF"
- Check your internet connection
- The PDF link might be broken on the LDA site
- Try accessing the PDF URL directly in your browser

### "No text extracted"
- The PDF might be scanned (needs OCR)
- For scanned PDFs, install EasyOCR: `pip3 install easyocr`
- Then use the meeting minutes scraper (it has OCR enabled)

## What About Meeting Minutes?

Meeting minutes are typically **scanned PDFs** that need OCR. To scrape them:

1. **Install EasyOCR** (if not already installed):
   ```bash
   pip3 install easyocr
   # Language models (~140MB) download on first use
   ```

2. **Update** `scrapers/scrape_meetings.py` with the URL

3. **Test with a small sample** (OCR is slow):
   ```bash
   # Edit scrape_meetings.py to set limit=2
   python3 scrapers/scrape_meetings.py
   ```

4. **Be patient**: OCR can take 5-10 minutes per document

## Next Steps

Once you've scraped some documents:

1. **Explore the data** in Datasette
2. **Search for advocacy topics**: walkability, parking, density, etc.
3. **Export findings** as CSV for analysis
4. **Share your discoveries** to support walkable Lahore!

## Need Help?

- Check `README.md` for full documentation
- Check `SETUP.md` for installation issues
- The database schema is in `database/schema.py`
- All scrapers are in `scrapers/` directory

---

**Ready to start? Run: `python3 reconnaissance.py`**
