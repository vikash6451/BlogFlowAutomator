# Blog Post Analyzer & Summarizer

## Overview

The Blog Post Analyzer is an automated blog research tool that scrapes blog posts from listing pages, processes them using AI to extract summaries and categorizations, and clusters similar posts together using embeddings. The application uses Streamlit for the user interface, enabling users to input blog listing URLs and receive structured analysis of multiple blog posts with clustering insights.

**Core Functionality:**
- Scrapes blog posts from listing pages
- Extracts clean text content from individual blog posts
- Uses Claude (Anthropic) to categorize, summarize, and extract deep insights from posts
- Generates embeddings using OpenAI to cluster similar posts
- Extracts 5 types of deep insights per post for brainstorming: central takeaways, contrarian perspectives, unstated assumptions, potential experiments, and industry applications
- Provides downloadable markdown reports and data exports optimized for ChatGPT Projects and Claude Skills
- Uses Replit Object Storage for file persistence
- **Checkpoint-based resilience:** Automatically saves progress every 10 posts and allows resuming from interruptions

## User Preferences

Preferred communication style: Simple, everyday language.

## System Architecture

### Frontend Architecture

**Framework:** Streamlit web application

The application uses Streamlit's session state management to maintain processed data across interactions, storing:
- Processed blog post data
- Markdown content for export
- Scraped post metadata
- Cluster analysis results

**User Flow:**
1. User inputs blog listing page URL
2. Optionally limits number of posts or processes all
3. Application scrapes, processes, and clusters posts
4. Results displayed with dual view options:
   - **Topic Clusters (AI-Discovered):** Semantic groupings based on content similarity
   - **AI Categories:** Traditional category-based organization
5. Downloadable exports organized by discovered topics

### Backend Architecture

**Scraping Layer** (`scraper.py`)
- **Primary Tool:** Trafilatura for content extraction
- **Fallback Strategy:** BeautifulSoup for cases where Trafilatura fails
- **Problem Addressed:** Extracting clean blog content from varied HTML structures and following pagination
- **Solution:** Multi-strategy approach with header spoofing and semantic HTML selectors
- **Pagination Support:** Automatically detects and follows pagination links (e.g., /page/2/, /page/3/, ?page=2)
- **Pagination Limit:** Configurable max_pages (default: 10) to prevent excessive scraping
- **Pagination Patterns:** Detects common pagination selectors, rel="next" links, numeric page links, and text-based links ("Next", "Previous", "Older", "Newer")
- **Smart Link Scoring:** Awards points for blog patterns, dates, content depth while filtering admin pages
- **Pros:** Handles diverse blog platforms; robust fallback mechanisms; automatically scrapes all pages
- **Cons:** May struggle with heavily JavaScript-rendered content

**AI Processing Layer** (`ai_processor.py`)
- **Switchable AI Models:** Claude (Anthropic) or GPT-4o (OpenAI) - configurable via `USE_OPENAI` flag in app.py
- **Default Model:** Claude Sonnet 4.5 (Anthropic)
- **Alternative Model:** GPT-4o (OpenAI) with structured JSON outputs
- **Problem Addressed:** Automated categorization, summarization, and deep insight extraction at scale
- **Solution:** Batch processing with concurrent requests (ThreadPoolExecutor); two sequential AI calls per post
- **Rate Limiting Strategy:** Exponential backoff with 7 retry attempts
- **Categorization:** Fixed taxonomy (Technology, Business, Marketing, Design, etc.)
- **Deep Insights:** Extracts 5 analysis dimensions - central takeaways, contrarian perspectives, unstated assumptions, potential experiments, industry applications
- **Output:** Structured JSON with fallback parsing for robust error handling
- **API Key Management:** Uses Replit AI Integrations for Claude, account-level OPENAI_API_KEY for OpenAI
- **Switching:** Change `USE_OPENAI = True` in app.py to switch from Claude to OpenAI
- **Pros:** Comprehensive analysis for brainstorming; structured output via JSON; robust error handling; model flexibility
- **Cons:** API costs scale with post volume; ~2x cost per post due to dual analysis calls

**Clustering Layer** (`embedding_cluster.py`)
- **Status:** Currently disabled (set `ENABLE_CLUSTERING = False` in app.py)
- **Embedding Model:** OpenAI text-embedding-3-large
- **Clustering Algorithm:** K-means with silhouette score optimization
- **Problem Addressed:** Grouping similar posts for pattern recognition
- **Solution:** Automatic optimal cluster determination (2-10 clusters)
- **Input Data:** Combines title + summary + main points for semantic richness
- **Batch Processing:** 100 texts per embedding request
- **Error Handling:** Graceful fallback to AI categories if OpenAI API key missing
- **Edge Cases:** Handles single-post scenarios (returns single cluster)
- **Pros:** Identifies content patterns; scalable batching; automatic topic discovery
- **Cons:** Requires OpenAI API key; clustering quality depends on post similarity
- **Note:** To re-enable, change `ENABLE_CLUSTERING = True` at the top of app.py

