"""Generate one QR code per doctor for the door banners.

    python scripts/generate_qr.py

For every active doctor it writes into qr_codes/:
  * <id>_<surname>.svg  pure vector QR, best for the banner designer / printing
  * <id>_<surname>.png  QR with the doctor's name underneath, for quick checks
and prints a table of all links (also saved as qr_codes/links.csv).

Every QR opens the same bot: https://t.me/<BOT_USERNAME>?start=<doctor code>
"""

import asyncio
import csv
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import qrcode  # noqa: E402
import qrcode.image.svg  # noqa: E402
from PIL import Image, ImageDraw, ImageFont  # noqa: E402
from sqlalchemy import select  # noqa: E402

from bot.config import BASE_DIR, settings  # noqa: E402
from bot.db import Doctor, Session, init_db  # noqa: E402

OUT = BASE_DIR / "qr_codes"
FONT_CANDIDATES = [
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    "/usr/share/fonts/dejavu/DejaVuSans.ttf",
    "C:/Windows/Fonts/arial.ttf",
    "/System/Library/Fonts/Supplemental/Arial.ttf",
    "/Library/Fonts/Arial.ttf",
]


def font(size: int):
    for path in FONT_CANDIDATES:
        if Path(path).is_file():
            return ImageFont.truetype(path, size)
    return ImageFont.load_default(size=size)


def make_qr(link: str) -> qrcode.QRCode:
    qr = qrcode.QRCode(error_correction=qrcode.constants.ERROR_CORRECT_Q, box_size=20, border=4)
    qr.add_data(link)
    qr.make(fit=True)
    return qr


def labelled_png(qr: qrcode.QRCode, lines: list[str]) -> Image.Image:
    img = qr.make_image(fill_color="black", back_color="white").convert("RGB")
    w, h = img.size
    pad = 24
    canvas = Image.new("RGB", (w, h + pad + 60 * len(lines)), "white")
    canvas.paste(img, (0, 0))
    draw = ImageDraw.Draw(canvas)
    y = h
    for i, text in enumerate(lines):
        size = 44 if i == 0 else 34
        f = font(size)
        while draw.textlength(text, font=f) > w - 40 and size > 16:  # shrink long names
            size -= 2
            f = font(size)
        tw = draw.textlength(text, font=f)
        draw.text(((w - tw) / 2, y), text, fill="black", font=f)
        y += 60
    return canvas


def slug(text: str) -> str:
    return re.sub(r"[^A-Za-z0-9]+", "_", text).strip("_").lower() or "doctor"


async def main() -> None:
    if not settings.bot_username:
        sys.exit("Set BOT_USERNAME in .env first (the bot's @username, without @).")
    await init_db()
    OUT.mkdir(exist_ok=True)
    async with Session() as s:
        doctors = (await s.scalars(select(Doctor).where(Doctor.is_active.is_(True), Doctor.code.not_like("demo%")).order_by(Doctor.id))).all()
    if not doctors:
        sys.exit("No doctors yet. Add them first: python scripts/import_doctors.py doctors.csv")

    with open(OUT / "links.csv", "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f)
        writer.writerow(["id", "full_name", "specialty", "department", "room", "link", "png", "svg"])
        for d in doctors:
            link = f"https://t.me/{settings.bot_username}?start={d.code}"
            base = f"{d.id:03d}_{slug(d.last_name)}"
            qr = make_qr(link)
            labelled_png(qr, [d.full_name, d.specialty_uz + (f" · {d.room}-kabinet" if d.room else "")]).save(OUT / f"{base}.png")
            qr.make_image(image_factory=qrcode.image.svg.SvgPathImage).save(str(OUT / f"{base}.svg"))
            writer.writerow([d.id, d.full_name, d.specialty_uz, d.department or "", d.room or "", link, f"{base}.png", f"{base}.svg"])
            print(f"{d.id:>4}  {d.full_name:<40} {link}")
    print(f"\nSaved {len(doctors)} QR codes to {OUT}")


if __name__ == "__main__":
    asyncio.run(main())
