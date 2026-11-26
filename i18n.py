"""Localization strings and helpers for Ukrainian (default), Russian, and English."""

from __future__ import annotations

DEFAULT_LANG = "uk"
SUPPORTED_LANGS: tuple[str, ...] = ("uk", "ru", "en")

LANG_BUTTONS: tuple[tuple[str, str], ...] = (
    ("uk", "🇺🇦 Укр"),
    ("ru", "🇷🇺 Рус"),
    ("en", "🇬🇧 Eng"),
)

STRINGS: dict[str, dict[str, str]] = {
    "uk": {
        "btn_now": "⚡ Зараз",
        "btn_today": "📅 Сьогодні",
        "btn_tomorrow": "📆 Завтра",
        "btn_settings": "⚙️ Налаштування",
        "queue_btn": "Черга {q}",
        "queue_lookup_btn": "🔎 Дізнатися свою чергу (zoe.com.ua)",
        "choose_queue": "Оберіть вашу чергу (підчергу) у Запоріжжі:",
        "need_queue": "Спочатку оберіть вашу чергу ГПВ:",
        "queue_set": "✅ Чергу встановлено: <b>{q}</b>.",
        "queue_selected": (
            "✅ Обрано чергу <b>{q}</b>.\n"
            "Попередження надійде за <b>{mins} хв</b> до відключення (змінити: /settings)."
        ),
        "start_intro": (
            "⚡ <b>Бот сповіщень про відключення світла у Запоріжжі (АТ «Запоріжжяобленерго»)</b>\n\n"
            "Я автоматично попереджу вас перед плановим відключенням, повідомлю про повернення світла, "
            "оновлення графіка та термінові аварійні перебої (після вибухів чи атак дронів).\n\n"
        ),
        "start_has_queue": "Ваша поточна черга: <b>{q}</b>.\nКористуйтеся кнопками внизу або оберіть іншу чергу:",
        "start_pick_queue": "Для початку оберіть вашу чергу ГПВ (наприклад, <b>1.1</b>):",
        "menu_hint": "Швидке меню завжди доступне на клавіатурі нижче 👇",
        "help_text": (
            "ℹ️ <b>Команди бота</b>\n\n"
            "/now — статус світла прямо зараз\n"
            "/today — графік відключень на сьогодні\n"
            "/tomorrow — графік відключень на завтра\n"
            "/incidents — останні термінові повідомлення про перебої\n"
            "/queue — обрати або змінити чергу (1.1 – 6.2)\n"
            "/settings — час попередження, мова та інші опції\n\n"
            "• Дізнатися свою чергу за адресою: <a href='{zoe_url}'>zoe.com.ua/outage</a>\n"
            "• Офіційний канал ЗОЕ: <a href='{zoe_tg}'>Telegram ЗОЕ</a>"
        ),
        "fetch_error": "⚠️ Не вдалося завантажити дані графіка. Спробуйте трохи пізніше.",
        "min_short": "хв",
        "hour_short": "год",
        "less_than_min": "менше хвилини",
        "not_selected": "не обрано",
        "yes": "так",
        "no": "ні",
        "status_paused": "⏸ на паузі",
        "status_active": "✅ активні",
        "toggle_restore_on": "🔔 Про включення світла: УВІМК",
        "toggle_restore_off": "🔕 Про включення світла: ВИМК",
        "toggle_change_on": "🔄 Про зміни графіка: УВІМК",
        "toggle_change_off": "🔕 Про зміни графіка: ВИМК",
        "toggle_emergency_on": "🚨 Термінові перебої/обстріли: УВІМК",
        "toggle_emergency_off": "🔕 Термінові перебої/обстріли: ВИМК",
        "toggle_pause_resume": "▶️ Відновити сповіщення",
        "toggle_pause_stop": "⏸ Пауза сповіщень",
        "btn_change_queue": "🔀 Змінити чергу",
        "settings_text": (
            "⚙️ <b>Налаштування сповіщень</b>\n\n"
            "• Черга: <b>{q}</b>\n"
            "• Автопопередження: <b>{status}</b>\n"
            "• Попереджати за: <b>{lead} хв</b> до відключення\n"
            "• Повідомляти про включення світла: <b>{restore}</b>\n"
            "• Повідомляти про зміну графіка: <b>{change}</b>\n"
            "• Повідомляти про перебої (дрони/аварії): <b>{emergency}</b>\n"
            "• Мова інтерфейсу: <b>{lang_name}</b>\n\n"
            "Оберіть інтервал, мову або перемкніть параметри нижче:"
        ),
        "lang_updated": "🌐 Мову змінено на українську.",
        "today_title": "Сьогодні",
        "tomorrow_title": "Завтра",
        "sched_unpublished": "📅 <b>{title} ({date}) — черга {q}</b>\n\n⏳ Графік на цей день ще не опубліковано.",
        "sched_no_data": "📅 <b>{title} ({date}) — черга {q}</b>\n\n⏳ Даних про графік на цей день поки немає.",
        "sched_header": "📅 <b>{title} ({date}) — черга {q}</b>",
        "avail_no_gpv": "🟢 На цей день відключення (ГПВ) не заплановані.",
        "avail_cached": "ℹ️ Показано збережений графік (нових оновлень поки не було).",
        "avail_failed": "⚠️ Не вдалося оновити дані із сайту, показано останній відомий графік.",
        "sched_no_outages": "\n🟢 Відключень за графіком на цей день немає.",
        "sched_maybe_suffix": " (можливо)",
        "sched_total_off": "\n⏱ Всього без світла: <b>{total}</b>",
        "sched_updated_at": "🕒 Оновлено: {updated}",
        "now_no_data": "⚡ <b>Зараз ({time}) — черга {q}</b>\n\n⏳ Графік на сьогодні поки недоступний.",
        "now_no_interval": "⚡ <b>Зараз ({time}) — черга {q}</b>\n\n⏳ Не вдалося визначити поточний інтервал.",
        "now_off_unknown_end": (
            "🔴 <b>Світла зараз немає</b> (черга {q})\n"
            "⏳ За поточними даними відключення щонайменше до {end}."
        ),
        "now_off_planned": "Планове відключення",
        "now_off_maybe": "Можливе відключення",
        "now_off_detail": (
            "🔴 <b>Світла зараз немає</b> ({kind}, черга {q})\n"
            "🔌 Очікуване включення: {day_prefix}<b>{time}</b> (через {dur})"
        ),
        "now_on_clear": (
            "🟢 <b>Світло зараз є</b> (черга {q})\n"
            "✅ За опублікованим графіком відключень найближчим часом не очікується."
        ),
        "now_on_kind_off": "відключення",
        "now_on_kind_maybe": "можливе відключення",
        "now_on_detail": (
            "🟢 <b>Світло зараз є</b> (черга {q})\n"
            "⚠️ Наступне {kind}: {day_prefix}<b>{start} – {end}</b> (через {dur})"
        ),
        "at_word": "о",
        "alert_tomorrow_published": "📢 <b>Опубліковано графік на завтра!</b>\n\n{body}",
        "alert_schedule_changed": "🔄 <b>Оновився графік відключень!</b>\n\n{body}",
        "alert_pre_off": (
            "⚠️ <b>Попередження про відключення світла!</b>\n"
            "Черга <b>{q}</b>: відключення о <b>{start}</b> (через {mins}).\n"
            "🕒 Орієнтовно до <b>{end}</b> ({dur})."
        ),
        "alert_restore": (
            "🟢 <b>Час включення світла!</b>\n"
            "За графіком для черги <b>{q}</b> електропостачання має відновитися о <b>{time}</b>.{extra}"
        ),
        "alert_restore_next": "\n⚡ Наступне відключення за графіком: {day_prefix}<b>{time}</b>.",
        "emergency_alert": (
            "🚨 <b>Термінове повідомлення про світло ({channel}, {time})</b>\n\n"
            "{text}\n\n"
            "🔗 <a href='{url}'>Джерело повідомлення</a>"
        ),
        "incidents_empty": "🟢 За останні 24 години термінових повідомлень про перебої/аварії в каналах @ProZaporizhzhia та @Zaporizhzhyaoblenergo_news не знайдено.",
        "incidents_header": "🚨 <b>Останні повідомлення про перебої (24 год):</b>\n",
        "incidents_link": "[посилання]",
    },
    "ru": {
        "btn_now": "⚡ Сейчас",
        "btn_today": "📅 Сегодня",
        "btn_tomorrow": "📆 Завтра",
        "btn_settings": "⚙️ Настройки",
        "queue_btn": "Очередь {q}",
        "queue_lookup_btn": "🔎 Узнать свою очередь (zoe.com.ua)",
        "choose_queue": "Выберите вашу очередь (подчередь) в Запорожье:",
        "need_queue": "Сначала выберите вашу очередь ГПВ:",
        "queue_set": "✅ Очередь установлена: <b>{q}</b>.",
        "queue_selected": (
            "✅ Выбрана очередь <b>{q}</b>.\n"
            "Предупреждение придёт за <b>{mins} мин</b> до отключения (изменить: /settings)."
        ),
        "start_intro": (
            "⚡ <b>Бот уведомлений об отключении света в Запорожье (ПАО «Запоріжжяобленерго»)</b>\n\n"
            "Я автоматически предупрежу вас перед плановым отключением, сообщу о включении света, "
            "обновлении графика и срочных аварийных перебоях (после взрывов или атак дронов).\n\n"
        ),
        "start_has_queue": "Ваша текущая очередь: <b>{q}</b>.\nИспользуйте кнопки внизу или выберите другую очередь:",
        "start_pick_queue": "Для начала выберите вашу очередь ГПВ (например, <b>1.1</b>):",
        "menu_hint": "Быстрое меню всегда доступно на клавиатуре ниже 👇",
        "help_text": (
            "ℹ️ <b>Команды бота</b>\n\n"
            "/now — статус света прямо сейчас\n"
            "/today — график отключений на сегодня\n"
            "/tomorrow — график отключений на завтра\n"
            "/incidents — последние срочные сообщения о перебоях\n"
            "/queue — выбрать или сменить очередь (1.1 – 6.2)\n"
            "/settings — время предупреждения, язык и другие опции\n\n"
            "• Узнать свою очередь по адресу: <a href='{zoe_url}'>zoe.com.ua/outage</a>\n"
            "• Официальный канал ЗОЕ: <a href='{zoe_tg}'>Telegram ЗОЕ</a>"
        ),
        "fetch_error": "⚠️ Не удалось загрузить данные графика. Попробуйте чуть позже.",
        "min_short": "мин",
        "hour_short": "ч",
        "less_than_min": "менее минуты",
        "not_selected": "не выбрана",
        "yes": "да",
        "no": "нет",
        "status_paused": "⏸ на паузе",
        "status_active": "✅ активны",
        "toggle_restore_on": "🔔 О включении света: ВКЛ",
        "toggle_restore_off": "🔕 О включении света: ВЫКЛ",
        "toggle_change_on": "🔄 Об изменениях графика: ВКЛ",
        "toggle_change_off": "🔕 Об изменениях графика: ВЫКЛ",
        "toggle_emergency_on": "🚨 Срочные перебои/обстрелы: ВКЛ",
        "toggle_emergency_off": "🔕 Срочные перебои/обстрелы: ВЫКЛ",
        "toggle_pause_resume": "▶️ Возобновить уведомления",
        "toggle_pause_stop": "⏸ Пауза уведомлений",
        "btn_change_queue": "🔀 Сменить очередь",
        "settings_text": (
            "⚙️ <b>Настройки уведомлений</b>\n\n"
            "• Очередь: <b>{q}</b>\n"
            "• Авто-предупреждения: <b>{status}</b>\n"
            "• Предупреждать за: <b>{lead} мин</b> до отключения\n"
            "• Сообщать о включении света: <b>{restore}</b>\n"
            "• Сообщать об изменении графика: <b>{change}</b>\n"
            "• Сообщать о перебоях (дроны/аварии): <b>{emergency}</b>\n"
            "• Язык интерфейса: <b>{lang_name}</b>\n\n"
            "Выберите интервал, язык или переключите параметры ниже:"
        ),
        "lang_updated": "🌐 Язык изменён на русский.",
        "today_title": "Сегодня",
        "tomorrow_title": "Завтра",
        "sched_unpublished": "📅 <b>{title} ({date}) — очередь {q}</b>\n\n⏳ График на этот день ещё не опубликован.",
        "sched_no_data": "📅 <b>{title} ({date}) — очередь {q}</b>\n\n⏳ Данных о графике на этот день пока нет.",
        "sched_header": "📅 <b>{title} ({date}) — очередь {q}</b>",
        "avail_no_gpv": "🟢 На этот день отключения (ГПВ) не запланированы.",
        "avail_cached": "ℹ️ Показан сохранённый график (новых обновлений пока не было).",
        "avail_failed": "⚠️ Не удалось обновить данные с сайта, показан последний известный график.",
        "sched_no_outages": "\n🟢 Отключений по графику на этот день нет.",
        "sched_maybe_suffix": " (возможно)",
        "sched_total_off": "\n⏱ Всего без света: <b>{total}</b>",
        "sched_updated_at": "🕒 Обновлено: {updated}",
        "now_no_data": "⚡ <b>Сейчас ({time}) — очередь {q}</b>\n\n⏳ График на сегодня пока недоступен.",
        "now_no_interval": "⚡ <b>Сейчас ({time}) — очередь {q}</b>\n\n⏳ Не удалось определить текущий интервал.",
        "now_off_unknown_end": (
            "🔴 <b>Света сейчас нет</b> (очередь {q})\n"
            "⏳ По текущим данным отключение как минимум до {end}."
        ),
        "now_off_planned": "Плановое отключение",
        "now_off_maybe": "Возможное отключение",
        "now_off_detail": (
            "🔴 <b>Света сейчас нет</b> ({kind}, очередь {q})\n"
            "🔌 Ожидаемое включение: {day_prefix}<b>{time}</b> (через {dur})"
        ),
        "now_on_clear": (
            "🟢 <b>Свет сейчас есть</b> (очередь {q})\n"
            "✅ По опубликованному графику отключений в ближайшее время не ожидается."
        ),
        "now_on_kind_off": "отключение",
        "now_on_kind_maybe": "возможное отключение",
        "now_on_detail": (
            "🟢 <b>Свет сейчас есть</b> (очередь {q})\n"
            "⚠️ Следующее {kind}: {day_prefix}<b>{start} – {end}</b> (через {dur})"
        ),
        "at_word": "в",
        "alert_tomorrow_published": "📢 <b>Опубликован график на завтра!</b>\n\n{body}",
        "alert_schedule_changed": "🔄 <b>Обновился график отключений!</b>\n\n{body}",
        "alert_pre_off": (
            "⚠️ <b>Предупреждение об отключении света!</b>\n"
            "Очередь <b>{q}</b>: отключение в <b>{start}</b> (через {mins}).\n"
            "🕒 Ориентировочно до <b>{end}</b> ({dur})."
        ),
        "alert_restore": (
            "🟢 <b>Время включения света!</b>\n"
            "По графику для очереди <b>{q}</b> электроснабжение должно возобновиться в <b>{time}</b>.{extra}"
        ),
        "alert_restore_next": "\n⚡ Следующее отключение по графику: {day_prefix}<b>{time}</b>.",
        "emergency_alert": (
            "🚨 <b>Срочное сообщение о свете ({channel}, {time})</b>\n\n"
            "{text}\n\n"
            "🔗 <a href='{url}'>Источник сообщения</a>"
        ),
        "incidents_empty": "🟢 За последние 24 часа срочных сообщений о перебоях/авариях в каналах @ProZaporizhzhia и @Zaporizhzhyaoblenergo_news не найдено.",
        "incidents_header": "🚨 <b>Последние сообщения о перебоях (24 ч):</b>\n",
        "incidents_link": "[ссылка]",
    },
    "en": {
        "btn_now": "⚡ Now",
        "btn_today": "📅 Today",
        "btn_tomorrow": "📆 Tomorrow",
        "btn_settings": "⚙️ Settings",
        "queue_btn": "Queue {q}",
        "queue_lookup_btn": "🔎 Find my queue (zoe.com.ua)",
        "choose_queue": "Select your power outage queue in Zaporizhzhia:",
        "need_queue": "Please select your queue first:",
        "queue_set": "✅ Queue set to <b>{q}</b>.",
        "queue_selected": (
            "✅ Selected queue <b>{q}</b>.\n"
            "You will be warned <b>{mins} min</b> before outages (change in /settings)."
        ),
        "start_intro": (
            "⚡ <b>Zaporizhzhia Power Outage Alert Bot (Zaporizhzhiaoblenergo)</b>\n\n"
            "I will automatically warn you before scheduled outages, notify you when power returns, "
            "alert on schedule updates, and forward urgent disruption reports (after explosions/drone attacks).\n\n"
        ),
        "start_has_queue": "Your current queue: <b>{q}</b>.\nUse the buttons below or choose a different queue:",
        "start_pick_queue": "To get started, choose your outage queue (e.g. <b>1.1</b>):",
        "menu_hint": "Quick menu is always available on the keyboard below 👇",
        "help_text": (
            "ℹ️ <b>Bot Commands</b>\n\n"
            "/now — current power status\n"
            "/today — today's outage schedule\n"
            "/tomorrow — tomorrow's outage schedule\n"
            "/incidents — recent urgent outage reports\n"
            "/queue — choose or change queue (1.1 – 6.2)\n"
            "/settings — warning lead time, language & options\n\n"
            "• Check queue by address: <a href='{zoe_url}'>zoe.com.ua/outage</a>\n"
            "• Official ZOE channel: <a href='{zoe_tg}'>ZOE Telegram</a>"
        ),
        "fetch_error": "⚠️ Could not fetch schedule data. Please try again later.",
        "min_short": "min",
        "hour_short": "h",
        "less_than_min": "less than a minute",
        "not_selected": "not selected",
        "yes": "yes",
        "no": "no",
        "status_paused": "⏸ paused",
        "status_active": "✅ active",
        "toggle_restore_on": "🔔 Power restore alerts: ON",
        "toggle_restore_off": "🔕 Power restore alerts: OFF",
        "toggle_change_on": "🔄 Schedule change alerts: ON",
        "toggle_change_off": "🔕 Schedule change alerts: OFF",
        "toggle_emergency_on": "🚨 Urgent outage/attack alerts: ON",
        "toggle_emergency_off": "🔕 Urgent outage/attack alerts: OFF",
        "toggle_pause_resume": "▶️ Resume notifications",
        "toggle_pause_stop": "⏸ Pause notifications",
        "btn_change_queue": "🔀 Change queue",
        "settings_text": (
            "⚙️ <b>Notification Settings</b>\n\n"
            "• Queue: <b>{q}</b>\n"
            "• Auto-alerts: <b>{status}</b>\n"
            "• Warn before outage: <b>{lead} min</b>\n"
            "• Notify on power restore: <b>{restore}</b>\n"
            "• Notify on schedule change: <b>{change}</b>\n"
            "• Urgent disruption alerts: <b>{emergency}</b>\n"
            "• Language: <b>{lang_name}</b>\n\n"
            "Choose lead time, language, or toggle options below:"
        ),
        "lang_updated": "🌐 Language changed to English.",
        "today_title": "Today",
        "tomorrow_title": "Tomorrow",
        "sched_unpublished": "📅 <b>{title} ({date}) — queue {q}</b>\n\n⏳ Schedule for this day is not published yet.",
        "sched_no_data": "📅 <b>{title} ({date}) — queue {q}</b>\n\n⏳ No schedule data available for this day yet.",
        "sched_header": "📅 <b>{title} ({date}) — queue {q}</b>",
        "avail_no_gpv": "🟢 No scheduled outages (GPV) for this day.",
        "avail_cached": "ℹ️ Showing saved schedule (no new updates yet).",
        "avail_failed": "⚠️ Failed to refresh from website, showing last known schedule.",
        "sched_no_outages": "\n🟢 No outages scheduled for this day.",
        "sched_maybe_suffix": " (possible)",
        "sched_total_off": "\n⏱ Total without power: <b>{total}</b>",
        "sched_updated_at": "🕒 Updated: {updated}",
        "now_no_data": "⚡ <b>Now ({time}) — queue {q}</b>\n\n⏳ Today's schedule is not available yet.",
        "now_no_interval": "⚡ <b>Now ({time}) — queue {q}</b>\n\n⏳ Could not determine current interval.",
        "now_off_unknown_end": (
            "🔴 <b>Power is currently OFF</b> (queue {q})\n"
            "⏳ According to current data, outage lasts at least until {end}."
        ),
        "now_off_planned": "Scheduled outage",
        "now_off_maybe": "Possible outage",
        "now_off_detail": (
            "🔴 <b>Power is currently OFF</b> ({kind}, queue {q})\n"
            "🔌 Expected restore: {day_prefix}<b>{time}</b> (in {dur})"
        ),
        "now_on_clear": (
            "🟢 <b>Power is currently ON</b> (queue {q})\n"
            "✅ No outages expected in the published schedule."
        ),
        "now_on_kind_off": "outage",
        "now_on_kind_maybe": "possible outage",
        "now_on_detail": (
            "🟢 <b>Power is currently ON</b> (queue {q})\n"
            "⚠️ Next {kind}: {day_prefix}<b>{start} – {end}</b> (in {dur})"
        ),
        "at_word": "at",
        "alert_tomorrow_published": "📢 <b>Tomorrow's schedule published!</b>\n\n{body}",
        "alert_schedule_changed": "🔄 <b>Outage schedule updated!</b>\n\n{body}",
        "alert_pre_off": (
            "⚠️ <b>Power outage warning!</b>\n"
            "Queue <b>{q}</b>: outage at <b>{start}</b> (in {mins}).\n"
            "🕒 Expected until <b>{end}</b> ({dur})."
        ),
        "alert_restore": (
            "🟢 <b>Power restore time!</b>\n"
            "According to schedule for queue <b>{q}</b>, power should return at <b>{time}</b>.{extra}"
        ),
        "alert_restore_next": "\n⚡ Next scheduled outage: {day_prefix}<b>{time}</b>.",
        "emergency_alert": (
            "🚨 <b>Urgent power report ({channel}, {time})</b>\n\n"
            "{text}\n\n"
            "🔗 <a href='{url}'>Source message</a>"
        ),
        "incidents_empty": "🟢 No urgent outage reports in @ProZaporizhzhia or @Zaporizhzhyaoblenergo_news over the last 24 hours.",
        "incidents_header": "🚨 <b>Recent urgent outage reports (24h):</b>\n",
        "incidents_link": "[link]",
    },
}

