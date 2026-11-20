"""All user-facing texts in Uzbek, Russian and English.

Answer *codes* (the first item of every option) are what goes into the
database, so analytics does not depend on the language the patient chose.
Edit the labels freely, but do not change the codes once real data exists.
"""

LANGS = ("uz", "ru", "en")

LANG_BUTTONS = {
    "uz": "🇺🇿 Oʻzbekcha",
    "ru": "🇷🇺 Русский",
    "en": "🇬🇧 English",
}

ROOM = {"uz": "\n🚪 {room}-kabinet", "ru": "\n🚪 Кабинет {room}", "en": "\n🚪 Room {room}"}

UI = {
    "choose_lang": {
        "all": "🌐 Tilni tanlang / Выберите язык / Choose a language",
    },
    "no_doctor": {
        "all": (
            "Iltimos, shifokor xonasi eshigidagi QR kodni skanerlang.\n"
            "Пожалуйста, отсканируйте QR-код на двери кабинета врача.\n"
            "Please scan the QR code on the doctor's office door."
        ),
    },
    "intro": {
        "uz": "👋 Assalomu alaykum!\n\n👨‍⚕️ <b>{name}</b>\n🏥 {specialty}{room}\n\n📝 8 ta qisqa savol, 1 daqiqa\n🔒 Javoblaringiz anonim",
        "ru": "👋 Здравствуйте!\n\n👨‍⚕️ <b>{name}</b>\n🏥 {specialty}{room}\n\n📝 8 коротких вопросов, 1 минута\n🔒 Ваши ответы анонимны",
        "en": "👋 Hello!\n\n👨‍⚕️ <b>{name}</b>\n🏥 {specialty}{room}\n\n📝 8 short questions, 1 minute\n🔒 Your answers are anonymous",
    },
    "already_today": {
        "uz": "Siz bugun ushbu shifokorni allaqachon baholagansiz. Rahmat! Ertaga yana baho berishingiz mumkin.",
        "ru": "Вы уже оценили этого врача сегодня. Спасибо! Повторно оценить можно завтра.",
        "en": "You have already rated this doctor today. Thank you! You can rate again tomorrow.",
        "all": (
            "Siz bugun ushbu shifokorni allaqachon baholagansiz. Rahmat!\n"
            "Вы уже оценили этого врача сегодня. Спасибо!\n"
            "You have already rated this doctor today. Thank you!"
        ),
    },
    "skip": {
        "uz": "Oʻtkazib yuborish ➡️",
        "ru": "Пропустить ➡️",
        "en": "Skip ➡️",
    },
    "use_buttons": {
        "uz": "Iltimos, yuqoridagi tugmalardan birini tanlang.",
        "ru": "Пожалуйста, выберите один из вариантов кнопками выше.",
        "en": "Please choose one of the buttons above.",
    },
    "comment_too_long": {
        "uz": "Izoh juda uzun. Iltimos, {max} belgidan oshirmang.",
        "ru": "Комментарий слишком длинный. Пожалуйста, не более {max} символов.",
        "en": "Your comment is too long. Please keep it under {max} characters.",
    },
    "thanks": {
        "uz": "🙏 Rahmat! Fikringiz qabul qilindi.\n💙 Sogʻ boʻling!",
        "ru": "🙏 Спасибо! Ваш отзыв принят.\n💙 Будьте здоровы!",
        "en": "🙏 Thank you! Your feedback has been received.\n💙 Stay healthy!",
    },
    "expired": {
        "all": (
            "Soʻrovnoma muddati tugadi. QR kodni qayta skanerlang.\n"
            "Сессия опроса истекла. Отсканируйте QR-код ещё раз.\n"
            "This survey session has expired. Please scan the QR code again."
        ),
    },
    "progress": {
        "uz": "Savol {n}/{total}",
        "ru": "Вопрос {n}/{total}",
        "en": "Question {n}/{total}",
    },
}


def ui(key: str, lang: str | None = None, **kw) -> str:
    entry = UI[key]
    text = entry.get(lang) if lang else None
    text = text or entry.get("all") or entry["uz"]
    return text.format(**kw) if kw else text


