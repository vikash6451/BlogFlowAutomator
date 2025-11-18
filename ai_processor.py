import os
from anthropic import Anthropic
from openai import OpenAI
import google.generativeai as genai
from mistralai import Mistral
from concurrent.futures import ThreadPoolExecutor, as_completed
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception
from typing import List, Dict
import json

# Get model selection from environment (set by app.py)
# Note: These are functions so they read the env vars at runtime, not import time
def get_use_openai():
    return os.environ.get("USE_OPENAI", "False").lower() == "true"

def get_use_gemini():
    return os.environ.get("USE_GEMINI", "False").lower() == "true"

def get_use_openrouter():
    return os.environ.get("USE_OPENROUTER", "False").lower() == "true"

def get_use_mistral():
    return os.environ.get("USE_MISTRAL", "False").lower() == "true"

# Claude client setup - try multiple sources for API key
import streamlit as st

# Try to get API key from multiple sources
ANTHROPIC_API_KEY = None
ANTHROPIC_BASE_URL = None

# 1. Try Streamlit secrets (for local dev with secrets.toml)
if hasattr(st, 'secrets') and 'ANTHROPIC_API_KEY' in st.secrets:
    ANTHROPIC_API_KEY = st.secrets['ANTHROPIC_API_KEY']
    ANTHROPIC_BASE_URL = st.secrets.get('ANTHROPIC_BASE_URL', None)
# 2. Try Replit AI Integrations env vars
elif os.environ.get("AI_INTEGRATIONS_ANTHROPIC_API_KEY"):
    ANTHROPIC_API_KEY = os.environ.get("AI_INTEGRATIONS_ANTHROPIC_API_KEY")
    ANTHROPIC_BASE_URL = os.environ.get("AI_INTEGRATIONS_ANTHROPIC_BASE_URL")
# 3. Try standard env var
else:
    ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY")
    ANTHROPIC_BASE_URL = os.environ.get("ANTHROPIC_BASE_URL")

claude_client = Anthropic(
    api_key=ANTHROPIC_API_KEY,
    base_url=ANTHROPIC_BASE_URL
)

# OpenAI client setup
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
openai_client = OpenAI(api_key=OPENAI_API_KEY) if OPENAI_API_KEY else None

# Gemini client setup
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)
    gemini_client = genai.GenerativeModel('gemini-2.0-flash-exp')
else:
    gemini_client = None

# OpenRouter client setup (uses OpenAI SDK since OpenRouter is OpenAI compatible)
OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY")
if OPENROUTER_API_KEY:
    openrouter_client = OpenAI(
        api_key=OPENROUTER_API_KEY,
        base_url="https://openrouter.ai/api/v1"
    )
else:
    openrouter_client = None

# Mistral client setup
MISTRAL_API_KEY = os.environ.get("MISTRAL_API_KEY")
if MISTRAL_API_KEY:
    mistral_client = Mistral(api_key=MISTRAL_API_KEY)
else:
    mistral_client = None


def is_rate_limit_error(exception: BaseException) -> bool:
    error_msg = str(exception)
    return (
        "429" in error_msg
        or "RATELIMIT_EXCEEDED" in error_msg
        or "quota" in error_msg.lower()
        or "rate limit" in error_msg.lower()
        or (hasattr(exception, "status_code") and exception.status_code == 429)
    )