LANG_DISPLAY_NAMES = {
    "uk": "Українська 🇺🇦",
    "ru": "Русский 🇷🇺",
    "en": "English 🇬🇧",
}


def normalize_lang(lang: str | None) -> str:
    if lang in SUPPORTED_LANGS:
        return lang
    return DEFAULT_LANG


def t(lang: str | None, key: str, **kwargs: object) -> str:
    code = normalize_lang(lang)
    template = STRINGS[code][key]
    return template.format(**kwargs) if kwargs else template


def format_duration_localized(minutes: int, lang: str | None = DEFAULT_LANG) -> str:
    code = normalize_lang(lang)
    if minutes <= 0:
        return t(code, "less_than_min")
    hours, mins = divmod(minutes, 60)
    h_unit = t(code, "hour_short")
    m_unit = t(code, "min_short")
    parts: list[str] = []
    if hours:
        parts.append(f"{hours} {h_unit}")
    if mins:
        parts.append(f"{mins} {m_unit}")
    return " ".join(parts)


def format_hours_total_localized(minutes: int, lang: str | None = DEFAULT_LANG) -> str:
    code = normalize_lang(lang)
    hours = minutes / 60
    h_unit = t(code, "hour_short")
    if hours.is_integer():
        return f"{int(hours)} {h_unit}"
    return f"{hours:.1f} {h_unit}"
