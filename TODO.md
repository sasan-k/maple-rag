# Canada.ca Chat Agent - TODO

## High Priority

### Legal & Compliance
- [ ] **Add Terms and Conditions page**
  - Disclaimer that this is not an official Government of Canada service
  - Data usage and privacy policy
  - Accuracy disclaimer (AI-generated content may contain errors)
  - Citation to official canada.ca sources
  - Contact information

### Scheduled Jobs
- [ ] **Set up scheduled job for nightly updates**
  - Configure cron (Linux) or Task Scheduler (Windows) for nightly incremental ingestion
  - Suggested schedule: Run at 2 AM to minimize disruption
  - Command: `uv run python scripts/incremental_ingest.py --filter "/en/revenue-agency/"`
  - Add logging and monitoring for job failures
  - Consider AWS Lambda or Azure Functions for serverless scheduling

### Bilingual Support
- [ ] **Add French pages by including French sitemap**
  - French sitemap URL: `https://www.canada.ca/fr/agence-revenu.sitemap.xml`
  - Update `incremental_ingest.py` to support both EN and FR sitemaps
  - Add `--include-french` flag to ingestion script
  - Consider running separate jobs for EN and FR for easier monitoring

---

## Medium Priority

### Performance
- [ ] Batch embedding generation (process multiple documents in parallel)
- [ ] Add progress bar for long ingestion jobs
- [ ] Implement retry logic for failed pages

### Monitoring
- [ ] Add ingestion metrics (pages/hour, embedding time, error rate)
- [ ] Create dashboard for scraping status
- [ ] Set up alerts for ingestion failures

### API Enhancements
- [ ] Add pagination to chat history endpoint
- [ ] Implement streaming responses for chat
- [ ] Add admin endpoint to trigger manual ingestion

---

## Low Priority

### Documentation
- [ ] Add API usage examples
- [ ] Create deployment guide for AWS/Azure
- [ ] Document embedding model migration process

### Testing
- [ ] Add unit tests for change detection
- [ ] Add integration tests for ingestion pipeline
- [ ] Add load tests for chat API

---

## Completed ✅

- [x] Set up Azure PostgreSQL and Redis
- [x] Implement AWS Bedrock integration (Claude 3 + Titan Embed)
- [x] Create SitemapParser for URL discovery
- [x] Implement ChangeDetector for incremental updates
- [x] Create incremental ingestion script
- [x] Add database migration for scrape tracking fields
- [x] Test end-to-end RAG pipeline with citations
