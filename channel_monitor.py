"""Monitor public Telegram channel web previews for emergency power disruptions in Zaporizhzhia."""

from __future__ import annotations

import html
import logging
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Iterable

import httpx

from config import KYIV_TZ
from i18n import DEFAULT_LANG, t

logger = logging.getLogger(__name__)

DEFAULT_EMERGENCY_CHANNELS: tuple[tuple[str, str], ...] = (
    ("ProZaporizhzhia", "@ProZaporizhzhia"),
    ("Zaporizhzhyaoblenergo_news", "@Zaporizhzhyaoblenergo_news"),
)

_POWER_STEMS = (
    "світл",
    "свет",
    "електро",
    "электро",
    "напруг",
    "напряжен",
    "знеструм",
    "обесточ",
    "блекаут",
    "blackout",
    "підстанц",
    "подстанц",
    "енергооб",
    "энергооб",
    "відключен",
    "отключен",
)

_ABBREV_RE = re.compile(r"\b(гав|гао|сгав)\b", re.I)

_INCIDENT_STEMS = (
    "перебо",
    "перепад",
    "вибух",
    "взрыв",
    "дрон",
    "шахед",
    "бпла",
    "ракет",
    "обстріл",
    "обстрел",
    "прил",
    "удар",
    "атак",
    "пошкодж",
    "поврежд",
    "аварі",
    "авари",
    "знеструм",
    "обесточ",
    "зник",
    "пропал",
    "немає",
    "нет свет",
    "без світл",
    "без свет",
    "без електро",
    "без электр",
    "скачк",
    "блима",
    "мига",
    "екстре",
    "экстрен",
    "віднов",
    "восстанов",
    "зажив",
    "запитал",
)

_ROUTINE_SCHEDULE_PHRASES = (
    "графік відключення світла",
    "графіки погодинних відключень",
    "погодинних відключень",
    "погодинні відключення",
    "оновили графік",
    "графік оновили",
    "графік гпв",
    "діятимуть гпв",
    "черги відключень",
)

_STRONG_ATTACK_OR_OUTAGE_PHRASES = (
    "перебо",
    "перепад",
    "вибух",
    "взрыв",
    "дрон",
    "шахед",
    "бпла",
    "ракет",
    "обстріл",
    "обстрел",
    "удар",
    "атак",
    "пошкодж",
    "поврежд",
    "аварі",
    "авари",
    "екстре",
    "экстрен",
)

_POST_ID_RE = re.compile(r'data-post="([^"]+)"')
_DATETIME_RE = re.compile(r'datetime="([^"]+)"')
_TEXT_RE = re.compile(r'class="tgme_widget_message_text[^"]*"[^>]*>(.*?)</div>', re.S)


@dataclass(frozen=True)
class ChannelPost:
    channel: str
    channel_label: str
    post_id: str
    numeric_id: int
    published_at: datetime
    text: str
    url: str


def _clean_html_text(raw_html: str) -> str:
    # Convert <br> to newlines before stripping tags
    with_newlines = re.sub(r"<br\s*/?>", "\n", raw_html, flags=re.I)
    no_tags = re.sub(r"<[^>]+>", "", with_newlines)
    unescaped = html.unescape(no_tags)
    lines = [line.strip() for line in unescaped.splitlines()]
    collapsed = "\n".join(line for line in lines if line)
    return re.sub(r"[ \t]{2,}", " ", collapsed).strip()


def _parse_numeric_id(post_id: str) -> int:
    _, _, tail = post_id.partition("/")
    try:
        return int(tail)
    except ValueError:
        return 0


def parse_channel_html(channel: str, channel_label: str, page_html: str) -> list[ChannelPost]:
    """Parse posts from https://t.me/s/<channel> HTML."""
    posts: list[ChannelPost] = []
    blocks = page_html.split("tgme_widget_message_wrap")
    for block in blocks[1:]:
        post_match = _POST_ID_RE.search(block)
        dt_match = _DATETIME_RE.search(block)
        txt_match = _TEXT_RE.search(block)
        if not post_match or not txt_match:
            continue
        post_id = post_match.group(1)
        clean_text = _clean_html_text(txt_match.group(1))
        if not clean_text:
            continue

        published_at = datetime.now(timezone.utc)
        if dt_match:
            try:
                published_at = datetime.fromisoformat(dt_match.group(1).replace("Z", "+00:00"))
            except ValueError:
                pass

        posts.append(
            ChannelPost(
                channel=channel,
                channel_label=channel_label,
                post_id=post_id,
                numeric_id=_parse_numeric_id(post_id),
                published_at=published_at,
                text=clean_text,
                url=f"https://t.me/{post_id}",
            )
        )
    posts.sort(key=lambda p: p.numeric_id)
    return posts


def is_emergency_power_post(text: str) -> bool:
    """Return True if post is about power disruptions, voltage drops, or emergency/attack outages."""
    lowered = text.lower()
    has_abbrev = bool(_ABBREV_RE.search(lowered))
    has_power = has_abbrev or any(stem in lowered for stem in _POWER_STEMS)
    if not has_power:
        return False

    has_incident = has_abbrev or any(stem in lowered for stem in _INCIDENT_STEMS)
    if not has_incident:
        return False

    # Filter out routine daily schedule publications unless they mention an attack/emergency
    is_routine_schedule = any(phrase in lowered for phrase in _ROUTINE_SCHEDULE_PHRASES)
    if is_routine_schedule:
        has_strong_emergency = has_abbrev or any(p in lowered for p in _STRONG_ATTACK_OR_OUTAGE_PHRASES)
        if not has_strong_emergency:
            return False

    return True


def format_emergency_alert(post: ChannelPost, lang: str = DEFAULT_LANG) -> str:
    """Format an HTML Telegram message for an emergency power disruption post."""
    local_time = post.published_at.astimezone(KYIV_TZ).strftime("%H:%M")
    safe_text = html.escape(post.text)
    if len(safe_text) > 700:
        safe_text = safe_text[:697] + "..."
    return t(
        lang,
        "emergency_alert",
        channel=html.escape(post.channel_label),
        time=local_time,
        text=safe_text,
        url=post.url,
    )


class ChannelMonitor:
    """Fetches public Telegram channel previews and returns newly seen emergency posts."""

    def __init__(self, channels: Iterable[tuple[str, str]] = DEFAULT_EMERGENCY_CHANNELS) -> None:
        self.channels = tuple(channels)

    async def fetch_channel_posts(self, client: httpx.AsyncClient, channel: str, label: str) -> list[ChannelPost]:
        url = f"https://t.me/s/{channel}"
        try:
            resp = await client.get(url, timeout=15.0, follow_redirects=True)
            resp.raise_for_status()
            return parse_channel_html(channel, label, resp.text)
        except httpx.HTTPError as exc:
            logger.warning("Failed to fetch Telegram channel %s: %s", channel, exc)
            return []

    async def fetch_all(self) -> dict[str, list[ChannelPost]]:
        results: dict[str, list[ChannelPost]] = {}
        async with httpx.AsyncClient(headers={"User-Agent": "Mozilla/5.0"}) as client:
            for channel, label in self.channels:
                posts = await self.fetch_channel_posts(client, channel, label)
                if posts:
                    results[channel] = posts
        return results
