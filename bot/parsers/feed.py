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
