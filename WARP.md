# WARP.md

This file provides guidance to WARP (warp.dev) when working with code in this repository.

## Project Overview

BlogFlowAutomator is a Streamlit web application that automates blog content analysis. It scrapes blog posts from listing pages, uses Claude AI to categorize and summarize content, and generates structured markdown knowledge bases for use in AI projects.

**Primary Use Case:** Accelerate blog research by transforming multiple blog posts into organized, AI-ready knowledge bases that can be uploaded to ChatGPT Projects or Claude Projects.

## Development Commands

### Running the Application

```bash
streamlit run app.py --server.port 5000
```

The app runs on port 5000 and is configured for headless deployment (see `.streamlit/config.toml`).

### Dependency Management

This project uses `uv` for Python dependency management:

```bash
# Install dependencies
uv pip install -e .

# Add a new dependency
uv add <package-name>
```

Dependencies are defined in `pyproject.toml` and locked in `uv.lock`.

### Environment Variables

Required environment variables (set by Replit AI Integrations):
- `AI_INTEGRATIONS_ANTHROPIC_API_KEY`: Anthropic API key for Claude
- `AI_INTEGRATIONS_ANTHROPIC_BASE_URL`: Custom base URL for Anthropic API

## Architecture

### Core Components

**1. Web Scraping Layer (`scraper.py`)**
- `extract_blog_links()`: Discovers blog post URLs from listing pages using intelligent scoring
  - Scores links based on URL patterns (dates, blog keywords)
  - Filters out navigation, admin, and static resource links
  - Prioritizes article containers and semantic HTML
- `get_website_text_content()`: Extracts clean text from blog posts
  - Primary: Uses `trafilatura` for content extraction
  - Fallback: BeautifulSoup with semantic selectors (`article`, `main`, `.post-content`)
  - Removes navigation, scripts, and chrome elements
- `scrape_blog_post()`: Wrapper that combines URL and extracted content

**2. AI Processing Layer (`ai_processor.py`)**
- `categorize_and_summarize_post()`: Calls Claude Sonnet 4.5 to analyze blog content
  - Categories: Technology, Business, Marketing, Design, Development, Product, Data Science, AI/ML, DevOps, Security, Other
  - Outputs: JSON with category, summary, main_points, examples
  - Includes retry logic with exponential backoff for rate limits
- `process_posts_batch()`: Concurrent processing with `ThreadPoolExecutor`
  - **Important:** Limited to 2 concurrent workers to respect API rate limits
  - Maintains order of results using indexed futures
  - Handles failures gracefully without stopping batch

**3. Streamlit UI Layer (`app.py`)**
- Main workflow orchestration and user interface
- Session state management for processed data
- Generates two output formats:
  - **Analysis Summary**: Categorized markdown with AI summaries, key takeaways, examples
  - **Full Content ZIP**: Individual markdown files for each blog post
- Replit Object Storage integration for persistence

### Data Flow

1. User inputs blog listing URL → `extract_blog_links()`
2. Links filtered and scored → user selects limit or processes all
3. Each URL scraped → `scrape_blog_post()` → returns content
4. Batch sent to `process_posts_batch()` → 2 concurrent Claude API calls
5. Results categorized and formatted into markdown knowledge base
6. Outputs saved to Object Storage and offered as downloads

### Key Design Patterns

**Rate Limit Handling:**
- `@retry` decorator with exponential backoff (2s to 128s)
- Custom `is_rate_limit_error()` catches multiple rate limit indicators
- Max 7 retry attempts before failing
- Only 2 concurrent API requests to avoid overwhelming limits

**Progressive Enhancement:**
- Primary scraping (trafilatura) → fallback (BeautifulSoup) → graceful failure
- If Claude JSON parsing fails, returns default structure with 'Other' category
- Scraping errors collected but don't halt processing

**User Experience:**
- Progress bars during long operations
- Expandable error logs for failed scrapes
- Time estimates for large batches (10s per post assumption)
- Two download options for different use cases

## Working with This Codebase

### Modifying Scraping Logic

The scraping heuristics in `score_link()` may need adjustment for different blog platforms:
- **blog_path_keywords**: Add domain-specific path patterns
- **date_pattern**: Modify regex if blog uses non-standard date formats
- **article_selectors**: Add CSS selectors for custom blog themes

### Changing AI Behavior

To modify categorization or output format:
1. Edit the prompt in `categorize_and_summarize_post()`
2. Update the JSON schema in the prompt
3. Adjust parsing logic (lines 62-80 in `ai_processor.py`)
4. Update markdown generation in `app.py` (lines 122-184)

### Adjusting Concurrency

The `ThreadPoolExecutor` is set to `max_workers=2` in `process_posts_batch()`. Increasing this will:
- Speed up processing but increase rate limit risk
- Require testing with your specific API quota
- May need adjustment to retry parameters

### Storage Integration

The app uses Replit Object Storage (lines 188-197 in `app.py`):
- Falls back gracefully if storage unavailable
- Files listed from storage in UI (lines 322-346)
- To use different storage, replace `replit.object_storage.Client()`

## Python Version

Requires Python 3.11+ (specified in `pyproject.toml` and `.replit`)
