# /bot/parsers/feed.py

import aiohttp
import feedparser
from bs4 import BeautifulSoup
from utils import sanitize_text

HEADERS = {"User-Agent": "Mozilla/5.0 FeedForwarderBot/1.0"}

async def fetch_url(session, url: str) -> str:
    async with session.get(url, headers=HEADERS, timeout=10) as response:
        return await response.text()

async def parse_rss(url: str) -> list[dict]:
    async with aiohttp.ClientSession() as session:
        content = await fetch_url(session, url)
        feed = feedparser.parse(content)
        return [
            {
                "title": sanitize_text(entry.title),
                "link": entry.link,
                "summary": sanitize_text(entry.get("summary", "")),
            }
            for entry in feed.entries[:5]
        ]

async def parse_html(url: str) -> dict:
    async with aiohttp.ClientSession() as session:
        html = await fetch_url(session, url)
        soup = BeautifulSoup(html, "html.parser")
        title = soup.title.string.strip() if soup.title else "No Title"
        summary = ""
        for tag in soup.find_all("p"):
            text = tag.get_text(strip=True)
            if len(text) > 60:
                summary = text
                break
        image = ""
        og_img = soup.find("meta", property="og:image")
        if og_img and og_img.get("content"):
            image = og_img["content"]

        return {
            "title": sanitize_text(title),
            "summary": sanitize_text(summary),
            "image": image,
            "link": url,
        }

async def fetch_articles(url: str) -> list[dict]:
    if url.endswith(".rss") or "rss" in url.lower():
        return await parse_rss(url)
    else:
        return [await parse_html(url)]
import aiohttp
import feedparser
from bs4 import BeautifulSoup
from utils import log_info

async def fetch_articles(url: str) -> list[dict]:
    """
    Fetch articles from RSS feeds or HTML pages.
    Returns list of articles with title, summary, and link.
    """
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                content = await response.text()
                
        # Try RSS/Atom feed first
        feed = feedparser.parse(content)
        if feed.entries:
            articles = []
            for entry in feed.entries[:10]:  # Limit to 10 recent articles
                articles.append({
                    'title': entry.get('title', 'No Title'),
                    'summary': entry.get('summary', entry.get('description', 'No Summary')),
                    'link': entry.get('link', url)
                })
            return articles
        
        # If not RSS, try HTML parsing
        soup = BeautifulSoup(content, 'html.parser')
        articles = []
        
        # Simple heuristic for finding articles
        for article in soup.find_all(['article', 'div'], class_=lambda x: x and any(
            word in x.lower() for word in ['post', 'article', 'entry', 'news']
        ))[:10]:
            title_elem = article.find(['h1', 'h2', 'h3', 'h4'])
            link_elem = article.find('a')
            
            title = title_elem.get_text(strip=True) if title_elem else 'No Title'
            link = link_elem.get('href') if link_elem else url
            summary = article.get_text(strip=True)[:200] + '...' if len(article.get_text(strip=True)) > 200 else article.get_text(strip=True)
            
            if title and title != 'No Title':
                articles.append({
                    'title': title,
                    'summary': summary,
                    'link': link if link.startswith('http') else f"{url.rstrip('/')}/{link.lstrip('/')}"
                })
        
        return articles
        
    except Exception as e:
        log_info(f"Error fetching articles from {url}: {e}")
        return []
