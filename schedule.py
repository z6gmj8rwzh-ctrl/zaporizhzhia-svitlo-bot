"""Parsing and formatting for Zaporizhzhiaoblenergo (ZOE) outage schedules."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any

from config import KYIV_TZ
from i18n import (
    DEFAULT_LANG,
    format_duration_localized,
    format_hours_total_localized,
    t,
)

QUEUES: tuple[str, ...] = (
    "GPV1.1",
    "GPV1.2",
    "GPV2.1",
    "GPV2.2",
    "GPV3.1",
    "GPV3.2",
    "GPV4.1",
    "GPV4.2",
    "GPV5.1",
    "GPV5.2",
    "GPV6.1",
    "GPV6.2",
)

OFF_STATES = {"no", "maybe"}


def format_queue(queue: str) -> str:
    """Return human-friendly queue number, e.g. 'GPV1.1' -> '1.1'."""
    return queue.removeprefix("GPV")


def normalize_queue(value: str) -> str | None:
    """Normalize '1.1' or 'GPV1.1' to canonical queue key, or None if invalid."""
    cleaned = value.strip().upper()
    if not cleaned.startswith("GPV"):
        cleaned = f"GPV{cleaned}"
    return cleaned if cleaned in QUEUES else None


@dataclass(frozen=True)
class Slot:
    start: datetime
    end: datetime
    state: str  # "on" | "off" | "maybe"


@dataclass(frozen=True)
class Interval:
    start: datetime
    end: datetime
    state: str  # "on" | "off" | "maybe"

    @property
    def duration_minutes(self) -> int:
        return int((self.end - self.start).total_seconds() // 60)


def day_timestamp_for(dt: datetime) -> str:
    """Return midnight Kyiv Unix timestamp string for the given datetime's date."""
    local = dt.astimezone(KYIV_TZ)
    midnight = local.replace(hour=0, minute=0, second=0, microsecond=0)
    return str(int(midnight.timestamp()))


def _hour_to_half_states(raw_state: str) -> tuple[str, str]:
    """Map ZOE hourly status string to (first_30_min_state, second_30_min_state)."""
    state = (raw_state or "yes").strip().lower()
    if state == "no":
        return ("off", "off")
    if state == "first":
        return ("off", "on")
    if state == "second":
        return ("on", "off")
    if state == "maybe":
        return ("maybe", "maybe")
    if state == "mfirst":
        return ("maybe", "on")
    if state == "msecond":
        return ("on", "maybe")
    return ("on", "on")


def extract_day_slots(data: dict[str, Any], day_ts: str, queue: str) -> list[Slot] | None:
    """Extract 48 half-hour slots for a single day timestamp and queue."""
    fact_data = data.get("fact", {}).get("data", {})
    day_entry = fact_data.get(day_ts)
    if not isinstance(day_entry, dict):
        return None
    queue_hours = day_entry.get(queue)
    if not isinstance(queue_hours, dict):
        return None

    day_start = datetime.fromtimestamp(int(day_ts), tz=KYIV_TZ)
    slots: list[Slot] = []
    for hour_idx in range(1, 25):
        raw_state = str(queue_hours.get(str(hour_idx), "yes"))
        first_state, second_state = _hour_to_half_states(raw_state)
        h_start = day_start + timedelta(hours=hour_idx - 1)
        h_mid = h_start + timedelta(minutes=30)
        h_end = h_start + timedelta(hours=1)
        slots.append(Slot(start=h_start, end=h_mid, state=first_state))
        slots.append(Slot(start=h_mid, end=h_end, state=second_state))
    return slots


def merge_slots(slots: list[Slot], collapse_outage_types: bool = False) -> list[Interval]:
    """Merge consecutive slots of the same state into Intervals."""
    if not slots:
        return []
    ordered = sorted(slots, key=lambda s: s.start)

    def norm(st: str) -> str:
        if collapse_outage_types and st in ("off", "maybe"):
            return "off"
        return st

    merged: list[Interval] = []
    cur_start = ordered[0].start
    cur_end = ordered[0].end
    cur_state = norm(ordered[0].state)

    for slot in ordered[1:]:
        s_state = norm(slot.state)
        if s_state == cur_state and slot.start == cur_end:
            cur_end = slot.end
        else:
            merged.append(Interval(start=cur_start, end=cur_end, state=cur_state))
            cur_start = slot.start
            cur_end = slot.end
            cur_state = s_state

    merged.append(Interval(start=cur_start, end=cur_end, state=cur_state))
    return merged


