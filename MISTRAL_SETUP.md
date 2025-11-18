# Mistral 7B Integration Setup Guide

Mistral 7B support has been successfully added to BlogFlowAutomator! This guide will help you set it up.

## What's New

The app now supports **Mistral 7B** (open-mistral-7b) as an additional AI model option for blog post analysis, alongside Claude, OpenAI, Gemini, and OpenRouter.

## Setup Instructions

### 1. Get Your Mistral API Key

1. Visit [Mistral AI Console](https://console.mistral.ai)
2. Sign up or log in to your account
3. Navigate to API Keys section
4. Create a new API key
5. Copy the key (it starts with something like `xxx...`)

### 2. Set the API Key as Environment Variable

You can set the API key in several ways:

#### Option A: Terminal (Temporary - for current session)
```bash
export MISTRAL_API_KEY="your-api-key-here"
```

#### Option B: Shell Profile (Permanent)
Add to your `~/.zshrc` or `~/.bashrc`:
```bash
echo 'export MISTRAL_API_KEY="your-api-key-here"' >> ~/.zshrc
source ~/.zshrc
```

#### Option C: Streamlit Secrets (Local Development)
Create/edit `.streamlit/secrets.toml`:
```toml
MISTRAL_API_KEY = "your-api-key-here"
```

#### Option D: Replit Secrets (If using Replit)
Go to Replit Secrets and add:
- Key: `MISTRAL_API_KEY`
- Value: your API key

### 3. Install Dependencies

The `mistralai` package has already been added to `pyproject.toml`. If you need to install it manually:

```bash
# If using uv (recommended by the project)
uv pip install mistralai

# Or using standard pip
pip install mistralai

# Or using python3 -m pip
python3 -m pip install mistralai
```

### 4. Run the Application

```bash
streamlit run app.py --server.port 5000
```

### 5. Select Mistral in the UI

1. Open the app in your browser
2. Expand the "⚙️ AI Model Settings" section
3. Select "Mistral 7B" from the radio buttons
4. The app will now use Mistral for all blog analysis

## How It Works

### Model Used
- **Model**: `open-mistral-7b` (Mistral's 7B parameter model)
- **Max Tokens**: 8192
- **Response Format**: JSON mode enabled for structured outputs

### API Calls
The integration makes two types of API calls for each blog post:

1. **Categorization & Summary** (`categorize_and_summarize_post_mistral`)
   - Assigns a category (Technology, Business, Marketing, etc.)
   - Generates a 2-3 sentence summary
   - Extracts 3-5 main points
   - Identifies specific examples

2. **Deep Insights** (`extract_deep_insights_mistral`)
   - Central takeaways (3-5 key ideas)
   - Contrarian/counterintuitive insights
   - Unstated assumptions
   - Potential experiments
   - Industry applications

### Rate Limiting
- Uses the same retry logic as other models (exponential backoff)
- Max 7 retry attempts with 2s to 128s wait times
- Processes 2 posts concurrently (same as other models)

## Pricing (as of Jan 2025)

Mistral 7B is very cost-effective:
- **Input**: ~$0.25 per 1M tokens
- **Output**: ~$0.25 per 1M tokens

For a typical blog post analysis (~6000 tokens input + ~1000 tokens output):
- Cost per post: ~$0.002 (less than a cent!)
- 100 posts: ~$0.20

This makes it one of the most affordable options compared to GPT-4o, Claude, etc.

## Model Comparison

| Model | Strengths | Cost (approx) |
|-------|-----------|---------------|
| **Mistral 7B** | Fast, cost-effective, good for structured tasks | $ |
| Claude Sonnet 4.5 | Best quality, deep reasoning | $$$$ |
| Gemini 2.0 Flash | Fast, good quality, free tier available | $$ |
| GPT-4o | Strong reasoning, JSON mode | $$$ |
| Qwen 2.5 72B | Large context, via OpenRouter | $$ |

## Code Changes Made

1. **ai_processor.py**
   - Added `from mistralai import Mistral`
   - Added `get_use_mistral()` function
   - Added `mistral_client` initialization
   - Added `extract_deep_insights_mistral()` function
   - Added `categorize_and_summarize_post_mistral()` function
   - Updated routing logic in main functions

2. **app.py**
   - Added "Mistral 7B" to model selection radio buttons
   - Added `USE_MISTRAL` flag and environment variable handling
   - Updated API key setup instructions
   - Updated footer with Mistral mention

3. **pyproject.toml**
   - Added `mistralai>=1.0.0` to dependencies

## Testing the Integration

Try analyzing a few blog posts with Mistral selected:

```bash
# Set your API key
export MISTRAL_API_KEY="your-key"

# Run the app
streamlit run app.py --server.port 5000

# In the UI:
# 1. Expand "AI Model Settings"
# 2. Select "Mistral 7B"
# 3. Enter a blog listing URL
# 4. Start with 3-5 posts to test
```

## Troubleshooting

### Error: "mistralai module not found"
```bash
python3 -m pip install mistralai
```

### Error: API key not found
Make sure you've set the environment variable and restarted the Streamlit app:
```bash
export MISTRAL_API_KEY="your-key"
streamlit run app.py --server.port 5000
```

### Error: Rate limit exceeded
The retry logic should handle this automatically. If it persists:
- Wait a few minutes before retrying
- Check your Mistral API quota/limits
- Consider upgrading your Mistral plan

## Support

For Mistral-specific issues:
- [Mistral Documentation](https://docs.mistral.ai)
- [Mistral API Reference](https://docs.mistral.ai/api)
- [Mistral Discord](https://discord.gg/mistralai)

For BlogFlowAutomator issues:
- Check existing codebase documentation
- Review `WARP.md` for project context