def extract_deep_insights_claude(content: str, title: str) -> Dict:
    """Extract deep insights using Claude API"""
    @retry(
        stop=stop_after_attempt(7),
        wait=wait_exponential(multiplier=1, min=2, max=128),
        retry=retry_if_exception(is_rate_limit_error),
        reraise=True
    )
    def process_with_retry():
        prompt = f"""Analyze this blog post and extract deep insights for brainstorming and strategic thinking:

1. Key Central Takeaways: What are the 3-5 most important ideas that someone should remember from this article?
2. Contrarian Takeaways: What are 3-5 contrarian or counterintuitive insights that challenge conventional thinking?
3. Unstated Assumptions: What assumptions does the author make that aren't explicitly stated?
4. Potential Experiments: What new experiments, tests, or research could be designed based on these ideas?
5. Industry Applications: Which industries or sectors could benefit most from these insights and how?

Blog Title: {title}
Blog Content:
{content[:6000]}

Respond in JSON format:
{{
    "central_takeaways": ["takeaway 1", "takeaway 2", "takeaway 3"],
    "contrarian_takeaways": ["contrarian 1", "contrarian 2", "contrarian 3"],
    "unstated_assumptions": ["assumption 1", "assumption 2", "assumption 3"],
    "potential_experiments": ["experiment 1", "experiment 2", "experiment 3"],
    "industry_applications": ["industry/application 1", "industry/application 2", "industry/application 3"]
}}"""

        message = claude_client.messages.create(
            model="claude-sonnet-4-5",
            max_tokens=8192,
            messages=[{"role": "user", "content": prompt}]
        )
        
        response_text = message.content[0].text if message.content[0].type == "text" else ""
        
        try:
            json_start = response_text.find('{')
            json_end = response_text.rfind('}') + 1
            if json_start != -1 and json_end > json_start:
                response_text = response_text[json_start:json_end]
            
            result = json.loads(response_text)
            return result
        except json.JSONDecodeError:
            return {
                'central_takeaways': [],
                'contrarian_takeaways': [],
                'unstated_assumptions': [],
                'potential_experiments': [],
                'industry_applications': []
            }
    
    return process_with_retry()


def extract_deep_insights_openai(content: str, title: str) -> Dict:
    """Extract deep insights using OpenAI API"""
    @retry(
        stop=stop_after_attempt(7),
        wait=wait_exponential(multiplier=1, min=2, max=128),
        retry=retry_if_exception(is_rate_limit_error),
        reraise=True
    )
    def process_with_retry():
        prompt = f"""Analyze this blog post and extract deep insights for brainstorming and strategic thinking:

1. Key Central Takeaways: What are the 3-5 most important ideas that someone should remember from this article?
2. Contrarian Takeaways: What are 3-5 contrarian or counterintuitive insights that challenge conventional thinking?
3. Unstated Assumptions: What assumptions does the author make that aren't explicitly stated?
4. Potential Experiments: What new experiments, tests, or research could be designed based on these ideas?
5. Industry Applications: Which industries or sectors could benefit most from these insights and how?

Blog Title: {title}
Blog Content:
{content[:6000]}

Respond in JSON format:
{{
    "central_takeaways": ["takeaway 1", "takeaway 2", "takeaway 3"],
    "contrarian_takeaways": ["contrarian 1", "contrarian 2", "contrarian 3"],
    "unstated_assumptions": ["assumption 1", "assumption 2", "assumption 3"],
    "potential_experiments": ["experiment 1", "experiment 2", "experiment 3"],
    "industry_applications": ["industry/application 1", "industry/application 2", "industry/application 3"]
}}"""

        response = openai_client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=8192,
            response_format={"type": "json_object"}
        )
        
        response_text = response.choices[0].message.content
        
        try:
            result = json.loads(response_text)
            return result
        except json.JSONDecodeError:
            return {
                'central_takeaways': [],
                'contrarian_takeaways': [],
                'unstated_assumptions': [],
                'potential_experiments': [],
                'industry_applications': []
            }
    
    return process_with_retry()


def extract_deep_insights_openrouter(content: str, title: str) -> Dict:
    """Extract deep insights using OpenRouter (Qwen3) API"""
    @retry(
        stop=stop_after_attempt(7),
        wait=wait_exponential(multiplier=1, min=2, max=128),
        retry=retry_if_exception(is_rate_limit_error),
        reraise=True
    )
    def process_with_retry():
        prompt = f"""Analyze this blog post and extract deep insights for brainstorming and strategic thinking:

1. Key Central Takeaways: What are the 3-5 most important ideas that someone should remember from this article?
2. Contrarian Takeaways: What are 3-5 contrarian or counterintuitive insights that challenge conventional thinking?
3. Unstated Assumptions: What assumptions does the author make that aren't explicitly stated?
4. Potential Experiments: What new experiments, tests, or research could be designed based on these ideas?
5. Industry Applications: Which industries or sectors could benefit most from these insights and how?

Blog Title: {title}
Blog Content:
{content[:6000]}

Respond in JSON format:
{{
    "central_takeaways": ["takeaway 1", "takeaway 2", "takeaway 3"],
    "contrarian_takeaways": ["contrarian 1", "contrarian 2", "contrarian 3"],
    "unstated_assumptions": ["assumption 1", "assumption 2", "assumption 3"],
    "potential_experiments": ["experiment 1", "experiment 2", "experiment 3"],
    "industry_applications": ["industry/application 1", "industry/application 2", "industry/application 3"]
}}"""

        response = openrouter_client.chat.completions.create(
            model="qwen/qwen-2.5-72b-instruct",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=8192,
            response_format={"type": "json_object"}
        )
        
        response_text = response.choices[0].message.content
        
        try:
            result = json.loads(response_text)
            return result
        except json.JSONDecodeError:
            return {
                'central_takeaways': [],
                'contrarian_takeaways': [],
                'unstated_assumptions': [],
                'potential_experiments': [],
                'industry_applications': []
            }
    
    return process_with_retry()