**AI Cluster Labeling** (`ai_processor.py`)
- **Purpose:** Generate meaningful labels and themes for discovered topic clusters
- **Method:** Claude analyzes post titles and summaries within each cluster
- **Output:** Topic label (2-5 words), cluster summary, and key themes

### Data Flow

1. **Scraping Phase:** URL → Blog links extraction → Individual post scraping
2. **Processing Phase:** Raw content → Claude analysis → Structured summaries
3. **Clustering Phase:** Summaries → OpenAI embeddings → K-means clustering → Labeled groups
4. **Export Phase:** Structured data → Markdown/ZIP generation → Replit Object Storage

### Concurrency & Performance

**Batch Processing Strategy:**
- AI processing uses ThreadPoolExecutor (default 2 concurrent workers)
- Embedding generation batches in groups of 100
- Rate limit handling with exponential backoff (2-128 seconds)
- Real-time progress tracking via callbacks updates UI during AI processing

**User Controls:**
- Post limit slider: 1-100 posts (allows testing with minimal posts)
- Process all checkbox: Processes entire blog listing (no limit)

**Rationale:** Balance between throughput and API rate limits to prevent request failures while maintaining reasonable processing times.

### Error Handling

**Rate Limit Detection:** Multi-signal approach checking for HTTP 429, "RATELIMIT_EXCEEDED", quota messages, and status codes

**Retry Strategy:** 
- 7 retry attempts with exponential backoff
- Specific retry condition for rate limit errors only
- Reraises non-rate-limit exceptions immediately

**Clustering Error Handling:**
- Missing OpenAI API key: Shows user-friendly warning and falls back to AI categories
- Single post scenario: Returns single cluster without invoking KMeans
- API failures: Gracefully degrades to category-based organization

**Alternatives Considered:** Simple retry without backoff (rejected due to continued rate limit hits); circuit breaker pattern (unnecessary for single-user tool)

### Checkpoint System (`checkpoint_manager.py`)

**Purpose:** Enable resilient blog analysis for large datasets (100+ posts) by saving incremental progress

**CheckpointManager Class:**
- **Storage:** Uses Replit Object Storage with `checkpoint_` prefix
- **Checkpoint Interval:** Every 10 posts processed
- **Data Stored:** run_id, URL, scraped_links, processed_results, last_index, total_posts, status, timestamp

**User Flow:**
1. **New Analysis:** Processing starts → checkpoint created after 10 posts → saves every 10 posts
2. **Interruption:** If browser disconnects/API fails → checkpoint remains "in_progress"
3. **Resume:** On app reload → incomplete checkpoints shown → click "Resume" → continues from last checkpoint
4. **Completion:** All posts processed → marked "completed" → auto-cleanup of old checkpoints (7 days)

**Implementation:**
- **run_id:** Unique 8-character UUID per run, stored in session state
- **Progress Callback:** Modified AI processing to save checkpoint every 10 posts
- **Error Handling:** Partial results saved if processing fails mid-run
- **Cleanup:** Automatic deletion of completed checkpoints >7 days old

**Edge Cases:**
- Failed checkpoint load → fallback to new analysis with error
- Browser disconnection → checkpoint persists, resumable
- Duplicate saves → reuses same run_id

## External Dependencies

### AI & ML Services

**Anthropic Claude API**
- **Purpose:** Blog post categorization and summarization
- **Configuration:** 
  - API Key: `AI_INTEGRATIONS_ANTHROPIC_API_KEY`
  - Base URL: `AI_INTEGRATIONS_ANTHROPIC_BASE_URL` (optional override)
- **Integration:** Direct SDK usage with custom retry logic
- **Model:** Not specified in code (uses default)

**OpenAI API**
- **Purpose:** Text embeddings for semantic clustering
- **Configuration:** `OPENAI_API_KEY` environment variable
- **Model:** text-embedding-3-large (3072-dimensional embeddings)
- **Note:** Code comment mentions GPT-5 but is only relevant for completions, not embeddings

### Web Scraping

**Trafilatura**
- **Purpose:** Primary content extraction from HTML
- **Features:** Comment filtering, table inclusion, fallback mechanisms

**BeautifulSoup4**
- **Purpose:** Fallback HTML parsing and DOM manipulation
- **Usage:** Removes navigation, headers, footers, scripts when Trafilatura fails

**Requests**
- **Purpose:** HTTP requests with custom headers
- **Configuration:** User-Agent spoofing to avoid bot detection

### Data Science & ML

**scikit-learn**
- **Components:** KMeans clustering, silhouette score calculation
- **Purpose:** Optimal cluster determination and post grouping

**NumPy**
- **Purpose:** Array operations for embedding manipulation

### Storage & UI

**Replit Object Storage Client**
- **Purpose:** Persistent file storage for exports
- **Use Case:** Storing generated ZIP files and markdown reports

**Streamlit**
- **Purpose:** Web application framework
- **Features:** Session state management, file downloads, interactive controls

### Utility Libraries

**tenacity**
- **Purpose:** Retry logic with exponential backoff
- **Configuration:** 7 attempts, 2-128 second wait range

**concurrent.futures**
- **Purpose:** Thread-based parallelism for AI processing