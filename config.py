"""Configuration loader for Zaporizhzhia power outage Telegram bot."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from zoneinfo import ZoneInfo

KYIV_TZ = ZoneInfo("Europe/Kyiv")

DEFAULT_PRIMARY_URL = (
    "https://raw.githubusercontent.com/milkmann/gpv-zoe-zaporizhzhia/main/data/Zaporizhzhiaoblenergo.json"
)
DEFAULT_FALLBACK_URL = (
    "https://raw.githubusercontent.com/yaroslav2901/OE_OUTAGE_DATA/main/data/Zaporizhzhiaoblenergo.json"
)
ZOE_OUTAGE_URL = "https://www.zoe.com.ua/outage/"
ZOE_TELEGRAM_URL = "https://t.me/Zaporizhzhyaoblenergo_news"


def load_dotenv(env_path: Path) -> None:
    """Load simple KEY=VALUE pairs from a .env file into os.environ if not already set."""
    if not env_path.is_file():
        return
    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in ("'", '"'):
            value = value[1:-1]
        if key and key not in os.environ:
            os.environ[key] = value


@dataclass(frozen=True)
class Config:
    bot_token: str
    db_path: Path
    cache_path: Path
    primary_url: str
    fallback_url: str
    fetch_interval_seconds: int
    alert_tick_seconds: int
    channel_check_interval_seconds: int
    log_level: str


def load_config(base_dir: Path | None = None) -> Config:
    """Build Config from environment variables and optional .env file."""
    root = base_dir or Path(__file__).resolve().parent
    load_dotenv(root / ".env")

    data_dir = root / "data"
    data_dir.mkdir(parents=True, exist_ok=True)

    return Config(
        bot_token=os.environ.get("BOT_TOKEN", "").strip(),
        db_path=Path(os.environ.get("DB_PATH", str(data_dir / "bot.db"))),
        cache_path=Path(os.environ.get("CACHE_PATH", str(data_dir / "schedule_cache.json"))),
        primary_url=os.environ.get("PRIMARY_DATA_URL", DEFAULT_PRIMARY_URL).strip(),
        fallback_url=os.environ.get("FALLBACK_DATA_URL", DEFAULT_FALLBACK_URL).strip(),
        fetch_interval_seconds=max(15, int(os.environ.get("FETCH_INTERVAL_SECONDS", "30"))),
        alert_tick_seconds=max(5, int(os.environ.get("ALERT_TICK_SECONDS", "10"))),
        channel_check_interval_seconds=max(20, int(os.environ.get("CHANNEL_CHECK_INTERVAL_SECONDS", "30"))),
        log_level=os.environ.get("LOG_LEVEL", "INFO").upper(),
    )
