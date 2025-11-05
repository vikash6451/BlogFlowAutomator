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


def process_posts_batch(posts: List[Dict[str, str]], progress_callback=None) -> List[Dict]:
    results = []
    
    def process_single_post(i: int, post: Dict[str, str]) -> tuple[int, Dict]:
        result = categorize_and_summarize_post(
            post['content'], 
            post['url'], 
            post.get('title', 'Untitled')
        )
        if progress_callback:
            progress_callback(i + 1, len(posts))
        return (i, result)
    
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
