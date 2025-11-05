import os
from anthropic import Anthropic
from concurrent.futures import ThreadPoolExecutor, as_completed
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception
from typing import List, Dict
import json

AI_INTEGRATIONS_ANTHROPIC_API_KEY = os.environ.get("AI_INTEGRATIONS_ANTHROPIC_API_KEY")
AI_INTEGRATIONS_ANTHROPIC_BASE_URL = os.environ.get("AI_INTEGRATIONS_ANTHROPIC_BASE_URL")

client = Anthropic(
    api_key=AI_INTEGRATIONS_ANTHROPIC_API_KEY,
    base_url=AI_INTEGRATIONS_ANTHROPIC_BASE_URL
)


def is_rate_limit_error(exception: BaseException) -> bool:
    error_msg = str(exception)
    return (
        "429" in error_msg
        or "RATELIMIT_EXCEEDED" in error_msg
        or "quota" in error_msg.lower()
        or "rate limit" in error_msg.lower()
        or (hasattr(exception, "status_code") and exception.status_code == 429)
    )


def extract_deep_insights(content: str, title: str) -> Dict:
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

        message = client.messages.create(
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


def categorize_and_summarize_post(content: str, url: str, title: str) -> Dict:
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

        message = client.messages.create(
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
        
        for future in as_completed(futures):
            try:
                idx, result = future.result()
                indexed_results[idx] = result
            except Exception as e:
                import traceback
                error_details = traceback.format_exc()
                print(f"Error processing post: {str(e)}")
                print(f"Full traceback: {error_details}")
        
        results = [r for r in indexed_results if r is not None]
    
    return results
