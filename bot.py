"""Telegram bot entrypoint for Zaporizhzhia power outage warnings."""

from __future__ import annotations

import asyncio
import contextlib
import logging
from datetime import datetime, timedelta

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, Update
from telegram.constants import ParseMode
from telegram.error import Forbidden, TelegramError
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

from channel_monitor import (
    ChannelMonitor,
    ChannelPost,
    format_emergency_alert,
    is_emergency_power_post,
)
from config import KYIV_TZ, ZOE_OUTAGE_URL, ZOE_TELEGRAM_URL, Config, load_config
from fetcher import ScheduleFetcher
from i18n import (
    DEFAULT_LANG,
    LANG_BUTTONS,
    LANG_DISPLAY_NAMES,
    SUPPORTED_LANGS,
    t,
)
from notifier import evaluate_user_alerts, seed_user_snapshots
from schedule import (
    QUEUES,
    format_day_schedule,
    format_now_status,
    format_queue,
    normalize_queue,
)
from storage import Storage, UserConfig

logger = logging.getLogger(__name__)

LEAD_OPTIONS = (5, 10, 15, 30, 60)

NOW_BUTTON_LABELS = {t(code, "btn_now") for code in SUPPORTED_LANGS}
TODAY_BUTTON_LABELS = {t(code, "btn_today") for code in SUPPORTED_LANGS}
TOMORROW_BUTTON_LABELS = {t(code, "btn_tomorrow") for code in SUPPORTED_LANGS}
SETTINGS_BUTTON_LABELS = {t(code, "btn_settings") for code in SUPPORTED_LANGS}


def build_main_keyboard(lang: str = DEFAULT_LANG) -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        [
            [t(lang, "btn_now"), t(lang, "btn_today")],
            [t(lang, "btn_tomorrow"), t(lang, "btn_settings")],
        ],
        resize_keyboard=True,
    )


def build_queue_keyboard(lang: str = DEFAULT_LANG) -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = []
    for i in range(0, len(QUEUES), 4):
        row = [
            InlineKeyboardButton(
                t(lang, "queue_btn", q=format_queue(q)),
                callback_data=f"q:{q}",
            )
            for q in QUEUES[i : i + 4]
        ]
        rows.append(row)
    rows.append([InlineKeyboardButton(t(lang, "queue_lookup_btn"), url=ZOE_OUTAGE_URL)])
    return InlineKeyboardMarkup(rows)


def build_settings_keyboard(user: UserConfig) -> InlineKeyboardMarkup:
    lang = user.lang
    min_unit = t(lang, "min_short")
    lead_row = [
        InlineKeyboardButton(
            f"{'✅ ' if user.lead_minutes == m else ''}{m} {min_unit}",
            callback_data=f"lead:{m}",
        )
        for m in LEAD_OPTIONS
    ]
    lang_row = [
        InlineKeyboardButton(
            f"{'✅ ' if lang == code else ''}{label}",
            callback_data=f"lang:{code}",
        )
        for code, label in LANG_BUTTONS
    ]

    return InlineKeyboardMarkup(
        [
            lead_row,
            lang_row,
            [InlineKeyboardButton(t(lang, "btn_change_queue"), callback_data="action:choose_queue")],
        ]
    )


def format_settings_text(user: UserConfig) -> str:
    lang = user.lang
    q_label = format_queue(user.queue) if user.queue else t(lang, "not_selected")
    status = t(lang, "status_paused" if user.paused else "status_active")
    return t(
        lang,
        "settings_text",
        q=q_label,
        status=status,
        lead=user.lead_minutes,
        restore=t(lang, "yes" if user.notify_on_restore else "no"),
        change=t(lang, "yes" if user.notify_on_change else "no"),
        emergency=t(lang, "yes" if user.notify_on_emergency else "no"),
        lang_name=LANG_DISPLAY_NAMES.get(lang, lang),
    )


async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.effective_chat or not update.message:
        return
    storage: Storage = context.application.bot_data["storage"]
    user = storage.ensure_user(update.effective_chat.id)
    lang = user.lang

    text = t(lang, "start_intro")
    if user.queue:
        text += t(lang, "start_has_queue", q=format_queue(user.queue))
    else:
        text += t(lang, "start_pick_queue")

    await update.message.reply_text(
        text,
        parse_mode=ParseMode.HTML,
        reply_markup=build_queue_keyboard(lang),
    )
    await update.message.reply_text(
        t(lang, "menu_hint"),
        reply_markup=build_main_keyboard(lang),
    )


