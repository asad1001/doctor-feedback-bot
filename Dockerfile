# Container for the Telegram bot (used by Fly.io; works with any Docker host).
FROM python:3.12-slim
ENV PYTHONUNBUFFERED=1
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY bot ./bot
COPY photos/bmtm ./photos/bmtm
COPY photos/samadov.jpg ./photos/
# Pre-compile all Python files so the bot starts in seconds on a small machine.
RUN python -m compileall -q /usr/local/lib/python3.12 /app/bot
CMD ["python", "-m", "bot", "--force"]
