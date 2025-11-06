# 🚀 Quick Start: Using Gemini 2.0 Flash

Get started with Gemini 2.0 Flash in under 2 minutes!

## Why Gemini?
- **10x Cheaper** than Claude Sonnet 4.5
- **Faster** processing times
- **Good quality** for blog content analysis
- Perfect for **high-volume** processing

## Setup (2 minutes)

### Step 1: Get Your API Key
1. Go to https://makersuite.google.com/app/apikey
2. Sign in with your Google account
3. Click "Create API Key"
4. Copy the key (starts with `AIza...`)

### Step 2: Set Environment Variable

**MacOS/Linux:**
```bash
export GEMINI_API_KEY="AIza-your-actual-key-here"
```

**Windows (PowerShell):**
```powershell
$env:GEMINI_API_KEY="AIza-your-actual-key-here"
```

**Or add to .env file:**
```bash
echo 'GEMINI_API_KEY="AIza-your-actual-key-here"' >> .env
```

### Step 3: Run the App
```bash
streamlit run app.py --server.port 5000
```

### Step 4: Select Gemini
1. Open the app in your browser
2. Expand "⚙️ AI Model Settings"
3. Select "Gemini 2.0 Flash"
4. Start analyzing!

## First Analysis

Try it with a small batch first:

1. Enter a blog URL (e.g., `https://blog.example.com`)
2. Set max posts to **5-10** for testing
3. Click "🚀 Analyze Blog Posts"
4. Watch it process in ~30-60 seconds!

## Cost Comparison

**Example: 100 blog posts**
- With Claude: $5-8 💰
- With Gemini: $0.50-1 ✨ **(10x cheaper!)**

**Example: 500 blog posts**
- With Claude: $25-40 💰
- With Gemini: $2.50-5 ✨ **(10x cheaper!)**

## When to Use Gemini

✅ **Perfect for:**
- Processing 50+ blog posts at once
- Initial broad research phase
- Testing/prototyping your workflow
- Budget-conscious projects
- Fast turnaround needed

❌ **Consider Claude instead for:**
- Highly technical/complex content
- When absolute best quality needed
- Regulatory/compliance content
- Only 5-10 critical posts

## Tips for Best Results

### 1. Start Small
Test with 10 posts before processing hundreds.

### 2. Hybrid Approach
```
1. Process all 500 posts with Gemini ($5)
2. Identify top 50 most important posts
3. Re-process those 50 with Claude ($4)
Total: $9 (instead of $40 all-Claude)
```

### 3. Check Quality
Review the first few results to ensure quality meets your needs.

### 4. Use Checkpoints
For large batches, the checkpoint system auto-saves every 10 posts.

## Troubleshooting

### "API key not configured"
```bash
# Check if variable is set
echo $GEMINI_API_KEY

# If empty, export it again
export GEMINI_API_KEY="AIza-your-key"
```

### Import Error
```bash
# Reinstall the package
pip3 install --upgrade google-generativeai
```

### Rate Limits
Gemini has generous free tier limits:
- 15 requests per minute
- 1 million tokens per minute
- 1,500 requests per day

The app respects these with built-in rate limiting.

## Next Steps

1. ✅ Complete your first analysis with Gemini
2. 📊 Compare results with Claude (optional)
3. 📚 Read [MODEL_GUIDE.md](./MODEL_GUIDE.md) for advanced usage
4. 🎯 Scale up to larger batches with confidence

## Need Help?

- **Documentation**: See [README.md](./README.md)
- **Model Comparison**: See [MODEL_GUIDE.md](./MODEL_GUIDE.md)
- **Technical Details**: See [WARP.md](./WARP.md)

---

**Happy analyzing! 🚀**

*Pro tip: Start with Gemini for all your blog research needs. You'll save money and time while getting quality insights.*