async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.effective_chat or not update.message:
        return
    storage: Storage = context.application.bot_data["storage"]
    user = storage.ensure_user(update.effective_chat.id)
    await update.message.reply_text(
        t(user.lang, "help_text", zoe_url=ZOE_OUTAGE_URL, zoe_tg=ZOE_TELEGRAM_URL),
        parse_mode=ParseMode.HTML,
        disable_web_page_preview=True,
        reply_markup=build_main_keyboard(user.lang),
    )


async def cmd_queue(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.effective_chat or not update.message:
        return
    storage: Storage = context.application.bot_data["storage"]
    fetcher: ScheduleFetcher = context.application.bot_data["fetcher"]
    user = storage.ensure_user(update.effective_chat.id)

    if context.args:
        parsed = normalize_queue(context.args[0])
        if parsed:
            user = storage.set_queue(update.effective_chat.id, parsed)
            seed_user_snapshots(storage, fetcher.data, user.chat_id, parsed, datetime.now(KYIV_TZ))
            await update.message.reply_text(
                t(user.lang, "queue_set", q=format_queue(parsed)),
                parse_mode=ParseMode.HTML,
                reply_markup=build_main_keyboard(user.lang),
            )
            return

    await update.message.reply_text(
        t(user.lang, "choose_queue"),
        reply_markup=build_queue_keyboard(user.lang),
    )


async def _require_queue(update: Update, context: ContextTypes.DEFAULT_TYPE) -> UserConfig | None:
    if not update.effective_chat or not update.message:
        return None
    storage: Storage = context.application.bot_data["storage"]
    user = storage.ensure_user(update.effective_chat.id)
    if not user.queue:
        await update.message.reply_text(
            t(user.lang, "need_queue"),
            reply_markup=build_queue_keyboard(user.lang),
        )
        return None
    return user


async def _ensure_data(fetcher: ScheduleFetcher) -> dict | None:
    if fetcher.data is not None:
        return fetcher.data
    return await fetcher.refresh()


async def cmd_now(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = await _require_queue(update, context)
    if not user or not update.message:
        return
    fetcher: ScheduleFetcher = context.application.bot_data["fetcher"]
    data = await _ensure_data(fetcher)
    if not data:
        await update.message.reply_text(t(user.lang, "fetch_error"))
        return
    msg = format_now_status(data, datetime.now(KYIV_TZ), user.queue or "", lang=user.lang)
    await update.message.reply_text(msg, parse_mode=ParseMode.HTML, reply_markup=build_main_keyboard(user.lang))


async def cmd_today(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = await _require_queue(update, context)
    if not user or not update.message:
        return
    fetcher: ScheduleFetcher = context.application.bot_data["fetcher"]
    data = await _ensure_data(fetcher)
    if not data:
        await update.message.reply_text(t(user.lang, "fetch_error"))
        return
    msg = format_day_schedule(
        data,
        datetime.now(KYIV_TZ),
        user.queue or "",
        t(user.lang, "today_title"),
        lang=user.lang,
    )
    await update.message.reply_text(msg, parse_mode=ParseMode.HTML, reply_markup=build_main_keyboard(user.lang))


async def cmd_tomorrow(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = await _require_queue(update, context)
    if not user or not update.message:
        return
    fetcher: ScheduleFetcher = context.application.bot_data["fetcher"]
    data = await _ensure_data(fetcher)
    if not data:
        await update.message.reply_text(t(user.lang, "fetch_error"))
        return
    tomorrow = datetime.now(KYIV_TZ) + timedelta(days=1)
    msg = format_day_schedule(
        data,
        tomorrow,
        user.queue or "",
        t(user.lang, "tomorrow_title"),
        lang=user.lang,
    )
    await update.message.reply_text(msg, parse_mode=ParseMode.HTML, reply_markup=build_main_keyboard(user.lang))


async def cmd_settings(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.effective_chat or not update.message:
        return
    storage: Storage = context.application.bot_data["storage"]
    user = storage.ensure_user(update.effective_chat.id)
    await update.message.reply_text(
        format_settings_text(user),
        parse_mode=ParseMode.HTML,
        reply_markup=build_settings_keyboard(user),
    )


async def cmd_incidents(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.effective_chat or not update.message:
        return
    storage: Storage = context.application.bot_data["storage"]
    user = storage.ensure_user(update.effective_chat.id)
    lang = user.lang
    monitor: ChannelMonitor = context.application.bot_data["channel_monitor"]
    all_posts_map = await monitor.fetch_all()
    cutoff = datetime.now(KYIV_TZ) - timedelta(hours=24)
    matched: list[ChannelPost] = []
    for posts in all_posts_map.values():
        for post in posts:
            if post.published_at.astimezone(KYIV_TZ) >= cutoff and is_emergency_power_post(post.text):
                matched.append(post)

    matched.sort(key=lambda p: p.published_at, reverse=True)
    if not matched:
        await update.message.reply_text(
            t(lang, "incidents_empty"),
            reply_markup=build_main_keyboard(lang),
        )
        return

    lines = [t(lang, "incidents_header")]
    link_label = t(lang, "incidents_link")
    for post in matched[:5]:
        local_t = post.published_at.astimezone(KYIV_TZ).strftime("%d.%m %H:%M")
        snippet = post.text.replace("\n", " ")
        if len(snippet) > 220:
            snippet = snippet[:217] + "..."
        lines.append(f"• <b>{post.channel_label}</b> ({local_t}): {snippet} <a href='{post.url}'>{link_label}</a>")

    await update.message.reply_text(
        "\n\n".join(lines),
        parse_mode=ParseMode.HTML,
        disable_web_page_preview=True,
        reply_markup=build_main_keyboard(lang),
    )


async def on_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    if not query or not query.data or not query.message:
        return
    await query.answer()

    storage: Storage = context.application.bot_data["storage"]
    fetcher: ScheduleFetcher = context.application.bot_data["fetcher"]
    chat_id = query.message.chat.id
    action, _, payload = query.data.partition(":")

    if action == "q":
        normalized = normalize_queue(payload)
        if not normalized:
            return
        user = storage.set_queue(chat_id, normalized)
        data = await _ensure_data(fetcher)
        seed_user_snapshots(storage, data, chat_id, normalized, datetime.now(KYIV_TZ))
        extra = ""
        if data:
            extra = "\n\n" + format_now_status(data, datetime.now(KYIV_TZ), normalized, lang=user.lang)
        await query.edit_message_text(
            t(user.lang, "queue_selected", q=format_queue(normalized), mins=user.lead_minutes) + extra,
            parse_mode=ParseMode.HTML,
        )
        return

    if action == "lead":
        try:
            minutes = int(payload)
        except ValueError:
            return
        if minutes not in LEAD_OPTIONS:
            return
        user = storage.set_lead_minutes(chat_id, minutes)
        await query.edit_message_text(
            format_settings_text(user),
            parse_mode=ParseMode.HTML,
            reply_markup=build_settings_keyboard(user),
        )
        return

    if action == "lang":
        if payload not in SUPPORTED_LANGS:
            return
        prev = storage.ensure_user(chat_id)
        if prev.lang == payload:
            return
        user = storage.set_lang(chat_id, payload)
        await query.edit_message_text(
            format_settings_text(user),
            parse_mode=ParseMode.HTML,
            reply_markup=build_settings_keyboard(user),
        )
        await context.bot.send_message(
            chat_id=chat_id,
            text=t(user.lang, "lang_updated"),
            reply_markup=build_main_keyboard(user.lang),
        )
        return

    if action == "toggle":
        if payload not in ("notify_on_restore", "notify_on_change", "notify_on_emergency", "paused"):
            return
        user = storage.toggle_field(chat_id, payload)
        await query.edit_message_text(
            format_settings_text(user),
            parse_mode=ParseMode.HTML,
            reply_markup=build_settings_keyboard(user),
        )
        return

    if action == "action" and payload == "choose_queue":
        user = storage.ensure_user(chat_id)
        await query.edit_message_text(
            t(user.lang, "choose_queue"),
            reply_markup=build_queue_keyboard(user.lang),
        )


async def on_text_button(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.message or not update.message.text:
        return
    text = update.message.text.strip()
    if text in NOW_BUTTON_LABELS:
        await cmd_now(update, context)
    elif text in TODAY_BUTTON_LABELS:
        await cmd_today(update, context)
    elif text in TOMORROW_BUTTON_LABELS:
        await cmd_tomorrow(update, context)
    elif text in SETTINGS_BUTTON_LABELS:
        await cmd_settings(update, context)


async def _fetch_loop(app: Application, config: Config) -> None:
    fetcher: ScheduleFetcher = app.bot_data["fetcher"]
    storage: Storage = app.bot_data["storage"]
    while True:
        try:
            await fetcher.refresh()
            cutoff = int((datetime.now(KYIV_TZ) - timedelta(days=3)).timestamp())
            storage.cleanup_old_notifications(cutoff)
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            logger.exception("Unexpected error in fetch loop: %s", exc)
        await asyncio.sleep(config.fetch_interval_seconds)


async def _send_safe(app: Application, storage: Storage, user: UserConfig, text: str) -> None:
    try:
        await app.bot.send_message(
            chat_id=user.chat_id,
            text=text,
            parse_mode=ParseMode.HTML,
            disable_web_page_preview=True,
        )
    except Forbidden:
        logger.info("User %s blocked the bot; pausing notifications.", user.chat_id)
        if not user.paused:
            storage.toggle_field(user.chat_id, "paused")
    except TelegramError as exc:
        logger.warning("Failed to send alert to %s: %s", user.chat_id, exc)


async def _alert_loop(app: Application, config: Config) -> None:
    fetcher: ScheduleFetcher = app.bot_data["fetcher"]
    storage: Storage = app.bot_data["storage"]
    while True:
        try:
            data = fetcher.data
            if data is not None:
                now = datetime.now(KYIV_TZ)
                for user in storage.list_active_users():
                    alerts = evaluate_user_alerts(user, data, now, storage)
                    for alert in alerts:
                        await _send_safe(app, storage, user, alert.text)
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            logger.exception("Unexpected error in alert loop: %s", exc)
        await asyncio.sleep(config.alert_tick_seconds)


async def _process_channel_updates(app: Application, seed_only: bool = False) -> None:
    monitor: ChannelMonitor = app.bot_data["channel_monitor"]
    storage: Storage = app.bot_data["storage"]
    posts_by_channel = await monitor.fetch_all()
    for channel, posts in posts_by_channel.items():
        if not posts:
            continue
        latest_id = max(p.numeric_id for p in posts)
        watermark = storage.get_channel_watermark(channel)
        if watermark is None:
            storage.set_channel_watermark(channel, latest_id)
            continue

        new_posts = [p for p in posts if p.numeric_id > watermark]
        if not new_posts:
            continue
        storage.set_channel_watermark(channel, latest_id)

        if seed_only:
            continue

        emergency_posts = [p for p in new_posts if is_emergency_power_post(p.text)]
        if not emergency_posts:
            continue

        users = storage.list_emergency_users()
        for post in emergency_posts:
            for user in users:
                event_key = f"chan:{post.post_id}"
                if storage.was_notified(user.chat_id, event_key):
                    continue
                msg = format_emergency_alert(post, lang=user.lang)
                await _send_safe(app, storage, user, msg)
                storage.mark_notified(user.chat_id, event_key, int(datetime.now(KYIV_TZ).timestamp()))


async def _channel_loop(app: Application, config: Config) -> None:
    while True:
        try:
            await _process_channel_updates(app, seed_only=False)
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            logger.exception("Unexpected error in channel loop: %s", exc)
        await asyncio.sleep(config.channel_check_interval_seconds)


async def post_init(app: Application) -> None:
    config: Config = app.bot_data["config"]
    fetcher: ScheduleFetcher = app.bot_data["fetcher"]
    await fetcher.refresh()
    await _process_channel_updates(app, seed_only=True)
    app.bot_data["tasks"] = [
        asyncio.create_task(_fetch_loop(app, config), name="fetch_loop"),
        asyncio.create_task(_alert_loop(app, config), name="alert_loop"),
        asyncio.create_task(_channel_loop(app, config), name="channel_loop"),
    ]
    logger.info(
        "Background tasks started (fetch=%ss, alert=%ss, channels=%ss)",
        config.fetch_interval_seconds,
        config.alert_tick_seconds,
        config.channel_check_interval_seconds,
    )


async def post_shutdown(app: Application) -> None:
    for task in app.bot_data.get("tasks", []):
        task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await task
    storage: Storage = app.bot_data["storage"]
    storage.close()
    logger.info("Bot shut down cleanly.")


def build_application(config: Config) -> Application:
    storage = Storage(config.db_path)
    fetcher = ScheduleFetcher(config.primary_url, config.fallback_url, config.cache_path)
    channel_monitor = ChannelMonitor()

    app = (
        Application.builder()
        .token(config.bot_token)
        .post_init(post_init)
        .post_shutdown(post_shutdown)
        .build()
    )
    app.bot_data["config"] = config
    app.bot_data["storage"] = storage
    app.bot_data["fetcher"] = fetcher
    app.bot_data["channel_monitor"] = channel_monitor

    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("help", cmd_help))
    app.add_handler(CommandHandler("queue", cmd_queue))
    app.add_handler(CommandHandler("now", cmd_now))
    app.add_handler(CommandHandler("today", cmd_today))
    app.add_handler(CommandHandler("tomorrow", cmd_tomorrow))
    app.add_handler(CommandHandler("incidents", cmd_incidents))
    app.add_handler(CommandHandler("settings", cmd_settings))
    app.add_handler(CallbackQueryHandler(on_callback))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, on_text_button))
    return app


def main() -> None:
    config = load_config()
    logging.basicConfig(
        level=getattr(logging, config.log_level, logging.INFO),
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )
    if not config.bot_token:
        raise SystemExit(
            "Помилка: не задано BOT_TOKEN.\n"
            "Створіть файл .env на основі .env.example та вставте токен від @BotFather."
        )
    app = build_application(config)
    logger.info("Starting Zaporizhzhia Svitlo Bot...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
