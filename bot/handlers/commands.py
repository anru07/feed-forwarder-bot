# /bot/handlers/commands.py

from telegram import Update
from telegram.ext import Application, ContextTypes, CommandHandler
from telegram.constants import ParseMode
from bot.database import queries as db
from functools import partial

HELP_TEXT = """
🤖 *Feed Forwarder Bot Commands:*

/start – Welcome message and instructions.
/help – Show this help message.
/getchatid – Get the current chat ID.

/addsource <url> [keywords] – Add a new RSS/HTML source with optional filters.
/removesource <url> – Remove a source.
/listsources – List all your sources.

/addtarget <source_url> <chat_id> – Route source to a group/channel.
/removetarget <source_url> <chat_id> – Remove routing.
/listtargets – List targets per source.

/addfilter <source_url> <keyword> – Add a keyword filter.
/removefilter <source_url> <keyword> – Remove a filter.
/listfilters – List all filters by source.

/status – Get status of your bot session.
/adminpanel – Admin stats (restricted).
"""

def register_handlers(app: Application, admin_ids: list[int]):
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_cmd))
    app.add_handler(CommandHandler("getchatid", get_chat_id))
    app.add_handler(CommandHandler("status", status))

    # Placeholder for core command logic (to be added in future files)
    app.add_handler(CommandHandler("addsource", add_source))
    app.add_handler(CommandHandler("removesource", remove_source))
    app.add_handler(CommandHandler("listsources", list_sources))

    app.add_handler(CommandHandler("addtarget", add_target))
    app.add_handler(CommandHandler("removetarget", remove_target))
    app.add_handler(CommandHandler("listtargets", list_targets))

    app.add_handler(CommandHandler("addfilter", add_filter))
    app.add_handler(CommandHandler("removefilter", remove_filter))
    app.add_handler(CommandHandler("listfilters", list_filters))

    app.add_handler(CommandHandler("adminpanel", partial(admin_panel, admin_ids=admin_ids)))

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 Welcome to Feed Forwarder Bot!\n\nSend /help to view available commands and usage instructions."
    )

async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(HELP_TEXT, parse_mode=ParseMode.MARKDOWN)

async def get_chat_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    await update.message.reply_text(f"📌 Current Chat ID: `{chat_id}`", parse_mode="Markdown")

async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    await update.message.reply_text(f"🧾 Your Telegram ID: `{user_id}`", parse_mode="Markdown")

async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE, admin_ids):
    user_id = update.effective_user.id
    if user_id not in admin_ids:
        await update.message.reply_text("🚫 You are not authorized to view admin stats.")
        return

    # Stub for now — real stats will come when DB and logic are built
    await update.message.reply_text("🛠️ Admin Panel:\n- Users: TODO\n- Sources: TODO\n- Channels: TODO")

