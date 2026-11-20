"""Turns raw responses into the numbers shown on the dashboard.

Aggregation is done in Python over the filtered rows. That keeps the logic
identical on SQLite and PostgreSQL and is fast enough for hundreds of
thousands of responses.
"""

from collections import Counter, defaultdict
from datetime import date, datetime, time, timedelta, timezone

from sqlalchemy import select

from bot.alerts import LOW_EMPATHY, LOW_NPS
from bot.config import settings
from bot.db import Doctor, Response, Session

# Which answer counts as the "good" one for each multiple-choice question.
POSITIVE = {
    "q2_communication": "full",
    "q3_timeliness": "on_time",
    "q4_thoroughness": "enough",
    "q5_outcome": "full",
}

OPTION_ORDER = {
    "q1_empathy": [5, 4, 3, 2, 1],
    "q2_communication": ["full", "partial", "none"],
    "q3_timeliness": ["on_time", "waited_15_20", "long_wait"],
    "q4_thoroughness": ["enough", "partial", "rushed"],
    "q5_outcome": ["full", "partial", "not"],
    "q6_nps": list(range(10, 0, -1)),
    "q7_corruption": [True, False],
}


def to_utc_bounds(date_from: date | None, date_to: date | None) -> tuple[datetime | None, datetime | None]:
    """Local (Tashkent) calendar dates -> UTC datetimes, end exclusive."""
    start = end = None
    if date_from:
        start = datetime.combine(date_from, time.min, settings.tz).astimezone(timezone.utc)
    if date_to:
        end = datetime.combine(date_to + timedelta(days=1), time.min, settings.tz).astimezone(timezone.utc)
    return start, end


def local_dt(dt: datetime) -> datetime:
    if dt.tzinfo is None:  # SQLite returns naive UTC
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(settings.tz)


async def load(date_from=None, date_to=None, doctor_id=None, specialty=None, department=None):
    start, end = to_utc_bounds(date_from, date_to)
    q = select(Response, Doctor).join(Doctor)
    if start:
        q = q.where(Response.created_at >= start)
    if end:
        q = q.where(Response.created_at < end)
    if doctor_id:
        q = q.where(Response.doctor_id == doctor_id)
    if specialty:
        q = q.where(Doctor.specialty_uz == specialty)
    if department:
        q = q.where(Doctor.department == department)
    q = q.order_by(Response.created_at.desc())
    async with Session() as s:
        return (await s.execute(q)).all()


def pct(part: int, total: int) -> float | None:
    return round(100 * part / total, 1) if total else None


def metrics(responses: list[Response]) -> dict:
    n = len(responses)
    if not n:
        return {"count": 0, "quality": None, "csat": None, "long_wait_pct": None, "alerts": 0, "empathy_avg": None, "nps": None, "promoters": None, "detractors": None,
                "communication_pct": None, "on_time_pct": None, "thorough_pct": None,
                "satisfied_pct": None, "corruption_count": 0, "corruption_pct": None, "comments": 0}
    # NPS on the 1-10 scale: promoters 9-10, detractors 1-6, passives 7-8.
    promoters = sum(r.q6_nps >= 9 for r in responses)
    detractors = sum(r.q6_nps <= 6 for r in responses)
    corruption = sum(r.q7_corruption for r in responses)
    # HCAHPS-style "top-box" quality index: share of best possible answers
    # across Q1-Q5, as a percentage. This is the main KPI per doctor.
    top_box = sum(
        (r.q1_empathy == 5) + (r.q2_communication == "full") + (r.q3_timeliness == "on_time")
        + (r.q4_thoroughness == "enough") + (r.q5_outcome == "full")
        for r in responses
    )
    satisfied = sum(r.q5_outcome == "full" for r in responses)
    return {
        "count": n,
        "quality": round(100 * top_box / (5 * n), 1),
        "csat": pct(satisfied, n),  # CSAT: share fully satisfied with the outcome (Q5)
        "long_wait_pct": pct(sum(r.q3_timeliness == "long_wait" for r in responses), n),
        "alerts": sum(is_alert(r) for r in responses),
        "empathy_avg": round(sum(r.q1_empathy for r in responses) / n, 2),
        "nps": round(100 * (promoters - detractors) / n),
        "promoters": pct(promoters, n),
        "detractors": pct(detractors, n),
        "communication_pct": pct(sum(r.q2_communication == "full" for r in responses), n),
        "on_time_pct": pct(sum(r.q3_timeliness == "on_time" for r in responses), n),
        "thorough_pct": pct(sum(r.q4_thoroughness == "enough" for r in responses), n),
        "satisfied_pct": pct(sum(r.q5_outcome == "full" for r in responses), n),
        "corruption_count": corruption,
        "corruption_pct": pct(corruption, n),
        "comments": sum(bool(r.q8_comment) for r in responses),
    }


