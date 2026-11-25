"""Unit tests for schedule parsing, formatting, storage, and alert evaluation."""

from __future__ import annotations

import tempfile
import unittest
from datetime import datetime, timedelta
from pathlib import Path

from channel_monitor import (
    format_emergency_alert,
    is_emergency_power_post,
    parse_channel_html,
)
from config import KYIV_TZ
from notifier import evaluate_user_alerts, seed_user_snapshots
from schedule import (
    collect_timeline_intervals,
    format_day_schedule,
    format_now_status,
    normalize_queue,
)
from storage import Storage


def _build_hours(overrides: dict[str, str] | None = None) -> dict[str, str]:
    hours = {str(i): "yes" for i in range(1, 25)}
    if overrides:
        hours.update(overrides)
    return hours


class ScheduleTests(unittest.TestCase):
    def setUp(self) -> None:
        self.today_dt = datetime(2026, 11, 25, 0, 0, tzinfo=KYIV_TZ)
        self.tomorrow_dt = self.today_dt + timedelta(days=1)
        self.today_ts = str(int(self.today_dt.timestamp()))
        self.tomorrow_ts = str(int(self.tomorrow_dt.timestamp()))

        self.sample_data = {
            "regionId": "Zaporizhzhia",
            "lastUpdated": "2026-11-25T01:30:00+00:00",
            "fact": {
                "today": int(self.today_ts),
                "update": "25.11.2026 03:30",
                "data": {
                    self.today_ts: {
                        "GPV1.1": _build_hours(
                            {
                                "6": "second",  # 05:30 - 06:00 off
                                "7": "no",      # 06:00 - 07:00 off
                                "8": "first",   # 07:00 - 07:30 off
                                "24": "second", # 23:30 - 24:00 off
                            }
                        )
                    },
                    self.tomorrow_ts: {
                        "GPV1.1": _build_hours(
                            {
                                "1": "no",      # 00:00 - 01:00 off
                                "2": "first",   # 01:00 - 01:30 off
                            }
                        )
                    },
                },
            },
            "availability": {},
            "schedule_updates": {self.today_ts: "25.11.2026 03:30"},
        }

    def test_normalize_queue(self) -> None:
        self.assertEqual(normalize_queue("1.1"), "GPV1.1")
        self.assertEqual(normalize_queue("gpv6.2"), "GPV6.2")
        self.assertIsNone(normalize_queue("9.9"))

    def test_cross_midnight_merging(self) -> None:
        intervals = collect_timeline_intervals(self.sample_data, "GPV1.1", self.today_dt, days_ahead=2)
        off_intervals = [iv for iv in intervals if iv.state == "off"]
        self.assertEqual(len(off_intervals), 2)

        self.assertEqual(off_intervals[0].start.strftime("%H:%M"), "05:30")
        self.assertEqual(off_intervals[0].end.strftime("%H:%M"), "07:30")
        self.assertEqual(off_intervals[0].duration_minutes, 120)

        # 23:30 on Nov 25 merged with 00:00-01:30 on Nov 26
        self.assertEqual(off_intervals[1].start, datetime(2026, 11, 25, 23, 30, tzinfo=KYIV_TZ))
        self.assertEqual(off_intervals[1].end, datetime(2026, 11, 26, 1, 30, tzinfo=KYIV_TZ))
        self.assertEqual(off_intervals[1].duration_minutes, 120)

    def test_format_day_schedule_and_unpublished(self) -> None:
        # Default language is Ukrainian
        today_msg = format_day_schedule(self.sample_data, self.today_dt, "GPV1.1", "Сьогодні")
        self.assertIn("05:30 – 07:30", today_msg)
        self.assertIn("23:30 – 24:00", today_msg)
        self.assertIn("2.5 год", today_msg)

        # English formatting
        today_en = format_day_schedule(self.sample_data, self.today_dt, "GPV1.1", "Today", lang="en")
        self.assertIn("Total without power", today_en)
        self.assertIn("2.5 h", today_en)

        self.sample_data["availability"][self.tomorrow_ts] = "unpublished"
        tomorrow_msg = format_day_schedule(self.sample_data, self.tomorrow_dt, "GPV1.1", "Завтра")
        self.assertIn("ще не опубліковано", tomorrow_msg)

    def test_format_now_status(self) -> None:
        before_outage = datetime(2026, 11, 25, 5, 15, tzinfo=KYIV_TZ)
        msg_on = format_now_status(self.sample_data, before_outage, "GPV1.1")
        self.assertIn("Світло зараз є", msg_on)
        self.assertIn("05:30 – 07:30", msg_on)
        self.assertIn("через 15 хв", msg_on)

        during_outage = datetime(2026, 11, 25, 6, 40, tzinfo=KYIV_TZ)
        msg_off = format_now_status(self.sample_data, during_outage, "GPV1.1", lang="ru")
        self.assertIn("Света сейчас нет", msg_off)
        self.assertIn("07:30", msg_off)
        self.assertIn("через 50 мин", msg_off)


class NotifierTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.db_path = Path(self.tmp.name) / "test.db"
        self.storage = Storage(self.db_path)

        self.today_dt = datetime(2026, 11, 25, 0, 0, tzinfo=KYIV_TZ)
        self.tomorrow_dt = self.today_dt + timedelta(days=1)
        self.today_ts = str(int(self.today_dt.timestamp()))
        self.tomorrow_ts = str(int(self.tomorrow_dt.timestamp()))

        self.data = {
            "regionId": "Zaporizhzhia",
            "lastUpdated": "2026-11-25T01:30:00+00:00",
            "fact": {
                "today": int(self.today_ts),
                "data": {
                    self.today_ts: {
                        "GPV1.1": _build_hours({"10": "no", "11": "no"}),  # 09:00 - 11:00 off
                    }
                },
            },
            "availability": {self.tomorrow_ts: "unpublished"},
        }

    def tearDown(self) -> None:
        self.storage.close()
        self.tmp.cleanup()

    def test_pre_outage_and_restore_deduplication(self) -> None:
        user = self.storage.set_queue(12345, "GPV1.1")
        seed_user_snapshots(self.storage, self.data, 12345, "GPV1.1", datetime(2026, 11, 25, 8, 0, tzinfo=KYIV_TZ))

        # Too early (08:30, 30 min before outage, lead is 15 min)
        alerts = evaluate_user_alerts(user, self.data, datetime(2026, 11, 25, 8, 30, tzinfo=KYIV_TZ), self.storage)
        self.assertEqual(alerts, [])

        # Inside lead window (08:47 -> 13 min before 09:00)
        alerts = evaluate_user_alerts(user, self.data, datetime(2026, 11, 25, 8, 47, tzinfo=KYIV_TZ), self.storage)
        self.assertEqual(len(alerts), 1)
        self.assertIn("09:00", alerts[0].text)
        self.assertIn("до <b>11:00</b>", alerts[0].text)

        # Second tick 30s later must NOT re-send
        alerts_dup = evaluate_user_alerts(user, self.data, datetime(2026, 11, 25, 8, 47, 30, tzinfo=KYIV_TZ), self.storage)
        self.assertEqual(alerts_dup, [])

        # Restoration at 11:01 (default Ukrainian)
        alerts_restore = evaluate_user_alerts(user, self.data, datetime(2026, 11, 25, 11, 1, tzinfo=KYIV_TZ), self.storage)
        self.assertEqual(len(alerts_restore), 1)
        self.assertIn("Час включення світла", alerts_restore[0].text)

        # No duplicate restore
        alerts_restore_dup = evaluate_user_alerts(user, self.data, datetime(2026, 11, 25, 11, 2, tzinfo=KYIV_TZ), self.storage)
        self.assertEqual(alerts_restore_dup, [])

    def test_schedule_change_and_tomorrow_published_alerts(self) -> None:
        user = self.storage.set_queue(777, "GPV1.1")
        self.assertEqual(user.lang, "uk")
        user = self.storage.set_lang(777, "en")
        self.assertEqual(user.lang, "en")
        seed_user_snapshots(self.storage, self.data, 777, "GPV1.1", datetime(2026, 11, 25, 8, 0, tzinfo=KYIV_TZ))

        # Update today's schedule and publish tomorrow
        self.data["fact"]["data"][self.today_ts]["GPV1.1"]["15"] = "no"
        self.data["fact"]["data"][self.tomorrow_ts] = {"GPV1.1": _build_hours({"8": "no"})}
        self.data["availability"].pop(self.tomorrow_ts, None)

        alerts = evaluate_user_alerts(user, self.data, datetime(2026, 11, 25, 12, 0, tzinfo=KYIV_TZ), self.storage)
        texts = "\n".join(a.text for a in alerts)
        self.assertIn("Outage schedule updated", texts)
        self.assertIn("Tomorrow's schedule published", texts)

        # No duplicate alerts on next tick
        alerts_next = evaluate_user_alerts(user, self.data, datetime(2026, 11, 25, 12, 1, tzinfo=KYIV_TZ), self.storage)
        self.assertEqual(alerts_next, [])

    def test_paused_user_gets_no_alerts(self) -> None:
        self.storage.set_queue(999, "GPV1.1")
        user = self.storage.toggle_field(999, "paused")
        alerts = evaluate_user_alerts(user, self.data, datetime(2026, 11, 25, 8, 50, tzinfo=KYIV_TZ), self.storage)
        self.assertEqual(alerts, [])


