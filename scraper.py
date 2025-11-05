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
        response = requests.get(listing_url, timeout=30)
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
            
            if any(ext in full_url.lower() for ext in ['.jpg', '.png', '.gif', '.pdf', '.zip', '.css', '.js']):
                continue
            
            title = link.get_text(strip=True)
            if title and len(title) > 3:
                links.append({
                    'url': full_url,
                    'title': title
                })
                seen_urls.add(full_url)
        
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