def collect_timeline_intervals(
    data: dict[str, Any],
    queue: str,
    start_day_dt: datetime,
    days_ahead: int = 2,
    collapse_outage_types: bool = True,
) -> list[Interval]:
    """Build merged continuous intervals starting from start_day_dt across consecutive published days."""
    base = start_day_dt.astimezone(KYIV_TZ).replace(hour=0, minute=0, second=0, microsecond=0)
    all_slots: list[Slot] = []
    for offset in range(days_ahead):
        day_dt = base + timedelta(days=offset)
        day_ts = str(int(day_dt.timestamp()))
        slots = extract_day_slots(data, day_ts, queue)
        if slots is None:
            break
        all_slots.extend(slots)
    return merge_slots(all_slots, collapse_outage_types=collapse_outage_types)


def schedule_signature(data: dict[str, Any], day_ts: str, queue: str) -> str | None:
    """Return deterministic hash of a queue's schedule + availability for day_ts, or None if unavailable."""
    availability = data.get("availability", {}).get(day_ts)
    if availability == "unpublished":
        return None
    fact_data = data.get("fact", {}).get("data", {})
    day_entry = fact_data.get(day_ts)
    if not isinstance(day_entry, dict) or queue not in day_entry:
        return None
    payload = {
        "hours": day_entry[queue],
        "availability": availability or "confirmed",
    }
    encoded = json.dumps(payload, sort_keys=True).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()[:16]


def format_duration(minutes: int, lang: str = DEFAULT_LANG) -> str:
    """Format duration in minutes into concise localized text."""
    return format_duration_localized(minutes, lang)


def format_hours_total(minutes: int, lang: str = DEFAULT_LANG) -> str:
    """Format total outage minutes (always multiple of 30) nicely."""
    return format_hours_total_localized(minutes, lang)


def _availability_note(availability: str | None, lang: str = DEFAULT_LANG) -> str | None:
    if availability == "no_gpv":
        return t(lang, "avail_no_gpv")
    if availability == "cached":
        return t(lang, "avail_cached")
    if availability == "update_failed":
        return t(lang, "avail_failed")
    return None


def _format_update_time(data: dict[str, Any], day_ts: str) -> str | None:
    updates = data.get("schedule_updates", {})
    if isinstance(updates, dict) and day_ts in updates:
        return str(updates[day_ts])
    fact_update = data.get("fact", {}).get("update")
    if fact_update:
        return str(fact_update)
    last_updated = data.get("lastUpdated")
    if isinstance(last_updated, str):
        try:
            dt = datetime.fromisoformat(last_updated.replace("Z", "+00:00")).astimezone(KYIV_TZ)
            return dt.strftime("%d.%m.%Y %H:%M")
        except ValueError:
            return None
    return None


# ─── Visual 24h timeline bar ────────────────────────────────────────────────

def _build_timeline_bar(slots: list[Slot]) -> str:
    """Build a 24-cell visual timeline bar (one char per hour).

    🟢 = on the whole hour
    🔴 = off the whole hour
    🟡 = maybe or mixed
    Hour labels: 0  3  6  9  12 15 18 21 24
    """
    if not slots or len(slots) < 48:
        return ""
    cells: list[str] = []
    for h in range(24):
        s1 = slots[h * 2].state      # first half-hour
        s2 = slots[h * 2 + 1].state  # second half-hour
        if s1 == "on" and s2 == "on":
            cells.append("🟢")
        elif s1 in ("off", "maybe") and s2 in ("off", "maybe"):
            if s1 == "maybe" or s2 == "maybe":
                cells.append("🟡")
            else:
                cells.append("🔴")
        else:
            # Mixed hour (half on, half off)
            cells.append("🟠")
    bar = "".join(cells)
    ruler = "0     3     6     9    12   15   18   21  24"
    return f"<code>{bar}</code>\n<code>{ruler}</code>"


# ─── Outage list formatting ──────────────────────────────────────────────────

def _format_outage_list(
    intervals: list[Interval],
    local_day: datetime,
    lang: str = DEFAULT_LANG,
) -> tuple[str, int]:
    """Format outage intervals list. Returns (text, total_off_minutes)."""
    outages = [iv for iv in intervals if iv.state in ("off", "maybe")]
    if not outages:
        return "", 0

    lines: list[str] = []
    total_off_min = sum(iv.duration_minutes for iv in outages)
    for iv in outages:
        start_s = iv.start.strftime("%H:%M")
        end_s = "24:00" if iv.end.hour == 0 and iv.end.date() > local_day.date() else iv.end.strftime("%H:%M")
        icon = "🔴" if iv.state == "off" else "🟡"
        suffix = t(lang, "sched_maybe_suffix") if iv.state == "maybe" else ""
        lines.append(f"{icon} <b>{start_s} – {end_s}</b> ({format_duration(iv.duration_minutes, lang)}){suffix}")
    return "\n".join(lines), total_off_min


