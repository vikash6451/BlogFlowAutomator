# AI Model Switching Guide

BlogFlowAutomator now supports three AI models: **Claude Sonnet 4.5**, **Gemini 2.0 Flash**, and **OpenAI GPT-4o**. This guide helps you choose and configure the right model for your needs.

## Quick Start

### Option 1: Use the UI (Recommended)
1. Run the app: `streamlit run app.py --server.port 5000`
2. Expand "⚙️ AI Model Settings"
3. Select your preferred model
4. Enter your blog URL and start analyzing

### Option 2: Edit Configuration File
Edit `app.py` and change these lines (around line 15-19):

```python
# AI Model Selection (set one to True)
USE_CLAUDE = True   # Claude Sonnet 4.5 (default)
USE_OPENAI = False  # OpenAI GPT-4o
USE_GEMINI = False  # Gemini 2.0 Flash ⚡
```

## Required API Keys

### Claude Sonnet 4.5
```bash
export ANTHROPIC_API_KEY="sk-ant-..."
```
Or for Replit AI Integrations:
```bash
export AI_INTEGRATIONS_ANTHROPIC_API_KEY="..."
export AI_INTEGRATIONS_ANTHROPIC_BASE_URL="..."
```

### Gemini 2.0 Flash ⚡ NEW
```bash
export GEMINI_API_KEY="AIza..."
```
Get your key at: https://makersuite.google.com/app/apikey

### OpenAI GPT-4o
```bash
export OPENAI_API_KEY="sk-..."
```

## Model Comparison

| Feature | Claude Sonnet 4.5 | Gemini 2.0 Flash | GPT-4o |
|---------|------------------|------------------|--------|
| **Cost** | $$$ | $ | $$ |
| **Speed** | Moderate | Fast | Moderate |
| **Quality** | Excellent | Good | Very Good |
| **Context Window** | 200K tokens | 128K tokens | 128K tokens |
| **JSON Reliability** | High | Good | High |
| **Best For** | High-stakes analysis | Large batches | General purpose |

## Cost Estimates (per 100 blog posts)

Assuming average blog post = 2000 tokens input, 500 tokens output per analysis:

- **Claude Sonnet 4.5**: ~$5-8
- **Gemini 2.0 Flash**: ~$0.50-1 (10x cheaper!) ⚡
- **OpenAI GPT-4o**: ~$3-5

*Note: Costs are approximate and depend on actual token usage*

## When to Use Each Model

### Use Claude Sonnet 4.5 when:
- ✅ Quality is paramount
- ✅ You need nuanced understanding of complex topics
- ✅ Budget is not a primary concern
- ✅ Processing 10-50 high-value articles

### Use Gemini 2.0 Flash when:
- ✅ Processing hundreds of blog posts
- ✅ Cost efficiency is important
- ✅ Fast turnaround needed
- ✅ Content analysis at scale
- ✅ Testing/prototyping workflows

### Use OpenAI GPT-4o when:
- ✅ You already have OpenAI credits
- ✅ You want balanced cost/quality
- ✅ Integrating with other OpenAI services
- ✅ Moderate batch sizes (50-100 posts)

## Testing Different Models

You can test all three models on the same content to compare results:

1. **First run with Gemini** (cheap, fast overview)
2. **Spot-check with Claude** (validate quality on key posts)
3. **Use GPT-4o** for production (if you prefer OpenAI ecosystem)

## Switching Models Mid-Session

**Important**: Model selection happens when you click "Analyze Blog Posts". To switch models:
1. Change the model in settings
2. Click "Analyze" again (this will re-process)
3. Or restart the app to clear session state

## Performance Tips

### For Large Batches (100+ posts):
- Start with **Gemini 2.0 Flash** for initial processing
- Use checkpoint/resume feature if interrupted
- Process in chunks of 50-100 posts

### For Maximum Quality:
- Use **Claude Sonnet 4.5**
- Reduce concurrent workers to 1 in `ai_processor.py` (line 431)
- This prevents rate limits and maximizes quality

### For Speed:
- Use **Gemini 2.0 Flash**
- Keep concurrent workers at 2 (default)
- Gemini has generous rate limits

## Troubleshooting

### "API key not configured"
Check your environment variable matches your selected model:
```bash
# Check which keys are set
echo $ANTHROPIC_API_KEY
echo $GEMINI_API_KEY
echo $OPENAI_API_KEY
```

### Rate Limit Errors
All models have built-in retry logic with exponential backoff. If you still hit limits:
- **Claude**: Reduce to 1 concurrent worker
- **Gemini**: Usually not an issue (high limits)
- **OpenAI**: Check your tier limits on platform.openai.com

### Quality Issues
If Gemini results aren't meeting quality standards:
- Switch to Claude for critical content
- Use Gemini for volume, Claude for quality validation
- Adjust prompts in `ai_processor.py` if needed

## API Key Security

Never commit API keys to version control. Use:
- Environment variables (`.env` file with `.gitignore`)
- Secret management services
- Replit Secrets (if on Replit)

## Example Workflow

**High-volume research project:**
```bash
# Week 1: Broad research with Gemini (1000 posts, $10)
export GEMINI_API_KEY="..."
streamlit run app.py
# Select "Gemini 2.0 Flash" in UI

# Week 2: Deep dive with Claude (50 key posts, $4)
export ANTHROPIC_API_KEY="..."
streamlit run app.py
# Select "Claude Sonnet 4.5" in UI
```

## Need Help?

- Check the main [README.md](./README.md) for setup instructions
- See [WARP.md](./WARP.md) for technical architecture
- Open an issue for bugs or feature requests
