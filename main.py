import asyncio
import logging
import os
import nest_asyncio
from aiohttp import web
from telegram.ext import Application

from bot.handlers.commands import register_handlers
from bot.scheduler.jobs import schedule_fetching
from bot.database.core import init_db
from utils import get_env_variable

# 🔧 Setup async compatibility for environments like Replit
nest_asyncio.apply()

# 📡 Health check route (optional)
async def handle_healthcheck(request):
    return web.Response(text="OK")

# 🌐 Start the aiohttp web server (for /healthz or UptimeRobot)
async def start_web():
    app = web.Application()
    app.add_routes([web.get("/healthz", handle_healthcheck)])
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, host="0.0.0.0", port=10000)
    await site.start()
    logging.info("Web server running on 0.0.0.0:10000/healthz")


# 🤖 Start the bot + scheduler
async def start_bot():
    token = get_env_variable("TELEGRAM_TOKEN")
    admin_ids = get_env_variable("ADMIN_USER_IDS", "").split(",")
    admin_ids = [int(uid.strip()) for uid in admin_ids if uid.strip().isdigit()]

    application = Application.builder().token(token).build()

    await init_db()
    register_handlers(application, admin_ids)
    schedule_fetching(application)

    logging.info("Bot is polling...")
    await application.initialize()
    await application.start()
    await application.updater.start_polling()
    
    # Keep the application running
    try:
        while True:
            await asyncio.sleep(1)
    except KeyboardInterrupt:
        logging.info("Shutting down bot...")
    finally:
        await application.updater.stop()
        await application.stop()
        await application.shutdown()

# 🚀 Launch both bot and health server
async def start_bot_and_server():
    await asyncio.gather(start_bot(), start_web())

# 🧠 Entrypoint
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(start_bot_and_server())
