FROM python:3.12-slim

# Don't buffer Python output
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /app

# Install dependencies first (better layer caching)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code
COPY . .

# Data directory for SQLite (override DATABASE_URL in env)
RUN mkdir -p /data

# Run migrations then start the bot
CMD ["sh", "-c", "alembic upgrade head && python -m app.main"]
