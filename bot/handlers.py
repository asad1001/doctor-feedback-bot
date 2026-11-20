from html import escape
from pathlib import Path

from aiogram import F, Router
from aiogram.filters import Command, CommandObject, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import (
    CallbackQuery,
    FSInputFile,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
)

from . import db
from .alerts import send_alert
from .config import BASE_DIR
from .texts import LANG_BUTTONS, LANGS, ROOM, QUESTIONS, TOTAL, question_text, ui

router = Router()

MAX_COMMENT = 1000
COMMENT_INDEX = TOTAL - 1  # Q8 is free text


class Survey(StatesGroup):
    choosing_lang = State()
    answering = State()  # Q1..Q7, button answers
    commenting = State()  # Q8, free text or Skip


def lang_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text=label, callback_data=f"lang:{code}")] for code, label in LANG_BUTTONS.items()]
    )


def question_keyboard(index: int, lang: str) -> InlineKeyboardMarkup:
    q = QUESTIONS[index]
    if index == COMMENT_INDEX:
        return InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text=ui("skip", lang), callback_data="skip")]])
    buttons = [InlineKeyboardButton(text=label[lang], callback_data=f"ans:{index}:{code}") for code, label in q["options"]]
    per_row = q["per_row"]
    return InlineKeyboardMarkup(inline_keyboard=[buttons[i : i + per_row] for i in range(0, len(buttons), per_row)])


# ---------------------------------------------------------------- entry point


@router.message(Command("chatid"), F.chat.type.in_({"group", "supergroup"}))
async def chat_id(message: Message) -> None:
    """Send /chatid inside the management group to learn the ALERT_CHAT_ID value."""
    await message.answer(f"ALERT_CHAT_ID={message.chat.id}")


@router.message(F.chat.type.in_({"group", "supergroup", "channel"}))
async def ignore_groups(message: Message) -> None:
    pass  # the survey only runs in private chats


@router.message(CommandStart())
async def start(message: Message, command: CommandObject, state: FSMContext) -> None:
    await state.clear()
    code = (command.args or "").strip()
    doctor = await db.get_doctor_by_code(code) if code else None
    if doctor is None:
        await message.answer(ui("no_doctor"))
        return
    if await db.already_submitted_today(message.from_user.id, doctor.id):
        await message.answer(ui("already_today"))
        return
    await state.set_state(Survey.choosing_lang)
    await state.update_data(doctor_id=doctor.id, answers={})
    await message.answer(ui("choose_lang"), reply_markup=lang_keyboard())


@router.callback_query(Survey.choosing_lang, F.data.startswith("lang:"))
async def choose_lang(call: CallbackQuery, state: FSMContext) -> None:
    lang = call.data.split(":", 1)[1]
    if lang not in LANGS:
        await call.answer()
        return
    data = await state.get_data()
    doctor = await db.get_doctor(data["doctor_id"])
    if doctor is None:
        await state.clear()
        await call.message.edit_text(ui("no_doctor"))
        await call.answer()
        return

    await state.update_data(lang=lang, step=0)
    await state.set_state(Survey.answering)
    room = ROOM[lang].format(room=escape(doctor.room)) if doctor.room else ""
    intro = ui("intro", lang, name=escape(doctor.full_name), specialty=escape(doctor.specialty(lang)), room=room)

    photo = Path(doctor.photo_path) if doctor.photo_path else None
    if photo and not photo.is_absolute():
        photo = BASE_DIR / photo
    if photo and photo.is_file():
        await call.message.delete()
        await call.message.answer_photo(FSInputFile(photo), caption=intro)
    else:
        await call.message.edit_text(intro)

    await call.message.answer(question_text(0, lang), reply_markup=question_keyboard(0, lang))
    await call.answer()


# ------------------------------------------------------------- button answers


@router.callback_query(Survey.answering, F.data.startswith("ans:"))
async def answer(call: CallbackQuery, state: FSMContext) -> None:
    _, idx, code = call.data.split(":", 2)
    data = await state.get_data()
    step, lang = data["step"], data["lang"]
    q = QUESTIONS[step]
    # Ignore taps on old messages or forged callback data.
    if int(idx) != step or code not in {c for c, _ in q["options"]}:
        await call.answer()
        return

    answers = data["answers"] | {q["key"]: code}
    step += 1
    await state.update_data(answers=answers, step=step)
    if step == COMMENT_INDEX:
        await state.set_state(Survey.commenting)
        await state.update_data(comment_msg_id=call.message.message_id)
    await call.message.edit_text(question_text(step, lang), reply_markup=question_keyboard(step, lang))
    await call.answer()


# ------------------------------------------------------------- Q8: free text


@router.callback_query(Survey.commenting, F.data == "skip")
async def skip_comment(call: CallbackQuery, state: FSMContext) -> None:
    await call.message.edit_reply_markup(reply_markup=None)
    await finish(call.message, call.from_user.id, state, comment=None)
    await call.answer()


@router.message(Survey.commenting, F.text)
async def comment(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    text = message.text.strip()
    if text.startswith("/"):
        return
    if len(text) > MAX_COMMENT:
        await message.answer(ui("comment_too_long", data["lang"], max=MAX_COMMENT))
        return
    try:  # remove the Skip button from the question
        await message.bot.edit_message_reply_markup(chat_id=message.chat.id, message_id=data["comment_msg_id"], reply_markup=None)
    except Exception:
        pass
    await finish(message, message.from_user.id, state, comment=text or None)


async def finish(message: Message, user_id: int, state: FSMContext, comment: str | None) -> None:
    data = await state.get_data()
    lang = data["lang"]
    answers = data["answers"] | {"q8": comment}
    await state.clear()
    saved = await db.save_response(user_id, data["doctor_id"], lang, answers)
    await message.answer(ui("thanks" if saved else "already_today", lang))
    if saved:
        doctor = await db.get_doctor(data["doctor_id"])
        if doctor:
            await send_alert(message.bot, doctor, answers)


# ------------------------------------------------------------------ fallbacks


@router.message(Survey.choosing_lang)
@router.message(Survey.answering)
@router.message(Survey.commenting)
async def use_buttons(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    await message.answer(ui("use_buttons", data.get("lang")) if data.get("lang") else ui("choose_lang"))


@router.callback_query()
async def stale_button(call: CallbackQuery) -> None:
    # A button from a finished or expired survey (e.g. after a bot restart).
    await call.answer(ui("expired"), show_alert=True)


@router.message()
async def no_survey(message: Message) -> None:
    await message.answer(ui("no_doctor"))