def extract_deep_insights_gemini(content: str, title: str) -> Dict:
    """Extract deep insights using Gemini API"""
    @retry(
        stop=stop_after_attempt(7),
        wait=wait_exponential(multiplier=1, min=2, max=128),
        retry=retry_if_exception(is_rate_limit_error),
        reraise=True
    )
    def process_with_retry():
        prompt = f"""Analyze this blog post and extract deep insights for brainstorming and strategic thinking:

1. Key Central Takeaways: What are the 3-5 most important ideas that someone should remember from this article?
2. Contrarian Takeaways: What are 3-5 contrarian or counterintuitive insights that challenge conventional thinking?
3. Unstated Assumptions: What assumptions does the author make that aren't explicitly stated?
4. Potential Experiments: What new experiments, tests, or research could be designed based on these ideas?
5. Industry Applications: Which industries or sectors could benefit most from these insights and how?

Blog Title: {title}
Blog Content:
{content[:6000]}

Respond in JSON format:
{{
    "central_takeaways": ["takeaway 1", "takeaway 2", "takeaway 3"],
    "contrarian_takeaways": ["contrarian 1", "contrarian 2", "contrarian 3"],
    "unstated_assumptions": ["assumption 1", "assumption 2", "assumption 3"],
    "potential_experiments": ["experiment 1", "experiment 2", "experiment 3"],
    "industry_applications": ["industry/application 1", "industry/application 2", "industry/application 3"]
}}"""

        response = gemini_client.generate_content(
            prompt,
            generation_config=genai.types.GenerationConfig(
                temperature=0.7,
                max_output_tokens=8192,
            )
        )
        
        response_text = response.text
        
        try:
            json_start = response_text.find('{')
            json_end = response_text.rfind('}') + 1
            if json_start != -1 and json_end > json_start:
                response_text = response_text[json_start:json_end]
            
            result = json.loads(response_text)
            return result
        except json.JSONDecodeError:
            return {
                'central_takeaways': [],
                'contrarian_takeaways': [],
                'unstated_assumptions': [],
                'potential_experiments': [],
                'industry_applications': []
            }
    
    return process_with_retry()


def extract_deep_insights_mistral(content: str, title: str) -> Dict:
    """Extract deep insights using Mistral API"""
    @retry(
        stop=stop_after_attempt(7),
        wait=wait_exponential(multiplier=1, min=2, max=128),
        retry=retry_if_exception(is_rate_limit_error),
        reraise=True
    )
    def process_with_retry():
        prompt = f"""Analyze this blog post and extract deep insights for brainstorming and strategic thinking:

1. Key Central Takeaways: What are the 3-5 most important ideas that someone should remember from this article?
2. Contrarian Takeaways: What are 3-5 contrarian or counterintuitive insights that challenge conventional thinking?
3. Unstated Assumptions: What assumptions does the author make that aren't explicitly stated?
4. Potential Experiments: What new experiments, tests, or research could be designed based on these ideas?
5. Industry Applications: Which industries or sectors could benefit most from these insights and how?

Blog Title: {title}
Blog Content:
{content[:6000]}

Respond in JSON format:
{{
    "central_takeaways": ["takeaway 1", "takeaway 2", "takeaway 3"],
    "contrarian_takeaways": ["contrarian 1", "contrarian 2", "contrarian 3"],
    "unstated_assumptions": ["assumption 1", "assumption 2", "assumption 3"],
    "potential_experiments": ["experiment 1", "experiment 2", "experiment 3"],
    "industry_applications": ["industry/application 1", "industry/application 2", "industry/application 3"]
}}"""

        response = mistral_client.chat.complete(
            model="open-mistral-7b",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=8192,
            response_format={"type": "json_object"}
        )
        
        response_text = response.choices[0].message.content
        
        try:
            result = json.loads(response_text)
            return result
        except json.JSONDecodeError:
            return {
                'central_takeaways': [],
                'contrarian_takeaways': [],
                'unstated_assumptions': [],
                'potential_experiments': [],
                'industry_applications': []
            }
    
    return process_with_retry()