# ─── Remaining today's intervals ─────────────────────────────────────────────

def _format_remaining_today(
    data: dict[str, Any],
    now: datetime,
    queue: str,
    lang: str = DEFAULT_LANG,
) -> str | None:
    """Format remaining outage intervals for the rest of today, if any."""
    local_now = now.astimezone(KYIV_TZ)
    today_dt = local_now.replace(hour=0, minute=0, second=0, microsecond=0)
    day_ts = str(int(today_dt.timestamp()))
    slots = extract_day_slots(data, day_ts, queue)
    if not slots:
        return None
    intervals = merge_slots(slots, collapse_outage_types=False)
    # Only future or current outages
    remaining = [iv for iv in intervals if iv.state in ("off", "maybe") and iv.end > local_now]
    if not remaining:
        return None

    lines: list[str] = []
    for iv in remaining:
        start_s = iv.start.strftime("%H:%M")
        end_s = "24:00" if iv.end.hour == 0 and iv.end.date() > today_dt.date() else iv.end.strftime("%H:%M")
        icon = "🔴" if iv.state == "off" else "🟡"
        lines.append(f"{icon} {start_s} – {end_s}")
    return t(lang, "remaining_today_label") + "\n" + "  ".join(lines) if lines else None


# ─── Main format functions ───────────────────────────────────────────────────

def format_day_schedule(
    data: dict[str, Any],
    day_dt: datetime,
    queue: str,
    title: str,
    lang: str = DEFAULT_LANG,
) -> str:
    """Format full schedule message for a given date and queue."""
    local_day = day_dt.astimezone(KYIV_TZ).replace(hour=0, minute=0, second=0, microsecond=0)
    day_ts = str(int(local_day.timestamp()))
    date_label = local_day.strftime("%d.%m.%Y")
    q_label = format_queue(queue)

    availability = data.get("availability", {}).get(day_ts)
    if availability == "unpublished":
        return t(lang, "sched_unpublished", title=title, date=date_label, q=q_label)

    slots = extract_day_slots(data, day_ts, queue)
    if not slots:
        return t(lang, "sched_no_data", title=title, date=date_label, q=q_label)

    intervals = merge_slots(slots, collapse_outage_types=False)
    outages = [iv for iv in intervals if iv.state in ("off", "maybe")]

    lines = [t(lang, "sched_header", title=title, date=date_label, q=q_label)]
    note = _availability_note(availability, lang)
    if note:
        lines.append(note)

    # Visual timeline
    timeline = _build_timeline_bar(slots)
    if timeline:
        lines.append("")
        lines.append(timeline)

    if not outages:
        if availability != "no_gpv":
            lines.append(t(lang, "sched_no_outages"))
    else:
        total_off_min = sum(iv.duration_minutes for iv in outages)
        lines.append("")
        for iv in outages:
            start_s = iv.start.strftime("%H:%M")
            end_s = "24:00" if iv.end.hour == 0 and iv.end.date() > local_day.date() else iv.end.strftime("%H:%M")
            icon = "🔴" if iv.state == "off" else "🟡"
            suffix = t(lang, "sched_maybe_suffix") if iv.state == "maybe" else ""
            lines.append(f"{icon} <b>{start_s} – {end_s}</b> ({format_duration(iv.duration_minutes, lang)}){suffix}")
        lines.append(t(lang, "sched_total_off", total=format_hours_total(total_off_min, lang)))

    updated = _format_update_time(data, day_ts)
    if updated:
        lines.append(t(lang, "sched_updated_at", updated=updated))

    return "\n".join(lines)


