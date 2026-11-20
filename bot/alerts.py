"""Instant alerts to the management Telegram group (ALERT_CHAT_ID).

Sent when a patient reports corruption (Q7 = Yes) or gives a very low rating.
Alerts never contain anything that identifies the patient.
"""

import logging
from html import escape

from aiogram import Bot

from .config import settings
from .db import Doctor

LOW_EMPATHY = 2  # Q1 at or below this triggers an alert
LOW_NPS = 3  # Q6 at or below this triggers an alert

LABELS = {
    "q2": {"full": "Toʻliq", "partial": "Qisman", "none": "Tushuntirmadi"},
    "q3": {"on_time": "Oʻz vaqtida", "waited_15_20": "15-20 daqiqa", "long_wait": "Uzoq kutdi"},
    "q4": {"enough": "Yetarli", "partial": "Qisman", "rushed": "Shoshilinch"},
    "q5": {"full": "Toʻliq qoniqdi", "partial": "Qisman", "not": "Qoniqmadi"},
}


def needs_alert(answers: dict) -> list[str]:
    reasons = []
    if answers.get("q7") == "yes":
        reasons.append("🚨 <b>KORRUPSIYA HAQIDA XABAR</b> (pul/sovgʻa talab qilingan yoki taklif qilingan)")
    if int(answers["q1"]) <= LOW_EMPATHY:
        reasons.append(f"⚠️ Past muomala bahosi: {answers['q1']}/5")
    if int(answers["q6"]) <= LOW_NPS:
        reasons.append(f"⚠️ Past tavsiya bahosi: {answers['q6']}/10")
    return reasons


async def send_alert(bot: Bot, doctor: Doctor, answers: dict) -> None:
    if not settings.alert_chat_id:
        return
    reasons = needs_alert(answers)
    if not reasons:
        return
    lines = [
        *reasons,
        "",
        f"👨‍⚕️ <b>{escape(doctor.full_name)}</b>",
        f"🏥 {escape(doctor.specialty_uz)}",
        "",
        f"🤝 Muomala: {answers['q1']}/5",
        f"💬 Tushuntirish: {LABELS['q2'][answers['q2']]}",
        f"⏰ Vaqt: {LABELS['q3'][answers['q3']]}",
        f"🩺 Koʻrik: {LABELS['q4'][answers['q4']]}",
        f"💊 Natija: {LABELS['q5'][answers['q5']]}",
        f"👍 Tavsiya: {answers['q6']}/10",
        f"🛡 Korrupsiya: {'Ha' if answers['q7'] == 'yes' else 'Yoʻq'}",
    ]
    if answers.get("q8"):
        lines += ["", f"✍️ <i>{escape(answers['q8'])}</i>"]
    try:
        await bot.send_message(settings.alert_chat_id, "\n".join(lines))
    except Exception:  # an alert problem must never break the patient's survey
        logging.exception("Could not send alert to ALERT_CHAT_ID=%s", settings.alert_chat_id)
