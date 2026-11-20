"""Run the bot on your own computer:  python -m bot

On a server (Render) you do NOT run this. The dashboard web service runs the
bot through a webhook instead (see README, "Deploy to Render").
"""

import asyncio
import logging
import sys

from .config import settings
from .db import init_db
from .runtime import create_bot


async def main() -> None:
    if not settings.bot_token:
        sys.exit("BOT_TOKEN is missing. Copy .env.example to .env and paste the token from @BotFather.")
    if not settings.anon_salt or settings.anon_salt == "change-me":
        sys.exit("ANON_SALT is missing. Set a long random value in .env (see .env.example).")

    await init_db()
    bot, dp = create_bot()
    info = await bot.get_webhook_info()
    if info.url and "--force" not in sys.argv:
        await bot.session.close()
        sys.exit(
            f"This bot is currently running on a server (webhook: {info.url}).\n"
            "Running it here too would take it away from the server.\n"
            "If you really want to run it locally, use:  python -m bot --force"
        )
    await bot.delete_webhook()
    me = await bot.get_me()
    logging.info("Bot @%s started (polling)", me.username)
    await dp.start_polling(bot)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    asyncio.run(main())
