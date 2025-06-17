# /bot/parsers/feed.py

import aiohttp
import feedparser
from bs4 import BeautifulSoup
from utils import sanitize_text, log_info

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
                "summary": sanitize_text(entry.get("summary", entry.get("description", ""))),
            }
            for entry in feed.entries[:5]
        ]

async def parse_html(url: str) -> dict:
    async with aiohttp.ClientSession() as session:
        html = await fetch_url(session, url)
        soup = BeautifulSoup(html, "html.parser")
        title = soup.title.string.strip() if soup.title else "No Title"
        summary = ""

        # Try to get meta description first
        meta_desc = soup.find("meta", attrs={"name": "description"})
        if meta_desc and meta_desc.get("content"):
            summary = meta_desc["content"]
        else:
            # Fall back to first paragraph
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
    """
    Fetch articles from RSS feeds or HTML pages.
    Returns list of articles with title, summary, and link.
    """
    try:
        # Check if it's likely an RSS feed
        if url.endswith(('.rss', '.xml')) or 'rss' in url.lower() or 'feed' in url.lower():
            return await parse_rss(url)
        else:
            # For HTML pages, return as single article
            article = await parse_html(url)
            return [article] if article['title'] != 'No Title' else []

    except Exception as e:
        log_info(f"Error fetching articles from {url}: {e}")
        return []