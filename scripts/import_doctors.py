"""Add doctors from a CSV file.

    python scripts/import_doctors.py doctors.csv

CSV columns (first row = header):
    last_name, first_name, patronymic, specialty_uz, specialty_ru, specialty_en,
    department, room, photo, code (optional)

A doctor with the same code, or the same last_name + first_name + patronymic, is updated,
not duplicated, so you can re-run the import after editing the CSV.
Each new doctor gets a random code that goes into their QR link.
"""

import asyncio
import csv
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import select  # noqa: E402

from bot.db import Doctor, Session, init_db  # noqa: E402

FIELDS = ("specialty_uz", "specialty_ru", "specialty_en", "department", "room")


def clean(value: str | None) -> str | None:
    value = (value or "").strip()
    return value or None


async def main(csv_path: str) -> None:
    await init_db()
    added = updated = 0
    with open(csv_path, newline="", encoding="utf-8-sig") as f:
        rows = list(csv.DictReader(f))
    async with Session() as s, s.begin():
        for n, row in enumerate(rows, start=2):
            last, first = clean(row.get("last_name")), clean(row.get("first_name"))
            if not last or not first or not clean(row.get("specialty_uz")):
                print(f"line {n}: skipped (last_name, first_name and specialty_uz are required)")
                continue
            patronymic = clean(row.get("patronymic"))
            code = clean(row.get("code"))
            # A known code wins: the printed QR stays tied to the same doctor even if the
            # spelling of the name changes (e.g. after moving to the new alphabet).
            doctor = await s.scalar(select(Doctor).where(Doctor.code == code)) if code else None
            if doctor is None:
                doctor = await s.scalar(
                    select(Doctor).where(Doctor.last_name == last, Doctor.first_name == first, Doctor.patronymic.is_not_distinct_from(patronymic))
                )
            if doctor is not None:
                doctor.last_name, doctor.first_name, doctor.patronymic = last, first, patronymic
            if doctor is None:
                doctor = Doctor(last_name=last, first_name=first, patronymic=patronymic)
                if code:  # optional: keep a code that is already printed on a banner
                    doctor.code = code
                s.add(doctor)
                added += 1
            else:
                updated += 1
            for field in FIELDS:
                setattr(doctor, field, clean(row.get(field)))
            doctor.photo_path = clean(row.get("photo"))
    print(f"Done: {added} added, {updated} updated. Now run: python scripts/generate_qr.py")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    asyncio.run(main(sys.argv[1]))
