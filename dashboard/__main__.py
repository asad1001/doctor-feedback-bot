"""Run the dashboard:  python -m dashboard   (then open http://localhost:8000)"""

import os
import sys

import uvicorn

from bot.config import settings

if __name__ == "__main__":
    if not settings.dashboard_users:
        sys.exit("DASHBOARD_USERS is missing in .env, e.g. DASHBOARD_USERS=director:StrongPassword123")
    uvicorn.run("dashboard.app:app", host=os.getenv("DASHBOARD_HOST", "127.0.0.1"),
                port=int(os.getenv("DASHBOARD_PORT", "8000")))