def extract_deep_insights(content: str, title: str) -> Dict:
    """Extract deep insights using Claude, OpenAI, Gemini, OpenRouter, or Mistral based on flags"""
    if get_use_mistral() and mistral_client:
        return extract_deep_insights_mistral(content, title)
    elif get_use_openrouter() and openrouter_client:
        return extract_deep_insights_openrouter(content, title)
    elif get_use_gemini() and gemini_client:
        return extract_deep_insights_gemini(content, title)
    elif get_use_openai() and openai_client:
        return extract_deep_insights_openai(content, title)
    else:
        return extract_deep_insights_claude(content, title)



def categorize_and_summarize_post_claude(content: str, url: str, title: str) -> Dict:
    """Categorize and summarize using Claude API"""
    @retry(
        stop=stop_after_attempt(7),
        wait=wait_exponential(multiplier=1, min=2, max=128),
        retry=retry_if_exception(is_rate_limit_error),
        reraise=True
    )
    def process_with_retry():
        prompt = f"""Analyze this blog post and provide:
1. A primary category (choose ONE most relevant: Technology, Business, Marketing, Design, Development, Product, Data Science, AI/ML, DevOps, Security, Other)
2. A concise summary (2-3 sentences)
3. Main points (3-5 key takeaways as bullet points)
4. Specific examples mentioned in the post (if any, 2-3 examples)

Blog Title: {title}
Blog Content:
{content[:4000]}

Respond in JSON format:
{{
    "category": "category name",
    "summary": "summary text",
    "main_points": ["point 1", "point 2", "point 3"],
    "examples": ["example 1", "example 2"]
}}"""

        message = claude_client.messages.create(
            model="claude-sonnet-4-5",
            max_tokens=8192,
            messages=[{"role": "user", "content": prompt}]
        )
        
        response_text = message.content[0].text if message.content[0].type == "text" else ""
        
        try:
            json_start = response_text.find('{')
            json_end = response_text.rfind('}') + 1
            if json_start != -1 and json_end > json_start:
                response_text = response_text[json_start:json_end]
            
            result = json.loads(response_text)
            result['url'] = url
            result['title'] = title
            return result
        except json.JSONDecodeError:
            return {
                'category': 'Other',
                'summary': 'Summary unavailable',
                'main_points': [],
                'examples': [],
                'url': url,
                'title': title
            }
    
    return process_with_retry()


def categorize_and_summarize_post_openai(content: str, url: str, title: str) -> Dict:
    """Categorize and summarize using OpenAI API"""
    @retry(
        stop=stop_after_attempt(7),
        wait=wait_exponential(multiplier=1, min=2, max=128),
        retry=retry_if_exception(is_rate_limit_error),
        reraise=True
    )
    def process_with_retry():
        prompt = f"""Analyze this blog post and provide:
1. A primary category (choose ONE most relevant: Technology, Business, Marketing, Design, Development, Product, Data Science, AI/ML, DevOps, Security, Other)
2. A concise summary (2-3 sentences)
3. Main points (3-5 key takeaways as bullet points)
4. Specific examples mentioned in the post (if any, 2-3 examples)

Blog Title: {title}
Blog Content:
{content[:4000]}

Respond in JSON format:
{{
    "category": "category name",
    "summary": "summary text",
    "main_points": ["point 1", "point 2", "point 3"],
    "examples": ["example 1", "example 2"]
}}"""

        response = openai_client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=8192,
            response_format={"type": "json_object"}
        )
        
        response_text = response.choices[0].message.content
        
        try:
            result = json.loads(response_text)
            result['url'] = url
            result['title'] = title
            return result
        except json.JSONDecodeError:
            return {
                'category': 'Other',
                'summary': 'Summary unavailable',
                'main_points': [],
                'examples': [],
                'url': url,
                'title': title
            }
    
    return process_with_retry()


