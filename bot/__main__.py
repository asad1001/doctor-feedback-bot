"""Run the bot:  python -m bot"""

import asyncio
import logging
import sys

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage

from .config import settings
from .db import init_db
from .handlers import router


async def main() -> None:
    if not settings.bot_token:
        sys.exit("BOT_TOKEN is missing. Copy .env.example to .env and paste the token from @BotFather.")
    if not settings.anon_salt or settings.anon_salt == "change-me":
        sys.exit("ANON_SALT is missing. Set a long random value in .env (see .env.example).")

    await init_db()
    bot = Bot(settings.bot_token, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dp = Dispatcher(storage=MemoryStorage())
    dp.include_router(router)
    me = await bot.get_me()
    logging.info("Bot @%s started", me.username)
    await dp.start_polling(bot)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    asyncio.run(main())
