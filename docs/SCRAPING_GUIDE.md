# Canada.ca Web Scraping Guide

## Overview

This document outlines best practices and strategies for scraping content from canada.ca for the RAG-based chat agent.

---

## Scraping Approaches

### 1. Curated URL List (Current Implementation)

**Best for:** Initial development, specific sections, maximum control

```python
# src/scraper/ingestion.py
CANADA_TAX_URLS = [
    "https://www.canada.ca/en/services/taxes.html",
    "https://www.canada.ca/en/services/taxes/income-tax.html",
    # ... manually curated URLs
]
```

**When to use:**
- Starting a new section
- When you need precise control over content
- For high-quality, hand-picked pages

---

### 2. Sitemap-Based Discovery (Recommended for Scale)

**Best for:** Complete sections, automatic discovery, incremental updates

canada.ca has a well-structured sitemap system:
- **Main Index:** `https://www.canada.ca/sitemap.xml`
- **Section Sitemaps:** `https://www.canada.ca/en/{department}.sitemap.xml`

**Key sitemaps for taxes:**
- `https://www.canada.ca/en/revenue-agency.sitemap.xml` - CRA pages

**Advantages:**
- Includes `<lastmod>` dates for change detection
- Official list of published pages
- Automatically picks up new pages

---

### 3. Recursive Crawling (Link Following)

**Best for:** Discovering interconnected content, finding orphan pages

**Caution:** 
- Set depth limits
- Filter by URL patterns
- Respect rate limits

---

## Best Practices

### 1. Respect robots.txt ✅

canada.ca's robots.txt allows most scraping. **Blocked paths:**
- `/content/dam/cra-arc/formspubs/` - PDF forms
- `/en/sr/srb.html` - Search pages
- `/en/service-canada/` - Service Canada section

### 2. Rate Limiting

```python
# Recommended: 1-2 seconds between requests
RATE_LIMIT_SECONDS = 1.5

# Be extra polite during business hours (EST)
async def polite_delay():
    await asyncio.sleep(RATE_LIMIT_SECONDS)
```

### 3. Identify Your Bot

```python
HEADERS = {
    "User-Agent": "CanadaCaBot/1.0 (RAG Research; contact@example.com)",
    "Accept": "text/html",
    "Accept-Language": "en-CA, fr-CA",
}
```

### 4. Handle Errors Gracefully

- Retry 5xx errors with exponential backoff
- Skip 404s but log them
- Don't retry 403s (you're blocked)

### 5. Store Raw HTML

Keep the original HTML for reprocessing:
```python
# Store both raw and processed content
document = {
    "url": url,
    "raw_html": html,
    "content": extracted_text,
    "scraped_at": datetime.utcnow(),
}
```

### 6. Incremental Updates

Use `lastmod` from sitemaps or `Last-Modified` headers:
```python
async def should_update(url: str, stored_modified: datetime) -> bool:
    response = await client.head(url)
    last_modified = response.headers.get("Last-Modified")
    return parse_date(last_modified) > stored_modified
```

---

## Recommended Workflow

### Phase 1: Initial Scrape

```bash
# Start with curated URLs for the tax section
python scripts/run_scraper.py --taxes-en

# Add French tax pages
python scripts/run_scraper.py --all-taxes
```

### Phase 2: Expand via Sitemap

```bash
# Scrape all CRA pages from sitemap
python scripts/run_scraper.py --sitemap https://www.canada.ca/en/revenue-agency.sitemap.xml

# Filter to only tax-related pages
python scripts/run_scraper.py --sitemap-filter "/services/taxes"
```

### Phase 3: Nightly Updates

```bash
# Check for changes and update only modified pages
python scripts/run_scraper.py --incremental --since yesterday
```

---

## URL Patterns to Include

### Tax Section (English)
```
https://www.canada.ca/en/services/taxes/*
https://www.canada.ca/en/revenue-agency/services/*
https://www.canada.ca/en/revenue-agency/programs/*
```

### Tax Section (French)
```
https://www.canada.ca/fr/services/impots/*
https://www.canada.ca/fr/agence-revenu/services/*
https://www.canada.ca/fr/agence-revenu/programmes/*
```

### URLs to Exclude
```
# Dynamic/personalized pages
*my-account*
*mon-dossier*

# Forms and PDFs
*.pdf
*/forms/*
*/formulaires/*

# Search and utility pages
*/search*
*/rechercher*
*/contact*
```

---

## Implementation: Sitemap Scraper

See `src/scraper/sitemap.py` for the sitemap-based implementation.

---

## Estimated Content Volume

| Section | Est. Pages | Est. Chunks |
|---------|-----------|-------------|
| Tax Services Hub | ~50 | ~500 |
| CRA Services | ~200 | ~2,000 |
| Full Tax Section | ~500 | ~5,000 |

---

## Monitoring & Quality

### Metrics to Track
- Pages scraped vs. failed
- Average page size
- Content language distribution
- Duplicate content detection
- Broken links discovered

### Quality Checks
- Minimum content length (reject < 100 words)
- Language validation
- No boilerplate-only pages
- Valid UTF-8 encoding

---

## Legal Considerations

1. **Government Content License:** canada.ca content is generally Crown Copyright with liberal reuse terms
2. **Rate Limiting:** Excessive requests could be seen as abuse
3. **No Personal Data:** Never scrape authenticated/personal sections
4. **Attribution:** Cite sources properly in responses
