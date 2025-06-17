# /bot/scheduler/jobs.py

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from telegram import Bot
from bot.parsers.feed import fetch_articles
from bot.database.queries import (
    get_sources,
    get_filters_by_source,
    get_targets_by_source,
    is_article_sent,
    mark_article_sent,
    get_or_create_user,
)
from utils import log_info

FETCH_INTERVAL_MIN = 30

def schedule_fetching(application):
    scheduler = AsyncIOScheduler()
    scheduler.add_job(lambda: fetch_and_forward(application.bot), 'interval', minutes=FETCH_INTERVAL_MIN)
    scheduler.start()
    log_info("Scheduled article fetching every 30 minutes")

async def fetch_and_forward(bot: Bot):
    # For now, fetch all users from sources table
    from aiosqlite import connect

    async with connect("feedforwarder.db") as db:
        cursor = await db.execute("SELECT DISTINCT user_id FROM sources")
        user_ids = [row[0] for row in await cursor.fetchall()]

    for user_id in user_ids:
        sources = await get_sources(user_id)
        for source_url in sources:
            articles = await fetch_articles(source_url)
            filters = await get_filters_by_source(source_url)
            targets = await get_targets_by_source(source_url)

            for article in articles:
                text = f"*{article['title']}*\n{article['summary']}\n🔗 {article['link']}"
                if filters:
                    text_lower = f"{article['title']} {article['summary']}".lower()
                    if not any(k.lower() in text_lower for k in filters):
                        continue
                if await is_article_sent(source_url, article["link"]):
                    continue
                for chat_id in targets:
                    try:
                        await bot.send_message(chat_id=chat_id, text=text, parse_mode="Markdown")
                        log_info(f"Forwarded article to {chat_id}: {article['title']}")
                    except Exception as e:
                        log_info(f"Failed to send to {chat_id}: {e}")
                await mark_article_sent(source_url, article["link"])
