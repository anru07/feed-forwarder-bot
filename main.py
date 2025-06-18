import asyncio
import logging
import os
import nest_asyncio

from aiohttp import web
from telegram import Update
from telegram.ext import Application

from bot.handlers.commands import register_handlers
from bot.scheduler.jobs import schedule_fetching, scheduler  # Import scheduler too
from bot.database.core import init_db
from utils import get_env_variable

# 🔧 Support nested event loops (needed in some environments)
nest_asyncio.apply()

# 📡 Health check endpoint
async def handle_healthcheck(request):
    return web.Response(text="OK")

# 🔁 Telegram webhook handler
def create_telegram_webhook_handler(app: Application):
    async def telegram_webhook_handler(request: web.Request):
        try:
            data = await request.json()
        except Exception as e:
            logging.error("Failed to parse JSON: %s", e)
            return web.Response(status=400, text="Invalid JSON")
        update = Update.de_json(data, app.bot)
        await app.process_update(update)
        return web.Response(text="OK")
    return telegram_webhook_handler

# 🚀 Entrypoint
async def run():
    logging.basicConfig(level=logging.INFO)

    # Load environment variables
    token = get_env_variable("TELEGRAM_TOKEN")
    webhook_url = get_env_variable("WEBHOOK_URL")
    webhook_path = "/webhook"
    full_webhook_url = webhook_url + webhook_path

    admin_ids = [int(uid.strip()) for uid in get_env_variable("ADMIN_USER_IDS", "").split(",") if uid.strip().isdigit()]

    # Initialize Telegram bot
    application = Application.builder().token(token).build()

    # Init database and handlers
    await init_db()
    register_handlers(application, admin_ids)

    # 🗓️ Schedule auto-fetching
    schedule_fetching(application)
    logging.info("✅ Scheduler started")

    # Initialize Telegram app (webhook mode)
    logging.info("Initializing Telegram application...")
    await application.initialize()
    await application.start()

    # Set webhook URL
    await application.bot.set_webhook(full_webhook_url)
    logging.info("Webhook set to: %s", full_webhook_url)

    # Setup aiohttp server
    app = web.Application()
    app.add_routes([
        web.get("/healthz", handle_healthcheck),
        web.post(webhook_path, create_telegram_webhook_handler(application)),
    ])

    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, host="0.0.0.0", port=10000)
    await site.start()
    logging.info("Web server running on http://0.0.0.0:10000")

    # Keep the app running
    try:
        while True:
            await asyncio.sleep(3600)
    except KeyboardInterrupt:
        logging.info("Shutting down...")
    finally:
        scheduler.shutdown()  # 🧹 Stop scheduled jobs cleanly
        await application.stop()
        await application.shutdown()
        await runner.cleanup()

# 🧠 Start the async app
if __name__ == "__main__":
    asyncio.run(run())