def format_now_status(
    data: dict[str, Any],
    now: datetime,
    queue: str,
    lang: str = DEFAULT_LANG,
) -> str:
    """Format current power status with full remaining-day context."""
    local_now = now.astimezone(KYIV_TZ)
    q_label = format_queue(queue)
    intervals = collect_timeline_intervals(data, queue, local_now, days_ahead=2, collapse_outage_types=False)
    if not intervals:
        return t(lang, "now_no_data", time=local_now.strftime("%H:%M"), q=q_label)

    current_idx: int | None = None
    for idx, iv in enumerate(intervals):
        if iv.start <= local_now < iv.end:
            current_idx = idx
            break

    if current_idx is None:
        return t(lang, "now_no_interval", time=local_now.strftime("%H:%M"), q=q_label)

    cur = intervals[current_idx]
    is_off = cur.state in ("off", "maybe")
    at_word = t(lang, "at_word")

    # Build main status line
    parts: list[str] = []

    if is_off:
        restore_dt = cur.end
        for nxt in intervals[current_idx + 1:]:
            if nxt.state == "on":
                restore_dt = nxt.start
                break
            restore_dt = nxt.end

        remaining_min = max(1, int((restore_dt - local_now).total_seconds() // 60))
        day_prefix = "" if restore_dt.date() == local_now.date() else f"{restore_dt.strftime('%d.%m')} {at_word} "
        kind = t(lang, "now_off_planned") if cur.state == "off" else t(lang, "now_off_maybe")
        parts.append(t(
            lang,
            "now_off_detail",
            kind=kind,
            q=q_label,
            day_prefix=day_prefix,
            time=restore_dt.strftime("%H:%M"),
            dur=format_duration(remaining_min, lang),
        ))
    else:
        next_outage = next((iv for iv in intervals[current_idx + 1:] if iv.state in ("off", "maybe")), None)
        if not next_outage:
            parts.append(t(lang, "now_on_clear", q=q_label))
        else:
            until_min = max(1, int((next_outage.start - local_now).total_seconds() // 60))
            day_prefix = "" if next_outage.start.date() == local_now.date() else f"{next_outage.start.strftime('%d.%m')} {at_word} "
            end_dt = next_outage.end
            next_idx = intervals.index(next_outage)
            for nxt in intervals[next_idx + 1:]:
                if nxt.state in ("off", "maybe") and nxt.start == end_dt:
                    end_dt = nxt.end
                else:
                    break
            end_s = end_dt.strftime("%H:%M")
            kind = t(lang, "now_on_kind_off") if next_outage.state == "off" else t(lang, "now_on_kind_maybe")
            parts.append(t(
                lang,
                "now_on_detail",
                q=q_label,
                kind=kind,
                day_prefix=day_prefix,
                start=next_outage.start.strftime("%H:%M"),
                end=end_s,
                dur=format_duration(until_min, lang),
            ))

    # Add remaining today's outages context
    remaining = _format_remaining_today(data, now, queue, lang)
    if remaining:
        parts.append("")
        parts.append(remaining)

    # Add timeline bar for today
    today_dt = local_now.replace(hour=0, minute=0, second=0, microsecond=0)
    day_ts = str(int(today_dt.timestamp()))
    slots = extract_day_slots(data, day_ts, queue)
    if slots:
        timeline = _build_timeline_bar(slots)
        if timeline:
            parts.append("")
            parts.append(timeline)

    return "\n".join(parts)


def compute_schedule_diff(
    data_old: dict[str, Any],
    data_new: dict[str, Any],
    day_ts: str,
    queue: str,
    lang: str = DEFAULT_LANG,
) -> str | None:
    """Compare two schedule versions and produce a human-readable diff.

    Returns None if no meaningful difference or data unavailable.
    """
    slots_old = extract_day_slots(data_old, day_ts, queue) if data_old else None
    slots_new = extract_day_slots(data_new, day_ts, queue)
    if not slots_new:
        return None

    day_start = datetime.fromtimestamp(int(day_ts), tz=KYIV_TZ)

    if not slots_old:
        # No previous data — just show new schedule
        return None

    intervals_old = merge_slots(slots_old, collapse_outage_types=False)
    intervals_new = merge_slots(slots_new, collapse_outage_types=False)

    old_outages = {(iv.start, iv.end) for iv in intervals_old if iv.state in ("off", "maybe")}
    new_outages = {(iv.start, iv.end) for iv in intervals_new if iv.state in ("off", "maybe")}

    added = new_outages - old_outages
    removed = old_outages - new_outages

    if not added and not removed:
        return None

    lines: list[str] = []
    if removed:
        lines.append(t(lang, "diff_removed_label"))
        for start, end in sorted(removed):
            end_s = "24:00" if end.hour == 0 and end.date() > day_start.date() else end.strftime("%H:%M")
            lines.append(f"  ✅ <s>{start.strftime('%H:%M')} – {end_s}</s>")
    if added:
        lines.append(t(lang, "diff_added_label"))
        for start, end in sorted(added):
            end_s = "24:00" if end.hour == 0 and end.date() > day_start.date() else end.strftime("%H:%M")
            lines.append(f"  🔴 <b>{start.strftime('%H:%M')} – {end_s}</b>")

    return "\n".join(lines)