async def add_source(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    args = context.args
    if not args:
        await update.message.reply_text("❌ Usage: /addsource <url>")
        return

    url = args[0]
    await db.get_or_create_user(user_id)
    success = await db.add_source(user_id, url)
    if success:
        await update.message.reply_text(f"✅ Source added:\n{url}")
    else:
        await update.message.reply_text("⚠️ Source already exists or error occurred.")

async def remove_source(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    args = context.args
    if not args:
        await update.message.reply_text("❌ Usage: /removesource <url>")
        return

    url = args[0]
    success = await db.remove_source(user_id, url)
    if success:
        await update.message.reply_text("🗑️ Source removed.")
    else:
        await update.message.reply_text("⚠️ Could not find or remove that source.")

async def list_sources(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    sources = await db.get_sources(user_id)
    if not sources:
        await update.message.reply_text("🔍 You have no sources added yet.")
        return
    formatted = "\n".join(f"• {url}" for url in sources)
    await update.message.reply_text(f"📚 *Your Sources:*\n{formatted}", parse_mode=ParseMode.MARKDOWN)

async def add_target(update: Update, context: ContextTypes.DEFAULT_TYPE):
    args = context.args
    if len(args) < 2:
        await update.message.reply_text("❌ Usage: /addtarget <source_url> <chat_id>")
        return

    source_url = args[0]
    try:
        chat_id = int(args[1])
    except ValueError:
        await update.message.reply_text("❌ Invalid chat ID. It must be a number.")
        return

    success = await db.add_target(source_url, chat_id)
    if success:
        await update.message.reply_text(f"📬 Target added for source:\n{source_url} → `{chat_id}`", parse_mode="Markdown")
    else:
        await update.message.reply_text("⚠️ Could not add target (invalid source or duplicate).")

async def remove_target(update: Update, context: ContextTypes.DEFAULT_TYPE):
    args = context.args
    if len(args) < 2:
        await update.message.reply_text("❌ Usage: /removetarget <source_url> <chat_id>")
        return

    source_url = args[0]
    try:
        chat_id = int(args[1])
    except ValueError:
        await update.message.reply_text("❌ Invalid chat ID.")
        return

    success = await db.remove_target(source_url, chat_id)
    if success:
        await update.message.reply_text(f"🗑️ Target removed: `{chat_id}` from {source_url}", parse_mode=ParseMode.MARKDOWN)
    else:
        await update.message.reply_text("⚠️ Target not found.")

async def list_targets(update: Update, context: ContextTypes.DEFAULT_TYPE):
    args = context.args
    if not args:
        await update.message.reply_text("❌ Usage: /listtargets <source_url>")
        return

    source_url = args[0]
    targets = await db.get_targets_by_source(source_url)
    if not targets:
        await update.message.reply_text("🔍 No targets set for that source.")
        return

    formatted = "\n".join(f"• `{chat_id}`" for chat_id in targets)
    await update.message.reply_text(f"🎯 *Targets for {source_url}:*\n{formatted}", parse_mode=ParseMode.MARKDOWN)

async def add_filter(update: Update, context: ContextTypes.DEFAULT_TYPE):
    args = context.args
    if len(args) < 2:
        await update.message.reply_text("❌ Usage: /addfilter <source_url> <keyword>")
        return

    source_url, keyword = args[0], " ".join(args[1:])
    success = await db.add_filter(source_url, keyword)
    if success:
        await update.message.reply_text(f"🔍 Filter added: `{keyword}` for\n{source_url}", parse_mode=ParseMode.MARKDOWN)
    else:
        await update.message.reply_text("⚠️ Could not add filter. Is the source valid?")

async def remove_filter(update: Update, context: ContextTypes.DEFAULT_TYPE):
    args = context.args
    if len(args) < 2:
        await update.message.reply_text("❌ Usage: /removefilter <source_url> <keyword>")
        return

    source_url = args[0]
    keyword = " ".join(args[1:])
    success = await db.remove_filter(source_url, keyword)
    if success:
        await update.message.reply_text(f"🧹 Filter removed: `{keyword}` from {source_url}", parse_mode=ParseMode.MARKDOWN)
    else:
        await update.message.reply_text("⚠️ Filter not found.")


async def list_filters(update: Update, context: ContextTypes.DEFAULT_TYPE):
    args = context.args
    if not args:
        await update.message.reply_text("❌ Usage: /listfilters <source_url>")
        return

    source_url = args[0]
    filters = await db.get_filters_by_source(source_url)
    if not filters:
        await update.message.reply_text("🔍 No filters for that source.")
        return

    formatted = "\n".join(f"• `{kw}`" for kw in filters)
    await update.message.reply_text(f"🔎 *Filters for {source_url}:*\n{formatted}", parse_mode=ParseMode.MARKDOWN)

async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE, admin_ids):
    user_id = update.effective_user.id
    if user_id not in admin_ids:
        await update.message.reply_text("🚫 You are not authorized to view admin stats.")
        return

    stats = await db.get_admin_stats()
    await update.message.reply_text(
        f"🛠️ *Admin Panel Stats:*\n"
        f"- 👥 Users: {stats['users']}\n"
        f"- 📚 Sources: {stats['sources']}\n"
        f"- 🎯 Targets: {stats['targets']}",
        parse_mode=ParseMode.MARKDOWN
    )
