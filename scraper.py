import trafilatura
import requests
from bs4 import BeautifulSoup
from typing import List, Dict, Optional
from urllib.parse import urljoin, urlparse
import re


def get_website_text_content(url: str) -> str:
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        downloaded = response.text
    except Exception:
        downloaded = trafilatura.fetch_url(url)
    
    text = trafilatura.extract(
        downloaded,
        include_comments=False,
        include_tables=True,
        no_fallback=False
    )
    
    if text and len(text) > 200:
        return text
    
    try:
        if not isinstance(downloaded, str):
            response = requests.get(url, headers=headers, timeout=30)
            response.raise_for_status()
            downloaded = response.text
        
        soup = BeautifulSoup(downloaded, 'html.parser')
        
        for tag in soup(['script', 'style', 'nav', 'header', 'footer', 'aside']):
            tag.decompose()
        
        article_selectors = [
            'article',
            '[role="main"]',
            '.post-content',
            '.entry-content',
            '.article-content',
            '.blog-post',
            'main'
        ]
        
        content_element = None
        for selector in article_selectors:
            content_element = soup.select_one(selector)
            if content_element:
                break
        
        if not content_element:
            content_element = soup.find('body')
        
        if content_element:
            text = content_element.get_text(separator='\n', strip=True)
            text = re.sub(r'\n{3,}', '\n\n', text)
            
            if len(text) > 200:
                return text
    
    except Exception:
        pass
    
    return text if text else ""


def score_link(link: Dict[str, str], listing_url: str) -> int:
    score = 0
    url = link['url'].lower()
    title = link['title'].lower()
    
    blog_path_keywords = ['blog', 'post', 'article', 'news', 'story', 'tutorial', 'guide', 'insight', 'resources']
    for keyword in blog_path_keywords:
        if keyword in url:
            score += 10
    
    date_pattern = r'/(20\d{2})/|(20\d{2})[-/](\d{2})[-/](\d{2})'
    if re.search(date_pattern, url):
        score += 15
    
    exclusion_patterns = [
        'about', 'contact', 'privacy', 'terms', 'category', 'tag', 'author',
        'search', 'page', 'login', 'signup', 'profile', 'settings', 'admin',
        'wp-content', 'wp-admin', 'feed', 'rss', 'sitemap'
    ]
    for pattern in exclusion_patterns:
        if pattern in url:
            score -= 20
    
    if len(title) > 15 and len(title) < 150:
        score += 5
    
    parsed_listing = urlparse(listing_url)
    parsed_link = urlparse(link['url'])
    depth = len([p for p in parsed_link.path.split('/') if p])
    if 2 <= depth <= 5:
        score += 3
    
    return score


def extract_blog_links(listing_url: str) -> List[Dict[str, str]]:
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        response = requests.get(listing_url, timeout=30, headers=headers)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')
        
        links = []
        seen_urls = set()
        
        article_containers = soup.find_all(['article', 'div', 'section'], class_=re.compile(r'(post|article|blog|entry|card|item)', re.I))
        
        if article_containers:
            for container in article_containers:
                link_tag = container.find('a', href=True)
                if link_tag:
                    href = link_tag['href']
                    full_url = urljoin(listing_url, href)
                    
                    if full_url not in seen_urls:
                        title = link_tag.get_text(strip=True)
                        
                        heading = container.find(['h1', 'h2', 'h3', 'h4'])
                        if heading and not title:
                            title = heading.get_text(strip=True)
                        
                        if not title or len(title) < 5:
                            title_tag = container.find(class_=re.compile(r'(title|heading)', re.I))
                            if title_tag:
                                title = title_tag.get_text(strip=True)
                        
                        if title and len(title) >= 5:
                            links.append({
                                'url': full_url,
                                'title': title
                            })
                            seen_urls.add(full_url)
        
        for link in soup.find_all('a', href=True):
            href = link['href']
            full_url = urljoin(listing_url, href)
            
            parsed_listing = urlparse(listing_url)
            parsed_link = urlparse(full_url)
            
            if parsed_link.netloc != parsed_listing.netloc:
                continue
            
            if full_url in seen_urls:
                continue
            
            if full_url == listing_url or full_url == listing_url + '/':
                continue
            
            if any(ext in full_url.lower() for ext in ['.jpg', '.png', '.gif', '.pdf', '.zip', '.css', '.js', '.xml', '.json', '.svg', '.woff']):
                continue
            
            if any(pattern in full_url.lower() for pattern in ['#', 'mailto:', 'tel:', 'javascript:']):
                continue
            
            title = link.get_text(strip=True)
            if title and len(title) > 5 and len(title) < 200:
                links.append({
                    'url': full_url,
                    'title': title
                })
                seen_urls.add(full_url)
        
        scored_links = [(link, score_link(link, listing_url)) for link in links]
        scored_links.sort(key=lambda x: x[1], reverse=True)
        
        filtered_links = [link for link, score in scored_links if score > 0]
        
        if len(filtered_links) < 5 and len(links) > 0:
            filtered_links = [link for link, score in scored_links[:50]]
        
        return filtered_links if filtered_links else links
    
    except Exception as e:
        raise Exception(f"Error extracting links: {str(e)}")


def scrape_blog_post(url: str) -> Dict[str, str]:
    try:
        content = get_website_text_content(url)
        if not content:
            raise Exception("No content extracted")
        
        return {
            'url': url,
            'content': content
        }
    except Exception as e:
        raise Exception(f"Error scraping {url}: {str(e)}")
