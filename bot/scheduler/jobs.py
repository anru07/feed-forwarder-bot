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
from aiosqlite import connect

FETCH_INTERVAL_MIN = 5

# ✅ Make scheduler global so it can be shutdown gracefully
scheduler = AsyncIOScheduler()

def schedule_fetching(application):
    async def job():
        log_info("⏰ Auto-fetch job triggered")
        await fetch_and_forward(application.bot)

    scheduler.add_job(job, trigger='interval', minutes=FETCH_INTERVAL_MIN)
    scheduler.start()
    log_info("✅ Scheduled article fetching every 5 minutes")

# ✅ Async fetching logic
async def fetch_and_forward(bot: Bot):
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

                # ✅ Filter logic
                if filters:
                    text_lower = f"{article['title']} {article['summary']}".lower()
                    if not any(k.lower() in text_lower for k in filters):
                        continue

                # ✅ Skip duplicates
                if await is_article_sent(source_url, article["link"]):
                    continue

                # ✅ Forward to all targets
                for chat_id in targets:
                    try:
                        # Escape Markdown characters
                        safe_title = article['title'].replace('*', '\\*').replace('_', '\\_').replace('[', '\\[').replace(']', '\\]')
                        safe_summary = article['summary'].replace('*', '\\*').replace('_', '\\_').replace('[', '\\[').replace(']', '\\]')
                        text = f"*{safe_title}*\n{safe_summary}\n🔗 {article['link']}"

                        await bot.send_message(chat_id=chat_id, text=text, parse_mode="Markdown")
                        log_info(f"✅ Sent to {chat_id}: {article['title']}")
                    except Exception as e:
                        log_info(f"❌ Failed to send to {chat_id}: {e}")

                # ✅ Mark as sent
                await mark_article_sent(source_url, article["link"])