class ChannelMonitorTests(unittest.TestCase):
    def test_emergency_post_filter(self) -> None:
        # True positives
        self.assertTrue(is_emergency_power_post("У Запоріжжі після вибуху перебої зі світлом\n@prozaporizhzhia"))
        self.assertTrue(is_emergency_power_post("Перепади напруги у Запоріжжі після вибуху"))
        self.assertTrue(is_emergency_power_post("Через атаку дронів пошкоджено мережі, частина міста без електроенергії"))
        self.assertTrue(is_emergency_power_post("Запоріжжяобленерго: застосовано ГАВ по місту"))

        # True negatives (routine news & regular schedules)
        self.assertFalse(is_emergency_power_post("Рух транспорту мостами та греблею ДніпроГЕС повністю перекрито"))
        self.assertFalse(is_emergency_power_post("До чого ж гарне небо"))
        self.assertFalse(is_emergency_power_post("Знову графік оновили 1.1: 06:30 – 10:30"))
        self.assertFalse(is_emergency_power_post("Графік відключення світла для Запоріжжя на 25 листопада"))

    def test_parse_channel_html_and_format(self) -> None:
        sample_html = """
        <div class="tgme_widget_message_wrap">
          <div class="tgme_widget_message" data-post="ProZaporizhzhia/4695">
            <time datetime="2026-11-25T01:36:42+00:00"></time>
            <div class="tgme_widget_message_text js-message_text">У Запоріжжі після вибуху перебої зі світлом<br><br>@prozaporizhzhia</div>
          </div>
        </div>
        """
        posts = parse_channel_html("ProZaporizhzhia", "@ProZaporizhzhia", sample_html)
        self.assertEqual(len(posts), 1)
        self.assertEqual(posts[0].numeric_id, 4695)
        self.assertIn("після вибуху перебої зі світлом", posts[0].text)
        formatted = format_emergency_alert(posts[0])
        self.assertIn("Термінове повідомлення про світло", formatted)
        self.assertIn("03:36", formatted)
        self.assertIn("https://t.me/ProZaporizhzhia/4695", formatted)

        formatted_ru = format_emergency_alert(posts[0], lang="ru")
        self.assertIn("Срочное сообщение о свете", formatted_ru)
        formatted_en = format_emergency_alert(posts[0], lang="en")
        self.assertIn("Urgent power report", formatted_en)


if __name__ == "__main__":
    unittest.main()
