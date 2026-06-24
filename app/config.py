"""Application configuration using pydantic-settings."""
from __future__ import annotations

from typing import List

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # ── Telegram ──────────────────────────────────────────────────────────────
    BOT_TOKEN: str
    GROUP_CHAT_ID: int = 0  # Required for scheduler; optional locally

    # ── GitHub ────────────────────────────────────────────────────────────────
    GITHUB_TOKEN: str = ""  # Optional — raises rate limit from 60 to 5000 req/hr
    GITHUB_REPO: str = "fossasia/eventyay-talk"

    # ── Database ──────────────────────────────────────────────────────────────
    DATABASE_URL: str = "sqlite+aiosqlite:///./lgtm.db"

    # ── Admin ─────────────────────────────────────────────────────────────────
    ADMIN_USERNAMES: str = ""  # Comma-separated usernames (without @)

    # ── Scheduler ─────────────────────────────────────────────────────────────
    # Daily digest time in UTC (14:30 UTC = 8:00 PM IST)
    DIGEST_HOUR: int = 14
    DIGEST_MINUTE: int = 30

    # ── Webhook (optional — polling used when not set) ────────────────────────
    WEBHOOK_URL: str = ""
    WEBHOOK_PORT: int = 8443
    WEBHOOK_PATH: str = "/webhook"

    @property
    def admin_list(self) -> List[str]:
        """Parsed admin usernames (lowercase, without @)."""
        if not self.ADMIN_USERNAMES:
            return []
        return [
            u.strip().lstrip("@").lower()
            for u in self.ADMIN_USERNAMES.split(",")
            if u.strip()
        ]

    @property
    def webhook_mode(self) -> bool:
        """True when WEBHOOK_URL is configured."""
        return bool(self.WEBHOOK_URL)


settings = Settings()
