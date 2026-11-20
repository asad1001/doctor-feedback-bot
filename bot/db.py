"""Database models.

Two ideas drive the design:

* ``responses`` holds one row per finished survey, with every answer in its own
  column and stored as a language-independent code, so the analytics dashboard
  can aggregate across Uzbek, Russian and English answers directly in SQL.
* ``responses`` contains NO patient identifier. The once-per-day spam check
  lives in a separate ``submission_locks`` table that only stores a salted
  hash, the doctor and the date, and old rows are deleted every day. So a
  response can never be traced back to a Telegram account.
"""

import hashlib
import hmac
import secrets
from datetime import date, datetime, timezone

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    SmallInteger,
    String,
    Text,
    delete,
    select,
)
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

from .config import settings


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def new_doctor_code() -> str:
    # Goes into the QR deep link (t.me/<bot>?start=<code>). Random, so nobody
    # can guess other doctors' links by counting 1, 2, 3...
    return secrets.token_urlsafe(6).replace("-", "x").replace("_", "y")


class Base(DeclarativeBase):
    pass


class Doctor(Base):
    __tablename__ = "doctors"

    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(32), unique=True, index=True, default=new_doctor_code)
    last_name: Mapped[str] = mapped_column(String(100))
    first_name: Mapped[str] = mapped_column(String(100))
    patronymic: Mapped[str | None] = mapped_column(String(100))
    specialty_uz: Mapped[str] = mapped_column(String(150))
    specialty_ru: Mapped[str | None] = mapped_column(String(150))
    specialty_en: Mapped[str | None] = mapped_column(String(150))
    department: Mapped[str | None] = mapped_column(String(150), index=True)  # boʻlim
    room: Mapped[str | None] = mapped_column(String(30))  # kabinet raqami
    photo_path: Mapped[str | None] = mapped_column(String(255))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    responses: Mapped[list["Response"]] = relationship(back_populates="doctor")

    @property
    def full_name(self) -> str:
        return " ".join(p for p in (self.last_name, self.first_name, self.patronymic) if p)

    def specialty(self, lang: str) -> str:
        return getattr(self, f"specialty_{lang}", None) or self.specialty_uz


class Response(Base):
    __tablename__ = "responses"

    id: Mapped[int] = mapped_column(primary_key=True)
    doctor_id: Mapped[int] = mapped_column(ForeignKey("doctors.id"), index=True)
    language: Mapped[str] = mapped_column(String(2))  # uz / ru / en
    q1_empathy: Mapped[int] = mapped_column(SmallInteger)  # 1..5
    q2_communication: Mapped[str] = mapped_column(String(16))  # full / partial / none
    q3_timeliness: Mapped[str] = mapped_column(String(16))  # on_time / waited_15_20 / long_wait
    q4_thoroughness: Mapped[str] = mapped_column(String(16))  # enough / partial / rushed
    q5_outcome: Mapped[str] = mapped_column(String(16))  # full / partial / not
    q6_nps: Mapped[int] = mapped_column(SmallInteger)  # 1..10
    q7_corruption: Mapped[bool] = mapped_column(Boolean)  # True = money/gift was asked or offered
    q8_comment: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)

    doctor: Mapped[Doctor] = relationship(back_populates="responses")


class SubmissionLock(Base):
    """One row = "this (anonymous) person already rated this doctor today"."""

    __tablename__ = "submission_locks"

    user_hash: Mapped[str] = mapped_column(String(64), primary_key=True)
    doctor_id: Mapped[int] = mapped_column(ForeignKey("doctors.id"), primary_key=True)
    day: Mapped[date] = mapped_column(Date, primary_key=True, index=True)


engine = create_async_engine(settings.database_url)
Session = async_sessionmaker(engine, expire_on_commit=False)


def _add_missing_columns(sync_conn) -> None:
    """Tiny migration: add columns introduced after the first release."""
    from sqlalchemy import inspect, text

    insp = inspect(sync_conn)
    for table in Base.metadata.sorted_tables:
        if not insp.has_table(table.name):
            continue
        existing = {c["name"] for c in insp.get_columns(table.name)}
        for col in table.columns:
            if col.name not in existing:
                col_type = col.type.compile(dialect=sync_conn.dialect)
                sync_conn.execute(text(f'ALTER TABLE {table.name} ADD COLUMN {col.name} {col_type}'))


async def init_db() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        await conn.run_sync(_add_missing_columns)


def user_hash(telegram_user_id: int) -> str:
    return hmac.new(settings.anon_salt.encode(), str(telegram_user_id).encode(), hashlib.sha256).hexdigest()


def today_local() -> date:
    return datetime.now(settings.tz).date()


async def get_doctor_by_code(code: str) -> Doctor | None:
    async with Session() as s:
        return await s.scalar(select(Doctor).where(Doctor.code == code, Doctor.is_active.is_(True)))


async def get_doctor(doctor_id: int) -> Doctor | None:
    async with Session() as s:
        return await s.get(Doctor, doctor_id)


async def already_submitted_today(telegram_user_id: int, doctor_id: int) -> bool:
    async with Session() as s:
        lock = await s.get(SubmissionLock, (user_hash(telegram_user_id), doctor_id, today_local()))
        return lock is not None


async def save_response(telegram_user_id: int, doctor_id: int, language: str, answers: dict) -> bool:
    """Save a finished survey. Returns False if this person already rated this doctor today."""
    today = today_local()
    async with Session() as s:
        try:
            async with s.begin():
                # Forget yesterday's locks so no long-lived trace remains.
                await s.execute(delete(SubmissionLock).where(SubmissionLock.day < today))
                s.add(SubmissionLock(user_hash=user_hash(telegram_user_id), doctor_id=doctor_id, day=today))
                s.add(
                    Response(
                        doctor_id=doctor_id,
                        language=language,
                        q1_empathy=int(answers["q1"]),
                        q2_communication=answers["q2"],
                        q3_timeliness=answers["q3"],
                        q4_thoroughness=answers["q4"],
                        q5_outcome=answers["q5"],
                        q6_nps=int(answers["q6"]),
                        q7_corruption=answers["q7"] == "yes",
                        q8_comment=answers.get("q8"),
                    )
                )
        except IntegrityError:
            return False
    return True
