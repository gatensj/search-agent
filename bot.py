"""
bot.py — Phase 2: interact with the agent from your iPhone via Telegram.

Setup (one time):
  1. In Telegram, message @BotFather -> /newbot -> copy the token into .env
  2. Run this bot, send it /start from your phone -> it replies with your chat id
  3. Put that chat id in .env as TELEGRAM_ALLOWED_CHAT_ID and restart

Security model: the bot ONLY accepts messages from your chat id. Anyone else
gets a polite refusal — this is what stops strangers from spending your API credits.
"""

import asyncio
import logging
import os

from dotenv import load_dotenv

load_dotenv()

from telegram import Update  # noqa: E402
from telegram.constants import ChatAction  # noqa: E402
from telegram.ext import (  # noqa: E402
    Application,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

from search_agent import run_search  # noqa: E402

logging.basicConfig(format="%(asctime)s %(levelname)s %(name)s: %(message)s", level=logging.INFO)
logging.getLogger("httpx").setLevel(logging.WARNING)
log = logging.getLogger("search-bot")

BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
ALLOWED_CHAT_ID = os.environ.get("TELEGRAM_ALLOWED_CHAT_ID", "")

TG_LIMIT = 4000  # Telegram hard limit is 4096 chars/message; leave headroom


def authorized(update: Update) -> bool:
    return ALLOWED_CHAT_ID != "" and str(update.effective_chat.id) == ALLOWED_CHAT_ID


async def send_chunked(update: Update, text: str) -> None:
    for i in range(0, len(text), TG_LIMIT):
        await update.effective_chat.send_message(text[i : i + TG_LIMIT])


async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = update.effective_chat.id
    if authorized(update):
        await update.effective_chat.send_message(
            "Ready. Send me a research task, e.g.\n"
            "“find cybersecurity grants for the Philadelphia region posted this month”"
        )
    else:
        # Bootstrap path: tell the owner their chat id so they can whitelist it.
        await update.effective_chat.send_message(
            f"Your chat id is: {chat_id}\n"
            "If you own this bot, set TELEGRAM_ALLOWED_CHAT_ID to that value in .env and restart."
        )


async def handle_task(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not authorized(update):
        await update.effective_chat.send_message("Sorry, this is a private bot.")
        return

    task = (update.message.text or "").strip()
    if not task:
        return

    # One task at a time keeps costs and confusion down.
    if context.application.bot_data.get("busy"):
        await update.effective_chat.send_message("Still working on the previous task — hang on.")
        return
    context.application.bot_data["busy"] = True

    log.info("Task: %s", task)
    await update.effective_chat.send_message(f"On it: “{task}”\nI'll message you when done.")

    async def keep_typing(stop: asyncio.Event) -> None:
        while not stop.is_set():
            try:
                await update.effective_chat.send_action(ChatAction.TYPING)
            except Exception:  # noqa: BLE001 - cosmetic only
                pass
            await asyncio.sleep(5)

    stop = asyncio.Event()
    typing_task = asyncio.create_task(keep_typing(stop))
    try:
        result = await run_search(task)
        footer = f"\n\n— turns: {result.num_turns}, cost: ${result.cost_usd or 0:.3f}"
        await send_chunked(update, result.text + footer)
        if result.is_error:
            await update.effective_chat.send_message("(The run ended with an error flag — result above may be partial.)")
    except Exception as exc:  # noqa: BLE001
        log.exception("Task failed")
        await update.effective_chat.send_message(f"Task failed: {exc}")
    finally:
        stop.set()
        typing_task.cancel()
        context.application.bot_data["busy"] = False


def main() -> None:
    if not BOT_TOKEN:
        raise SystemExit("Set TELEGRAM_BOT_TOKEN in .env (get one from @BotFather).")
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_task))
    log.info("Bot polling. Send /start from your phone.")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
