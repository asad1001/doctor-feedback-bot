# Container for the Telegram bot (used by Fly.io; works with any Docker host).
FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY bot ./bot
COPY photos/bmtm ./photos/bmtm
COPY photos/samadov.jpg ./photos/
CMD ["python", "-m", "bot", "--force"]