def categorize_and_summarize_post_openrouter(content: str, url: str, title: str) -> Dict:
    """Categorize and summarize using OpenRouter (Qwen3) API"""
    @retry(
        stop=stop_after_attempt(7),
        wait=wait_exponential(multiplier=1, min=2, max=128),
        retry=retry_if_exception(is_rate_limit_error),
        reraise=True
    )
    def process_with_retry():
        prompt = f"""Analyze this blog post and provide:
1. A primary category (choose ONE most relevant: Technology, Business, Marketing, Design, Development, Product, Data Science, AI/ML, DevOps, Security, Other)
2. A concise summary (2-3 sentences)
3. Main points (3-5 key takeaways as bullet points)
4. Specific examples mentioned in the post (if any, 2-3 examples)

Blog Title: {title}
Blog Content:
{content[:4000]}

Respond in JSON format:
{{
    "category": "category name",
    "summary": "summary text",
    "main_points": ["point 1", "point 2", "point 3"],
    "examples": ["example 1", "example 2"]
}}"""

        response = openrouter_client.chat.completions.create(
            model="qwen/qwen-2.5-72b-instruct",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=8192,
            response_format={"type": "json_object"}
        )
        
        response_text = response.choices[0].message.content
        
        try:
            result = json.loads(response_text)
            result['url'] = url
            result['title'] = title
            return result
        except json.JSONDecodeError:
            return {
                'category': 'Other',
                'summary': 'Summary unavailable',
                'main_points': [],
                'examples': [],
                'url': url,
                'title': title
            }
    
    return process_with_retry()


def categorize_and_summarize_post_gemini(content: str, url: str, title: str) -> Dict:
    """Categorize and summarize using Gemini API"""
    @retry(
        stop=stop_after_attempt(7),
        wait=wait_exponential(multiplier=1, min=2, max=128),
        retry=retry_if_exception(is_rate_limit_error),
        reraise=True
    )
    def process_with_retry():
        prompt = f"""Analyze this blog post and provide:
1. A primary category (choose ONE most relevant: Technology, Business, Marketing, Design, Development, Product, Data Science, AI/ML, DevOps, Security, Other)
2. A concise summary (2-3 sentences)
3. Main points (3-5 key takeaways as bullet points)
4. Specific examples mentioned in the post (if any, 2-3 examples)

Blog Title: {title}
Blog Content:
{content[:4000]}

Respond in JSON format:
{{
    "category": "category name",
    "summary": "summary text",
    "main_points": ["point 1", "point 2", "point 3"],
    "examples": ["example 1", "example 2"]
}}"""

        response = gemini_client.generate_content(
            prompt,
            generation_config=genai.types.GenerationConfig(
                temperature=0.7,
                max_output_tokens=8192,
            )
        )
        
        response_text = response.text
        
        try:
            json_start = response_text.find('{')
            json_end = response_text.rfind('}') + 1
            if json_start != -1 and json_end > json_start:
                response_text = response_text[json_start:json_end]
            
            result = json.loads(response_text)
            result['url'] = url
            result['title'] = title
            return result
        except json.JSONDecodeError:
            return {
                'category': 'Other',
                'summary': 'Summary unavailable',
                'main_points': [],
                'examples': [],
                'url': url,
                'title': title
            }
    
    return process_with_retry()


def categorize_and_summarize_post_mistral(content: str, url: str, title: str) -> Dict:
    """Categorize and summarize using Mistral API"""
    @retry(
        stop=stop_after_attempt(7),
        wait=wait_exponential(multiplier=1, min=2, max=128),
        retry=retry_if_exception(is_rate_limit_error),
        reraise=True
    )
    def process_with_retry():
        prompt = f"""Analyze this blog post and provide:
1. A primary category (choose ONE most relevant: Technology, Business, Marketing, Design, Development, Product, Data Science, AI/ML, DevOps, Security, Other)
2. A concise summary (2-3 sentences)
3. Main points (3-5 key takeaways as bullet points)
4. Specific examples mentioned in the post (if any, 2-3 examples)

Blog Title: {title}
Blog Content:
{content[:4000]}

Respond in JSON format:
{{
    "category": "category name",
    "summary": "summary text",
    "main_points": ["point 1", "point 2", "point 3"],
    "examples": ["example 1", "example 2"]
}}"""

        response = mistral_client.chat.complete(
            model="open-mistral-7b",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=8192,
            response_format={"type": "json_object"}
        )
        
        response_text = response.choices[0].message.content
        
        try:
            result = json.loads(response_text)
            result['url'] = url
            result['title'] = title
            return result
        except json.JSONDecodeError:
            return {
                'category': 'Other',
                'summary': 'Summary unavailable',
                'main_points': [],
                'examples': [],
                'url': url,
                'title': title
            }
    
    return process_with_retry()