# Each question: key, title, text, options [(code, {lang: label})], buttons per row.
QUESTIONS = [
    {
        "key": "q1",
        "title": {
            "uz": "Muomala va eʼtibor",
            "ru": "Вежливость и внимание",
            "en": "Courtesy and attention",
        },
        "text": {
            "uz": "Shifokor sizga qanchalik xushmuomala va eʼtiborli boʻldi?",
            "ru": "Насколько вежливым и внимательным был к вам врач?",
            "en": "How courteous and attentive was the doctor towards you?",
        },
        "options": [
            ("5", {"uz": "🤩 Juda yaxshi", "ru": "🤩 Очень хорошо", "en": "🤩 Very good"}),
            ("4", {"uz": "🙂 Yaxshi", "ru": "🙂 Хорошо", "en": "🙂 Good"}),
            ("3", {"uz": "😐 Qoniqarli", "ru": "😐 Удовлетворительно", "en": "😐 Satisfactory"}),
            ("2", {"uz": "🙁 Yomon", "ru": "🙁 Плохо", "en": "🙁 Poor"}),
            ("1", {"uz": "😠 Juda yomon", "ru": "😠 Очень плохо", "en": "😠 Very poor"}),
        ],
        "per_row": 1,
    },
    {
        "key": "q2",
        "title": {
            "uz": "Davolash va tashxisni tushuntirish",
            "ru": "Объяснение диагноза и лечения",
            "en": "Explaining the diagnosis and treatment",
        },
        "text": {
            "uz": "Shifokor kasallik, belgilangan davolash va dorilarni sizga tushunarli qilib tushuntirib berdimi?",
            "ru": "Объяснил ли вам врач понятным языком заболевание, назначенное лечение и лекарства?",
            "en": "Did the doctor explain the illness, the prescribed treatment and the medicines in a way you could understand?",
        },
        "options": [
            ("full", {"uz": "✅ Toʻliq va aniq tushuntirdi", "ru": "✅ Объяснил полностью и ясно", "en": "✅ Fully and clearly"}),
            ("partial", {"uz": "🟡 Qisman tushuntirdi", "ru": "🟡 Объяснил частично", "en": "🟡 Partially"}),
            ("none", {"uz": "❌ Tushuntirmadi", "ru": "❌ Не объяснил", "en": "❌ Did not explain"}),
        ],
        "per_row": 1,
    },
    {
        "key": "q3",
        "title": {
            "uz": "Qabul vaqtiga rioya qilinishi",
            "ru": "Соблюдение времени приёма",
            "en": "Keeping to the appointment time",
        },
        "text": {
            "uz": "Belgilangan vaqtda qabulga kira oldingizmi (navbat kutish vaqti sizni qoniqtirdimi)?",
            "ru": "Смогли ли вы попасть на приём в назначенное время (устроило ли вас время ожидания в очереди)?",
            "en": "Were you seen at your scheduled time (were you satisfied with the waiting time)?",
        },
        "options": [
            ("on_time", {"uz": "⚡ Tez va oʻz vaqtida", "ru": "⚡ Быстро и вовремя", "en": "⚡ Quickly and on time"}),
            ("waited_15_20", {"uz": "⏳ 15-20 daqiqa kutdim", "ru": "⏳ Ждал(а) 15-20 минут", "en": "⏳ Waited 15-20 minutes"}),
            ("long_wait", {"uz": "🐢 Uzoq vaqt kutib qoldim", "ru": "🐢 Пришлось долго ждать", "en": "🐢 Waited a long time"}),
        ],
        "per_row": 1,
    },
    {
        "key": "q4",
        "title": {
            "uz": "Koʻrikning atroflicha oʻtkazilishi",
            "ru": "Тщательность осмотра",
            "en": "Thoroughness of the examination",
        },
        "text": {
            "uz": "Shifokor koʻrigi va sizga ajratilgan vaqt yetarli boʻldi deb hisoblaysizmi?",
            "ru": "Считаете ли вы, что осмотр врача и уделённое вам время были достаточными?",
            "en": "Do you feel the doctor's examination and the time given to you were sufficient?",
        },
        "options": [
            ("enough", {"uz": "✅ Ha, toʻliq yetarli", "ru": "✅ Да, вполне достаточно", "en": "✅ Yes, fully sufficient"}),
            ("partial", {"uz": "🟡 Qisman yetarli", "ru": "🟡 Частично достаточно", "en": "🟡 Partly sufficient"}),
            ("rushed", {"uz": "❌ Yoʻq, shoshilinch boʻldi", "ru": "❌ Нет, всё было в спешке", "en": "❌ No, it was rushed"}),
        ],
        "per_row": 1,
    },
    {
        "key": "q5",
        "title": {
            "uz": "Tibbiy yordam natijasi",
            "ru": "Результат медицинской помощи",
            "en": "Outcome of the medical care",
        },
        "text": {
            "uz": "Berilgan davolash va koʻrsatilgan tibbiy xizmat natijasidan qoniqdingizmi?",
            "ru": "Удовлетворены ли вы назначенным лечением и результатом оказанной медицинской помощи?",
            "en": "Are you satisfied with the treatment given and the result of the medical service?",
        },
        "options": [
            ("full", {"uz": "😊 Toʻliq qoniqdim", "ru": "😊 Полностью удовлетворён(а)", "en": "😊 Fully satisfied"}),
            ("partial", {"uz": "😐 Qisman", "ru": "😐 Частично", "en": "😐 Partially"}),
            ("not", {"uz": "😞 Qoniqmadim", "ru": "😞 Не удовлетворён(а)", "en": "😞 Not satisfied"}),
        ],
        "per_row": 1,
    },
    {
        "key": "q6",
        "title": {
            "uz": "Tavsiya etish koʻrsatkichi",
            "ru": "Готовность рекомендовать",
            "en": "Likelihood to recommend",
        },
        "text": {
            "uz": "Ushbu shifokorni yaqinlaringiz va tanishlaringizga tavsiya etasizmi?",
            "ru": "Порекомендуете ли вы этого врача родным и знакомым?",
            "en": "Would you recommend this doctor to your family and friends?",
        },
        "options": [(str(i), {lang: {1: "1 👎", 10: "10 👍"}.get(i, str(i)) for lang in ("uz", "ru", "en")}) for i in range(1, 11)],
        "per_row": 5,
    },
    {
        "key": "q7",
        "title": {
            "uz": "Korrupsion holatlar va shaffoflik",
            "ru": "Коррупционные случаи и прозрачность",
            "en": "Corruption and transparency",
        },
        "text": {
            "uz": "Shifokor yoki tibbiyot xodimlari tomonidan tibbiy xizmat ko‘rsatish jarayonida Sizdan qo‘shimcha pul, "
            "sovg‘a yoki boshqa moddiy manfaat talab qilindimi yoki shunday taklif bildirildimi?",
            "ru": "Требовали ли у вас врач или медицинский персонал в процессе оказания медицинской помощи дополнительные "
            "деньги, подарок или иную материальную выгоду, или предлагали ли вам это сделать?",
            "en": "During your medical care, did the doctor or medical staff demand, or suggest that you give, extra money, "
            "a gift or any other material benefit?",
        },
        "options": [
            ("yes", {"uz": "⚠️ Ha", "ru": "⚠️ Да", "en": "⚠️ Yes"}),
            ("no", {"uz": "✅ Yoʻq", "ru": "✅ Нет", "en": "✅ No"}),
        ],
        "per_row": 2,
    },
    {
        "key": "q8",
        "title": {
            "uz": "Ixtiyoriy izoh va takliflar",
            "ru": "Комментарии и предложения (по желанию)",
            "en": "Comments and suggestions (optional)",
        },
        "text": {
            "uz": "Shifokor xizmatini yanada yaxshilash boʻyicha fikr yoki taklifingiz",
            "ru": "Ваши замечания или предложения по улучшению работы врача",
            "en": "Your comments or suggestions for improving the doctor's service",
        },
        "options": [],  # free text + Skip button
        "per_row": 1,
    },
]

TOTAL = len(QUESTIONS)


QUESTION_EMOJI = {"q1": "🤝", "q2": "💬", "q3": "⏰", "q4": "🩺", "q5": "💊", "q6": "👍", "q7": "🛡", "q8": "✍️"}


def question_text(index: int, lang: str) -> str:
    q = QUESTIONS[index]
    return f"{QUESTION_EMOJI[q['key']]} <b>{q['text'][lang]}</b>"
