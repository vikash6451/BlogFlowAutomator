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


def detect_pagination_links(soup: BeautifulSoup, base_url: str) -> List[str]:
    """Detect pagination links from the current page"""
    pagination_urls = []
    seen = set()
    
    # Common pagination patterns
    pagination_selectors = [
        'a.page-numbers',
        'a.pagination',
        '.pagination a',
        '.pager a',
        'nav.pagination a',
        '[class*="pag"] a',
        'a[rel="next"]',
        'a[aria-label*="page"]'
    ]
    
    for selector in pagination_selectors:
        for link in soup.select(selector):
            href = link.get('href')
            if href:
                full_url = urljoin(base_url, href)
                
                # Check if URL contains page number patterns
                if re.search(r'/page/\d+/?$|[?&]page=\d+', full_url) and full_url not in seen:
                    pagination_urls.append(full_url)
                    seen.add(full_url)
    
    # Also look for numeric links that might be pagination
    for link in soup.find_all('a', href=True):
        href = link.get('href')
        text = link.get_text(strip=True)
        
        # If link text is just a number and href contains page pattern
        if text.isdigit() and href:
            full_url = urljoin(base_url, href)
            if re.search(r'/page/\d+/?$|[?&]page=\d+', full_url) and full_url not in seen:
                pagination_urls.append(full_url)
                seen.add(full_url)
    
    return sorted(pagination_urls)


def extract_blog_links(listing_url: str, follow_pagination: bool = True, max_pages: int = 10) -> List[Dict[str, str]]:
    """
    Extract blog links from a listing page, optionally following pagination.
    
    Args:
        listing_url: The URL of the blog listing page
        follow_pagination: Whether to automatically follow pagination links
        max_pages: Maximum number of pages to scrape (default 10)
    """
    all_links = []
    seen_urls = set()
    pages_to_scrape = [listing_url]
    pages_scraped = set()
    
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        
        while pages_to_scrape and len(pages_scraped) < max_pages:
            current_url = pages_to_scrape.pop(0)
            
            if current_url in pages_scraped:
                continue
                
            pages_scraped.add(current_url)
            
            response = requests.get(current_url, timeout=30, headers=headers)
            response.raise_for_status()
            soup = BeautifulSoup(response.content, 'html.parser')
            
            links = []
            page_seen_urls = set()
            
            # Extract blog post links from current page
            article_containers = soup.find_all(['article', 'div', 'section'], class_=re.compile(r'(post|article|blog|entry|card|item)', re.I))
            
            if article_containers:
                for container in article_containers:
                    link_tag = container.find('a', href=True)
                    if link_tag:
                        href = link_tag['href']
                        full_url = urljoin(current_url, href)
                        
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
                                page_seen_urls.add(full_url)
            
            for link in soup.find_all('a', href=True):
                href = link['href']
                full_url = urljoin(current_url, href)
                
                parsed_listing = urlparse(listing_url)
                parsed_link = urlparse(full_url)
                
                if parsed_link.netloc != parsed_listing.netloc:
                    continue
                
                if full_url in seen_urls:
                    continue
                
                if full_url == current_url or full_url == current_url + '/':
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
                    page_seen_urls.add(full_url)
            
            all_links.extend(links)
            
            # Detect and queue pagination links if enabled
            if follow_pagination and len(pages_scraped) < max_pages:
                pagination_links = detect_pagination_links(soup, current_url)
                for page_link in pagination_links:
                    if page_link not in pages_scraped and page_link not in pages_to_scrape:
                        pages_to_scrape.append(page_link)
        
        # Score and filter all collected links
        scored_links = [(link, score_link(link, listing_url)) for link in all_links]
        scored_links.sort(key=lambda x: x[1], reverse=True)
        
        filtered_links = [link for link, score in scored_links if score > 0]
        
        if len(filtered_links) < 5 and len(all_links) > 0:
            filtered_links = [link for link, score in scored_links[:50]]
        
        return filtered_links if filtered_links else all_links
    
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