def is_alert(r: Response) -> bool:
    """Same rule as the Telegram alerts: corruption or a very low rating."""
    return bool(r.q7_corruption) or r.q1_empathy <= LOW_EMPATHY or r.q6_nps <= LOW_NPS


def breakdown(responses: list[Response]) -> dict:
    out = {}
    for field, order in OPTION_ORDER.items():
        c = Counter(getattr(r, field) for r in responses)
        out[field] = [{"value": v, "count": c.get(v, 0)} for v in order]
    return out


def timeseries(responses: list[Response], date_from: date | None, date_to: date | None) -> list[dict]:
    """Daily (or weekly for long ranges) counts, average empathy and NPS."""
    if not responses:
        return []
    days = [local_dt(r.created_at).date() for r in responses]
    first = date_from or min(days)
    last = date_to or max(max(days), datetime.now(settings.tz).date())
    weekly = (last - first).days > 62

    def bucket(d: date) -> date:
        return d - timedelta(days=d.weekday()) if weekly else d

    groups: dict[date, list[Response]] = defaultdict(list)
    for d, r in zip(days, responses):
        groups[bucket(d)].append(r)

    out, cur, step = [], bucket(first), timedelta(days=7 if weekly else 1)
    while cur <= last:
        m = metrics(groups.get(cur, []))
        out.append({"date": cur.isoformat(), "count": m["count"], "empathy_avg": m["empathy_avg"], "nps": m["nps"],
                    "quality": m["quality"],
                    "corruption": m["corruption_count"]})
        cur += step
    return out


def photo_exists(d: Doctor) -> bool:
    from pathlib import Path

    from bot.config import BASE_DIR
    if not d.photo_path:
        return False
    path = Path(d.photo_path)
    return (path if path.is_absolute() else BASE_DIR / path).is_file()


def doctor_dict(d: Doctor) -> dict:
    return {"id": d.id, "name": d.full_name, "specialty": d.specialty_uz, "specialty_ru": d.specialty_ru,
            "department": d.department, "room": d.room,
            "specialty_en": d.specialty_en, "code": d.code, "photo": photo_exists(d)}


def response_dict(r: Response, d: Doctor) -> dict:
    return {
        "id": r.id,
        "created_at": local_dt(r.created_at).strftime("%Y-%m-%d %H:%M"),
        "doctor_id": d.id,
        "doctor": d.full_name,
        "specialty": d.specialty_uz,
        "department": d.department,
        "room": d.room,
        "alert": is_alert(r),
        "language": r.language,
        "q1_empathy": r.q1_empathy,
        "q2_communication": r.q2_communication,
        "q3_timeliness": r.q3_timeliness,
        "q4_thoroughness": r.q4_thoroughness,
        "q5_outcome": r.q5_outcome,
        "q6_nps": r.q6_nps,
        "q7_corruption": r.q7_corruption,
        "q8_comment": r.q8_comment,
    }


async def all_doctors() -> list[Doctor]:
    async with Session() as s:
        return list((await s.scalars(select(Doctor).order_by(Doctor.last_name, Doctor.first_name))).all())


def by_department(rows) -> list[dict]:
    groups: dict[str, list[Response]] = defaultdict(list)
    for r, d in rows:
        groups[d.department or "—"].append(r)
    out = []
    for name, rs in groups.items():
        m = metrics(rs)
        c = Counter(r.q3_timeliness for r in rs)
        out.append({"department": name, **m,
                    "wait": {k: c.get(k, 0) for k in OPTION_ORDER["q3_timeliness"]}})
    return sorted(out, key=lambda x: -x["count"])
