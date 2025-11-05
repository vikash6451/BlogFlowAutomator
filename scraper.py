import trafilatura
import requests
from bs4 import BeautifulSoup
from typing import List, Dict
from urllib.parse import urljoin, urlparse


def get_website_text_content(url: str) -> str:
    downloaded = trafilatura.fetch_url(url)
    text = trafilatura.extract(downloaded)
    return text if text else ""


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
            
            if any(ext in full_url.lower() for ext in ['.jpg', '.png', '.gif', '.pdf', '.zip', '.css', '.js', '.xml', '.json']):
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
        
        blog_keywords = ['blog', 'post', 'article', 'news', 'story', 'tutorial', 'guide']
        priority_links = [l for l in links if any(keyword in l['url'].lower() for keyword in blog_keywords)]
        
        if priority_links:
            return priority_links
        
        return links
    
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
