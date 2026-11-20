"""Builds the bot and runs it either by polling (laptop) or by webhook (server).

* Laptop:  python -m bot            -> long polling
* Server:  the dashboard web app receives Telegram updates on
           /telegram/webhook, so ONE web service runs both the website and the
           bot (this is how it runs on Render).
"""

import hashlib
import os

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage

from .config import settings
from .handlers import router

WEBHOOK_PATH = "/telegram/webhook"


def create_bot() -> tuple[Bot, Dispatcher]:
    bot = Bot(settings.bot_token, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dp = Dispatcher(storage=MemoryStorage())
    dp.include_router(router)
    return bot, dp


def public_url() -> str | None:
    """The server's public https address. Render sets RENDER_EXTERNAL_URL itself."""
    url = os.getenv("PUBLIC_URL") or os.getenv("RENDER_EXTERNAL_URL")
    return url.rstrip("/") if url else None


def webhook_secret() -> str:
    # Telegram sends this back in a header, so nobody else can post fake updates.
    return hashlib.sha256(f"webhook:{settings.bot_token}".encode()).hexdigest()[:48]
