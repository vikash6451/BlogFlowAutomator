# BlogFlowAutomator

A Streamlit web application that automates blog content analysis. Scrapes blog posts from listing pages, uses AI to categorize and summarize content, and generates structured markdown knowledge bases for use in AI projects.

## Features

- **Multi-Model Support**: Choose between Claude Sonnet 4.5, Gemini 2.0 Flash, or OpenAI GPT-4o
- **Intelligent Web Scraping**: Extracts blog posts from listing pages using smart heuristics
- **AI-Powered Analysis**: Categorizes, summarizes, and extracts deep insights from blog content
- **Batch Processing**: Handles multiple posts concurrently with rate limit protection
- **Checkpoint System**: Resume interrupted analysis sessions
- **Multiple Export Formats**: Download as markdown summary or full content ZIP
- **Persistent Storage**: Saves analysis results for future reference

## AI Model Options

### Claude Sonnet 4.5 (Default)
- **Best for**: High-quality analysis and nuanced understanding
- **API Key**: `ANTHROPIC_API_KEY` or `AI_INTEGRATIONS_ANTHROPIC_API_KEY`
- **Cost**: Higher per token, excellent quality

### Gemini 2.0 Flash ⚡
- **Best for**: Fast processing and cost-effective analysis
- **API Key**: `GEMINI_API_KEY`
- **Cost**: Very competitive pricing, good quality
- **Speed**: Faster response times

### OpenAI GPT-4o
- **Best for**: Balanced performance and reliability
- **API Key**: `OPENAI_API_KEY`
- **Cost**: Moderate pricing

## Getting Started

### Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd BlogFlowAutomator
```

2. Install dependencies using `uv`:
```bash
uv pip install -e .
```

### Environment Setup

Set up your API key for the model you want to use:

**For Claude:**
```bash
export ANTHROPIC_API_KEY="your-anthropic-api-key"
# OR for Replit AI Integrations
export AI_INTEGRATIONS_ANTHROPIC_API_KEY="your-key"
export AI_INTEGRATIONS_ANTHROPIC_BASE_URL="your-base-url"
```

**For Gemini:**
```bash
export GEMINI_API_KEY="your-gemini-api-key"
```

**For OpenAI:**
```bash
export OPENAI_API_KEY="your-openai-api-key"
```

### Running the Application

```bash
streamlit run app.py --server.port 5000
```

The app will be available at `http://localhost:5000`

## Usage

1. **Select AI Model**: Expand the "⚙️ AI Model Settings" section and choose your preferred AI model
2. **Enter Blog URL**: Paste the URL of a blog listing page
3. **Configure Processing**: Choose to process all posts or limit the number
4. **Analyze**: Click "🚀 Analyze Blog Posts" to start processing
5. **Export Results**: Download as markdown summary or full content ZIP

## Model Selection in Code

To programmatically set the model, edit `app.py`:

```python
# AI Model Selection (set one to True)
USE_CLAUDE = True   # Claude Sonnet 4.5 (default)
USE_OPENAI = False  # OpenAI GPT-4o
USE_GEMINI = False  # Gemini 2.0 Flash
```

Or use the UI toggle in the application itself!

## Output Formats

### Analysis Summary (Markdown)
- AI-generated summaries organized by category or topic
- Key takeaways and examples
- Deep insights including:
  - Central takeaways
  - Contrarian insights
  - Unstated assumptions
  - Potential experiments
  - Industry applications

### Full Content (ZIP)
- Individual markdown files for each blog post
- Complete original content preserved
- Organized with numbered filenames

## Project Structure

```
BlogFlowAutomator/
├── app.py                  # Main Streamlit application
├── ai_processor.py         # AI processing logic (Claude, Gemini, OpenAI)
├── scraper.py             # Web scraping utilities
├── embedding_cluster.py   # Optional semantic clustering
├── checkpoint_manager.py  # Session management
├── storage_adapter.py     # Persistent storage interface
└── pyproject.toml        # Dependencies
```

## Rate Limiting & Concurrency

- **Concurrent Workers**: Limited to 2 simultaneous API requests
- **Retry Logic**: Exponential backoff with up to 7 retry attempts
- **Checkpoints**: Automatically saves progress every 10 posts

## Cost Considerations

| Model | Relative Cost | Speed | Quality |
|-------|--------------|-------|---------|
| Claude Sonnet 4.5 | High | Moderate | Excellent |
| Gemini 2.0 Flash | Low | Fast | Good |
| OpenAI GPT-4o | Medium | Moderate | Very Good |

**Tip**: Start with Gemini 2.0 Flash for large batches to save costs, then use Claude for high-priority analysis.

## Troubleshooting

### "No API key found"
Make sure you've set the correct environment variable for your chosen model.

### Rate Limit Errors
The application has built-in retry logic. If you continue to hit rate limits, the system will automatically back off.

### Scraping Failures
Some blogs may have anti-scraping measures. The app will skip failed posts and continue processing others.

## Development

### Adding a New Model

1. Update `pyproject.toml` with the model's SDK
2. Add client setup in `ai_processor.py`
3. Create model-specific processing functions
4. Update the routing logic in wrapper functions
5. Add UI option in `app.py`

## License

[Your License Here]

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.
