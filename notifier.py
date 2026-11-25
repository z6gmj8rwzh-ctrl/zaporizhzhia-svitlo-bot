"""Alert evaluation engine for pre-outage warnings, power restoration, and schedule updates."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any

from config import KYIV_TZ
from i18n import t
from schedule import (
    collect_timeline_intervals,
    day_timestamp_for,
    format_day_schedule,
    format_duration,
    format_queue,
    schedule_signature,
)
from storage import Storage, UserConfig


@dataclass(frozen=True)
class PendingAlert:
    chat_id: int
    text: str


def seed_user_snapshots(storage: Storage, data: dict[str, Any] | None, chat_id: int, queue: str, now: datetime) -> None:
    """Record current schedule signatures as baseline when a user selects a queue."""
    if not data:
        return
    local_today = now.astimezone(KYIV_TZ).replace(hour=0, minute=0, second=0, microsecond=0)
    for offset in (0, 1):
        day_ts = str(int((local_today + timedelta(days=offset)).timestamp()))
        sig = schedule_signature(data, day_ts, queue)
        if sig:
            storage.set_snapshot(chat_id, day_ts, queue, sig)


def evaluate_user_alerts(
    user: UserConfig,
    data: dict[str, Any],
    now: datetime,
    storage: Storage,
) -> list[PendingAlert]:
    """Compute all pending Telegram messages for a single active user and persist dedup state."""
    if not user.queue or user.paused:
        return []

    local_now = now.astimezone(KYIV_TZ)
    now_ts = int(local_now.timestamp())
    queue = user.queue
    lang = user.lang
    q_label = format_queue(queue)
    alerts: list[PendingAlert] = []

    today_dt = local_now.replace(hour=0, minute=0, second=0, microsecond=0)
    tomorrow_dt = today_dt + timedelta(days=1)
    today_ts = day_timestamp_for(today_dt)
    tomorrow_ts = day_timestamp_for(tomorrow_dt)

    # 1. Schedule change & newly published tomorrow schedule alerts
    for day_dt, day_ts, label_key in (
        (today_dt, today_ts, "today_title"),
        (tomorrow_dt, tomorrow_ts, "tomorrow_title"),
    ):
        sig = schedule_signature(data, day_ts, queue)
        if not sig:
            continue
        prev = storage.get_snapshot(user.chat_id, day_ts)
        label = t(lang, label_key)
        if prev is None:
            # First time seeing this day: notify if tomorrow just appeared and user already tracked today
            if day_ts == tomorrow_ts and storage.get_snapshot(user.chat_id, today_ts) is not None and user.notify_on_change:
                body = format_day_schedule(data, day_dt, queue, label, lang=lang)
                alerts.append(
                    PendingAlert(
                        chat_id=user.chat_id,
                        text=t(lang, "alert_tomorrow_published", body=body),
                    )
                )
            storage.set_snapshot(user.chat_id, day_ts, queue, sig)
        elif prev != (queue, sig):
            storage.set_snapshot(user.chat_id, day_ts, queue, sig)
            if user.notify_on_change:
                body = format_day_schedule(data, day_dt, queue, label, lang=lang)
                alerts.append(
                    PendingAlert(
                        chat_id=user.chat_id,
                        text=t(lang, "alert_schedule_changed", body=body),
                    )
                )

    # 2. Pre-outage and restoration alerts across today + tomorrow
    intervals = collect_timeline_intervals(data, queue, today_dt, days_ahead=2, collapse_outage_types=True)
    lead_seconds = user.lead_minutes * 60
    at_word = t(lang, "at_word")

    for idx, iv in enumerate(intervals):
        if iv.state == "off":
            seconds_until = (iv.start - local_now).total_seconds()
            if 0 < seconds_until <= lead_seconds:
                event_key = f"pre_off:{int(iv.start.timestamp())}:{user.lead_minutes}"
                if not storage.was_notified(user.chat_id, event_key):
                    mins_left = max(1, int((seconds_until + 59) // 60))
                    end_label = iv.end.strftime("%H:%M")
                    if iv.end.date() > iv.start.date():
                        end_label = iv.end.strftime("%d.%m %H:%M")
                    alerts.append(
                        PendingAlert(
                            chat_id=user.chat_id,
                            text=t(
                                lang,
                                "alert_pre_off",
                                q=q_label,
                                start=iv.start.strftime("%H:%M"),
                                mins=format_duration(mins_left, lang),
                                end=end_label,
                                dur=format_duration(iv.duration_minutes, lang),
                            ),
                        )
                    )
                    storage.mark_notified(user.chat_id, event_key, now_ts)

        elif iv.state == "on" and user.notify_on_restore and idx > 0 and intervals[idx - 1].state == "off":
            seconds_since_restore = (local_now - iv.start).total_seconds()
            if 0 <= seconds_since_restore <= 300:
                event_key = f"restore:{int(iv.start.timestamp())}"
                if not storage.was_notified(user.chat_id, event_key):
                    next_off = next((n for n in intervals[idx + 1 :] if n.state == "off"), None)
                    extra = ""
                    if next_off:
                        day_prefix = "" if next_off.start.date() == local_now.date() else f"{next_off.start.strftime('%d.%m')} {at_word} "
                        extra = t(lang, "alert_restore_next", day_prefix=day_prefix, time=next_off.start.strftime("%H:%M"))
                    alerts.append(
                        PendingAlert(
                            chat_id=user.chat_id,
                            text=t(lang, "alert_restore", q=q_label, time=iv.start.strftime("%H:%M"), extra=extra),
                        )
                    )
                    storage.mark_notified(user.chat_id, event_key, now_ts)

    return alerts
