import asyncio
import logging
import os
import nest_asyncio

from aiohttp import web
from telegram import Update
from telegram.ext import Application

from bot.handlers.commands import register_handlers
from bot.scheduler.jobs import schedule_fetching
from bot.database.core import init_db
from utils import get_env_variable

# 🔧 Setup async compatibility
nest_asyncio.apply()

# 📡 Health check handler
async def handle_healthcheck(request):
    return web.Response(text="OK")

# 📨 Telegram webhook handler (uses the telegram Application)
def create_telegram_webhook_handler(app: Application):
    async def telegram_webhook_handler(request: web.Request):
        try:
            data = await request.json()
        except Exception as e:
            logging.error("Failed to parse JSON: %s", e)
            return web.Response(status=400, text="Invalid JSON")
        # Convert JSON to a Telegram Update object
        update = Update.de_json(data, app.bot)
        # Process the update through the Application
        await app.process_update(update)
        return web.Response(text="OK")
    return telegram_webhook_handler

# 🚀 Main entrypoint: setup Telegram Application and aiohttp server with webhook route
async def run():
    # Retrieve configuration from environment
    token = get_env_variable("TELEGRAM_TOKEN")
    webhook_url = get_env_variable("WEBHOOK_URL")  # e.g., "https://your-render-app-name.onrender.com"
    webhook_path = "/webhook"
    full_webhook_url = webhook_url + webhook_path

    # Process ADMIN_USER_IDS if provided
    admin_ids = get_env_variable("ADMIN_USER_IDS", "").split(",")
    admin_ids = [int(uid.strip()) for uid in admin_ids if uid.strip().isdigit()]

    # Build the Telegram Application
    application = Application.builder().token(token).build()

    # Initialize your database, register handlers, and schedule any jobs
    await init_db()
    register_handlers(application, admin_ids)
    schedule_fetching(application)

    # Initialize and start the Telegram Application (without polling)
    logging.info("Initializing Telegram application...")
    await application.initialize()
    await application.start()

    # Set the webhook so that Telegram sends updates to your endpoint
    await application.bot.set_webhook(full_webhook_url)
    logging.info("Webhook set to: %s", full_webhook_url)

    # Create an aiohttp application and add routes for both health check and Telegram webhook
    app = web.Application()
    app.add_routes([
        web.get("/healthz", handle_healthcheck),
        web.post(webhook_path, create_telegram_webhook_handler(application)),
    ])

    # Setup the aiohttp runner on port 10000 (adjust if needed)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, host="0.0.0.0", port=10000)
    await site.start()
    logging.info("Web server running on http://0.0.0.0:10000")

    # Keep the service running indefinitely
    try:
        while True:
            await asyncio.sleep(3600)
    except KeyboardInterrupt:
        logging.info("Shutting down...")
    finally:
        # Clean shutdown of both the Telegram Application and the web runner
        await application.stop()
        await application.shutdown()
        await runner.cleanup()

# 🧠 Entrypoint
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(run())
