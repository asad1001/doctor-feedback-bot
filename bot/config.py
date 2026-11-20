import os
from dataclasses import dataclass
from pathlib import Path
from zoneinfo import ZoneInfo

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")


@dataclass(frozen=True)
class Settings:
    bot_token: str
    bot_username: str
    anon_salt: str
    database_url: str
    tz: ZoneInfo
    alert_chat_id: int | None
    dashboard_users: dict[str, str]
    dashboard_secret: str


def _dashboard_users() -> dict[str, str]:
    # DASHBOARD_USERS=director:pass1,quality:pass2
    users = {}
    for pair in os.getenv("DASHBOARD_USERS", "").split(","):
        if ":" in pair:
            name, password = pair.split(":", 1)
            if name.strip() and password.strip():
                users[name.strip()] = password.strip()
    return users


def _alert_chat_id() -> int | None:
    value = os.getenv("ALERT_CHAT_ID", "").strip()
    return int(value) if value.lstrip("-").isdigit() else None


def _database_url() -> str:
    url = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///data/feedback.db")
    # Render/Heroku give postgres://...; SQLAlchemy async needs postgresql+asyncpg://
    for old in ("postgres://", "postgresql://"):
        if url.startswith(old):
            url = "postgresql+asyncpg://" + url[len(old):]
    # Make relative SQLite paths relative to the project folder, not the cwd.
    prefix = "sqlite+aiosqlite:///"
    if url.startswith(prefix) and not url[len(prefix):].startswith("/"):
        path = BASE_DIR / url[len(prefix):]
        path.parent.mkdir(parents=True, exist_ok=True)
        url = prefix + str(path)
    return url


settings = Settings(
    bot_token=os.getenv("BOT_TOKEN", ""),
    bot_username=os.getenv("BOT_USERNAME", "").lstrip("@"),
    anon_salt=os.getenv("ANON_SALT", ""),
    database_url=_database_url(),
    tz=ZoneInfo(os.getenv("TIMEZONE", "Asia/Tashkent")),
    alert_chat_id=_alert_chat_id(),
    dashboard_users=_dashboard_users(),
    dashboard_secret=os.getenv("DASHBOARD_SECRET", ""),
)
