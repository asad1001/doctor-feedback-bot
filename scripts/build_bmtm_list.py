"""Build doctors_bmtm.csv (new Uzbek alphabet) and copy the doctors' photos.

    python scripts/build_bmtm_list.py [photo folder ...]

The doctor list lives in data_src/doctors_raw.py. Photos are matched by the
file name management sent (e.g. "Самадов Фуркат (1).png") and saved as
photos/bmtm/<last>_<first>.jpg. Codes already in doctors_bmtm.csv are kept,
so re-running never changes a printed QR code.
"""

import csv
import re
import secrets
import string
import sys
import unicodedata
from pathlib import Path

from PIL import Image

BASE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE))

from data_src.doctors_raw import DOCTORS, SPECIALTIES  # noqa: E402

OUT_CSV = BASE / "doctors_bmtm.csv"
PHOTO_DIR = BASE / "photos" / "bmtm"
DEPARTMENT = "Maslahat va diagnostika"
FIXED_CODES = {("Samadov", "Furqat"): "SmdF7nQ2"}  # already printed
FIELDS = ["last_name", "first_name", "patronymic", "specialty_uz", "specialty_ru", "specialty_en",
          "department", "room", "photo", "code", "degree", "icon"]


def slug(text: str) -> str:
    table = str.maketrans({"ş": "sh", "ç": "ch", "ö": "o", "ğ": "g", "Ş": "Sh", "Ç": "Ch", "Ö": "O", "Ğ": "G"})
    text = unicodedata.normalize("NFKD", text.translate(table)).encode("ascii", "ignore").decode()
    return re.sub(r"[^A-Za-z0-9]+", "_", text).strip("_").lower()


def new_code(used: set[str]) -> str:
    alphabet = string.ascii_letters + string.digits
    while True:
        code = "".join(secrets.choice(alphabet) for _ in range(8))
        if code not in used:
            used.add(code)
            return code


def main(folders: list[str]) -> None:
    old = {}
    if OUT_CSV.exists():
        with open(OUT_CSV, encoding="utf-8-sig", newline="") as f:
            old = {(r["last_name"], r["first_name"]): r for r in csv.DictReader(f)}
    sources = {}
    for folder in folders:
        for p in Path(folder).iterdir():
            if p.suffix.lower() in (".png", ".jpg", ".jpeg", ".webp"):
                sources[unicodedata.normalize("NFC", p.stem).strip()] = p
    PHOTO_DIR.mkdir(parents=True, exist_ok=True)
    used = {r["code"] for r in old.values() if r.get("code")} | set(FIXED_CODES.values())
    rows, missing = [], []
    for last, first, patr, spec, degree, stem in DOCTORS:
        key = (last, first)
        prev = old.get(key, {})
        code = FIXED_CODES.get(key) or prev.get("code") or new_code(used)
        photo = prev.get("photo", "")
        src = sources.get(unicodedata.normalize("NFC", stem).strip()) if stem else None
        if src:
            dest = PHOTO_DIR / f"{slug(last)}_{slug(first)}.jpg"
            Image.open(src).convert("RGB").save(dest, quality=92)
            photo = dest.relative_to(BASE).as_posix()
        if not photo:
            missing.append(f"{last} {first}")
        uz, ru, en, icon = SPECIALTIES[spec]
        rows.append(dict(last_name=last, first_name=first, patronymic=patr, specialty_uz=uz, specialty_ru=ru,
                         specialty_en=en, department=DEPARTMENT, room="", photo=photo, code=code,
                         degree=degree, icon=icon))
    with open(OUT_CSV, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        w.writeheader()
        w.writerows(rows)
    unmatched = set(sources) - {unicodedata.normalize("NFC", d[5]).strip() for d in DOCTORS}
    print(f"{len(rows)} doctors written to {OUT_CSV.name}, {len(rows) - len(missing)} with photo.")
    if unmatched:
        print("Photos not matched to anyone:", ", ".join(sorted(unmatched)))
    if missing:
        print(f"No photo yet ({len(missing)}):", ", ".join(missing))


if __name__ == "__main__":
    main(sys.argv[1:])