def categorize_and_summarize_post(content: str, url: str, title: str) -> Dict:
    """Categorize and summarize using Claude, OpenAI, Gemini, OpenRouter, or Mistral based on flags"""
    if get_use_mistral() and mistral_client:
        return categorize_and_summarize_post_mistral(content, url, title)
    elif get_use_openrouter() and openrouter_client:
        return categorize_and_summarize_post_openrouter(content, url, title)
    elif get_use_gemini() and gemini_client:
        return categorize_and_summarize_post_gemini(content, url, title)
    elif get_use_openai() and openai_client:
        return categorize_and_summarize_post_openai(content, url, title)
    else:
        return categorize_and_summarize_post_claude(content, url, title)



def generate_cluster_labels(clusters: Dict[int, List[Dict]]) -> Dict[int, Dict]:
    """
    Generate meaningful labels and summaries for each cluster using Claude.
    
    Args:
        clusters: Dictionary mapping cluster_id to list of posts
    
    Returns:
        Dictionary mapping cluster_id to cluster metadata (label, summary, etc.)
    """
    cluster_metadata = {}
    
    for cluster_id, posts in clusters.items():
        titles = [post.get('title', 'Untitled') for post in posts[:10]]
        
        summaries = [post.get('summary', '') for post in posts[:10] if post.get('summary')]
        
        prompt = f"""Analyze this group of {len(posts)} blog posts and generate:
1. A concise, descriptive topic label (2-5 words)
2. A brief summary of what this topic cluster is about (1-2 sentences)
3. Key themes present across these posts

Blog post titles in this cluster:
{chr(10).join(f"- {title}" for title in titles)}

{"Post summaries:" + chr(10).join(f"- {s[:200]}" for s in summaries[:5]) if summaries else ""}

Respond in JSON format:
{{
    "label": "topic label",
    "summary": "cluster summary",
    "themes": ["theme 1", "theme 2", "theme 3"]
}}"""

        try:
            message = client.messages.create(
                model="claude-sonnet-4-5",
                max_tokens=2048,
                messages=[{"role": "user", "content": prompt}]
            )
            
            response_text = message.content[0].text if message.content[0].type == "text" else ""
            
            json_start = response_text.find('{')
            json_end = response_text.rfind('}') + 1
            if json_start != -1 and json_end > json_start:
                response_text = response_text[json_start:json_end]
            
            metadata = json.loads(response_text)
            metadata['post_count'] = len(posts)
            cluster_metadata[cluster_id] = metadata
            
        except Exception as e:
            cluster_metadata[cluster_id] = {
                'label': f'Topic {cluster_id + 1}',
                'summary': f'A cluster of {len(posts)} related posts',
                'themes': [],
                'post_count': len(posts)
            }
    
    return cluster_metadata


def process_posts_batch(posts: List[Dict[str, str]], progress_callback=None) -> List[Dict]:
    results = []
    
    def process_single_post(i: int, post: Dict[str, str]) -> tuple[int, Dict]:
        title = post.get('title', 'Untitled')
        content = post['content']
        url = post['url']
        
        summary_result = categorize_and_summarize_post(content, url, title)
        
        insights_result = extract_deep_insights(content, title)
        
        combined_result = {**summary_result, **insights_result}
        
        return (i, combined_result)
    
    with ThreadPoolExecutor(max_workers=2) as executor:
        futures = {executor.submit(process_single_post, i, post): i for i, post in enumerate(posts)}
        indexed_results = [None] * len(posts)
        completed_count = 0
        
        for future in as_completed(futures):
            try:
                idx, result = future.result()
                indexed_results[idx] = result
                completed_count += 1
                
                if progress_callback:
                    progress_callback(completed_count, len(posts))
            except Exception as e:
                import traceback
                error_details = traceback.format_exc()
                print(f"Error processing post: {str(e)}")
                print(f"Full traceback: {error_details}")
                completed_count += 1
                
                if progress_callback:
                    progress_callback(completed_count, len(posts))
        
        results = [r for r in indexed_results if r is not None]
    
    return results
