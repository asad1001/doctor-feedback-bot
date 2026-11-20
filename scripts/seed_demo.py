"""Fill the database with DEMO doctors and responses, to try the dashboard.

    python scripts/seed_demo.py           add 12 demo doctors + ~1500 responses (last 120 days)
    python scripts/seed_demo.py --remove  delete all demo doctors and their responses

Demo doctors have codes starting with "demo", so they never mix with real ones
and --remove deletes only them. Remove the demo data before going live.
"""

import asyncio
import random
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import delete, select  # noqa: E402

from bot.db import Doctor, Response, Session, init_db  # noqa: E402

DEPARTMENTS = {'Pediatr': 'Pediatriya boʻlimi', 'Bolalar kardiologi': 'Kardiologiya boʻlimi', 'Bolalar nevrologi': 'Nevrologiya boʻlimi', 'Bolalar endokrinologi': 'Endokrinologiya boʻlimi', 'Bolalar jarrohi': 'Jarrohlik boʻlimi', 'LOR (otorinolaringolog)': 'Konsultativ poliklinika', 'Bolalar gastroenterologi': 'Gastroenterologiya boʻlimi', 'Bolalar ortopedi': 'Jarrohlik boʻlimi', 'Bolalar allergologi': 'Konsultativ poliklinika', 'Bolalar oftalmologi': 'Konsultativ poliklinika'}

DEMO = [
    ("Aliyeva", "Kamola", "Rustamovna", "Pediatr", "Педиатр", "Pediatrician", 0.92),
    ("Hasanov", "Aziz", "Baxtiyorovich", "Bolalar kardiologi", "Детский кардиолог", "Pediatric cardiologist", 0.85),
    ("Yusupova", "Malika", "Shavkatovna", "Pediatr", "Педиатр", "Pediatrician", 0.78),
    ("Rahimov", "Jasur", "Olimovich", "Bolalar nevrologi", "Детский невролог", "Pediatric neurologist", 0.70),
    ("Abdullayeva", "Nigora", "Ilhomovna", "Bolalar endokrinologi", "Детский эндокринолог", "Pediatric endocrinologist", 0.88),
    ("Ergashev", "Bobur", "Kamolovich", "Bolalar jarrohi", "Детский хирург", "Pediatric surgeon", 0.60),
    ("Saidova", "Gulnora", "Anvarovna", "LOR (otorinolaringolog)", "ЛОР (оториноларинголог)", "ENT specialist", 0.82),
    ("Qodirov", "Sherzod", "Ulugʻbekovich", "Bolalar gastroenterologi", "Детский гастроэнтеролог", "Pediatric gastroenterologist", 0.45),
    ("Mirzayeva", "Feruza", "Baxromovna", "Pediatr", "Педиатр", "Pediatrician", 0.95),
    ("Nazarov", "Otabek", "Rustamovich", "Bolalar ortopedi", "Детский ортопед", "Pediatric orthopedist", 0.74),
    ("Xolmatova", "Zarina", "Sobirovna", "Bolalar allergologi", "Детский аллерголог", "Pediatric allergist", 0.80),
    ("Usmonov", "Dilshod", "Akmalovich", "Bolalar oftalmologi", "Детский офтальмолог", "Pediatric ophthalmologist", 0.66),
]

COMMENTS = {
    "good": [
        "Shifokor juda eʼtiborli, bolamga yaxshi munosabatda boʻldi. Rahmat!",
        "Hammasi tushunarli qilib tushuntirildi, katta rahmat.",
        "Очень внимательный врач, всё подробно объяснила. Спасибо!",
        "Ребёнок не боялся, врач нашла подход. Рекомендую.",
        "Very kind doctor, explained everything clearly.",
    ],
    "bad": [
        "Navbatda 1 soatdan koʻp kutdik.",
        "Shifokor shoshib turdi, savollarimga javob bermadi.",
        "Долго ждали в очереди, приём был очень коротким.",
        "Не объяснили, как принимать лекарства.",
        "Waited a long time, the appointment felt rushed.",
    ],
}


def pick(quality: float, good, mid, bad):
    x = random.random()
    if x < quality:
        return good
    return mid if x < quality + (1 - quality) * 0.6 else bad


def fake_response(doctor_id: int, quality: float, when: datetime) -> Response:
    q = max(0.05, min(0.98, random.gauss(quality, 0.08)))
    q1 = pick(q, random.choice([5, 5, 4]), random.choice([4, 3]), random.choice([2, 1]))
    nps = pick(q, random.choice([9, 10, 10]), random.choice([7, 8]), random.randint(1, 6))
    comment = None
    if random.random() < 0.25:
        comment = random.choice(COMMENTS["good" if q1 >= 4 else "bad"])
    return Response(
        doctor_id=doctor_id,
        language=random.choices(["uz", "ru", "en"], [0.62, 0.35, 0.03])[0],
        q1_empathy=q1,
        q2_communication=pick(q, "full", "partial", "none"),
        q3_timeliness=pick(min(0.95, q + 0.05), "on_time", "waited_15_20", "long_wait"),
        q4_thoroughness=pick(q, "enough", "partial", "rushed"),
        q5_outcome=pick(q, "full", "partial", "not"),
        q6_nps=nps,
        q7_corruption=random.random() < (0.06 if quality < 0.6 else 0.008),
        q8_comment=comment,
        created_at=when,
    )


async def remove() -> None:
    async with Session() as s, s.begin():
        ids = (await s.scalars(select(Doctor.id).where(Doctor.code.like("demo%")))).all()
        if ids:
            await s.execute(delete(Response).where(Response.doctor_id.in_(ids)))
            await s.execute(delete(Doctor).where(Doctor.id.in_(ids)))
    print(f"Removed {len(ids)} demo doctors and their responses.")


async def seed() -> None:
    await init_db()
    await remove()
    random.seed(42)
    now = datetime.now(timezone.utc)
    total = 0
    async with Session() as s, s.begin():
        for i, (last, first, patr, uz, ru, en, quality) in enumerate(DEMO, start=1):
            d = Doctor(code=f"demo{i:03d}", last_name=last, first_name=first, patronymic=patr,
                       specialty_uz=uz, specialty_ru=ru, specialty_en=en,
                       department=DEPARTMENTS.get(uz), room=str(100 + i * 7))
            s.add(d)
            await s.flush()
            for day in range(120):
                for _ in range(random.choices([0, 1, 2, 3], [0.5, 0.3, 0.15, 0.05])[0]):
                    when = now - timedelta(days=day, hours=random.randint(0, 9), minutes=random.randint(0, 59))
                    s.add(fake_response(d.id, quality, when))
                    total += 1
    print(f"Added {len(DEMO)} demo doctors and {total} demo responses. Run: python -m dashboard")


if __name__ == "__main__":
    asyncio.run(remove() if "--remove" in sys.argv else seed())
