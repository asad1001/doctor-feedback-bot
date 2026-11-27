"""Generate a print-ready A4 door banner for every doctor.

    python scripts/generate_banners.py            all active doctors
    python scripts/generate_banners.py 5 7        only doctors with id 5 and 7

Writes banners/<id>_<surname>.html. Open a file in Chrome or Edge, press
Ctrl+P, choose "Save as PDF" (or your printer), paper A4, margins "None",
and tick "Background graphics". Each banner contains the doctor's photo,
name, specialty, room and their personal QR code.
"""

import base64
import html
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import asyncio  # noqa: E402

import qrcode  # noqa: E402
from sqlalchemy import select  # noqa: E402

from bot.config import BASE_DIR, settings  # noqa: E402
from bot.db import Doctor, Session, init_db  # noqa: E402

OUT = BASE_DIR / "banners"
ASSETS = BASE_DIR / "assets"
NAVY = "#0f2c43"


def data_uri(path: Path) -> str:
    mime = {".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png", ".svg": "image/svg+xml",
            ".webp": "image/webp"}[path.suffix.lower()]
    return f"data:{mime};base64,{base64.b64encode(path.read_bytes()).decode()}"


def qr_svg(link: str) -> str:
    """QR as crisp vector SVG with the clinic emblem in the middle."""
    qr = qrcode.QRCode(error_correction=qrcode.constants.ERROR_CORRECT_H, border=0)
    qr.add_data(link)
    qr.make(fit=True)
    m = qr.get_matrix()
    n = len(m)
    hole = round(n * 0.22) | 1  # odd size, ~22% of the width, safe with level H
    lo, hi = (n - hole) // 2, (n + hole) // 2
    rects = []
    for y, row in enumerate(m):
        for x, dark in enumerate(row):
            if dark and not (lo - 1 <= x <= hi and lo - 1 <= y <= hi):
                rects.append(f"M{x} {y}h1v1h-1z")
    emblem = (ASSETS / "emblem.svg").read_text(encoding="utf-8")
    inner = re.sub(r"^<svg[^>]*>|</svg>$", "", emblem.strip())
    s = hole / 54
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {n} {n}" shape-rendering="crispEdges">'
        f'<path fill="{NAVY}" d="{"".join(rects)}"/>'
        f'<rect x="{lo - 0.5}" y="{lo - 0.5}" width="{hole + 1}" height="{hole + 1}" rx="1.2" fill="#fff"/>'
        f'<g transform="translate({lo} {lo}) scale({s})" shape-rendering="auto">{inner}</g></svg>'
    )


ICON_SCAN = ('<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" '
             'stroke-linejoin="round"><path d="M3 7V5a2 2 0 0 1 2-2h2M17 3h2a2 2 0 0 1 2 2v2M21 17v2a2 2 0 0 1-2 2h-2'
             'M7 21H5a2 2 0 0 1-2-2v-2"/><rect x="7" y="7" width="4" height="4"/><rect x="13" y="13" width="4" height="4"/>'
             '<path d="M13 7h4v2M7 15v2h2"/></svg>')
ICON_TG = ('<svg viewBox="0 0 24 24" fill="currentColor"><path d="M21.5 3.6 2.9 10.8c-1.3.5-1.2 1.3-.2 1.6l4.8 1.5 '
           '1.8 5.6c.2.6.4.8.9.8.4 0 .6-.2.9-.4l2.4-2.3 4.9 3.6c.9.5 1.5.2 1.8-.8l3.2-15.2c.3-1.3-.5-1.9-1.4-1.6zM9.6 '
           '14.2l8.6-7.6c.4-.3-.1-.5-.6-.2L7.5 13.1"/></svg>')
ICON_STAR = ('<svg viewBox="0 0 24 24" fill="currentColor"><path d="m12 2.8 2.8 5.8 6.3.9-4.6 4.5 1.1 6.3L12 17.3 '
             '6.4 20.3l1.1-6.3L2.9 9.5l6.3-.9z"/></svg>')
ICON_LOCK = ('<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round">'
             '<rect x="5" y="11" width="14" height="10" rx="2"/><path d="M8 11V8a4 4 0 0 1 8 0v3"/></svg>')
ICON_CLOCK = ('<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round">'
              '<circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/></svg>')

TEMPLATE = """<!doctype html>
<html lang="uz"><head><meta charset="utf-8">
<title>{title}</title>
<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Montserrat:wght@500;600;700;800;900&display=swap" rel="stylesheet">
<style>
  @page {{ size: A4; margin: 0; }}
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  html, body {{ background: #e9eef1; }}
  body {{ font-family: Montserrat, "Segoe UI", Arial, sans-serif; color: {navy};
         -webkit-print-color-adjust: exact; print-color-adjust: exact; }}
  .page {{ width: 210mm; height: 297mm; margin: 10mm auto; background: #fff; position: relative; overflow: hidden; }}
  @media print {{ html, body {{ background: #fff; }} .page {{ margin: 0; }} }}

  /* soft brand shapes */
  .blob {{ position: absolute; border-radius: 50%; filter: blur(0.2mm); }}
  .b1 {{ width: 150mm; height: 150mm; right: -55mm; top: -45mm; background: radial-gradient(circle at 30% 70%, #d8f3f6, #eaf7f9 60%, transparent 61%); }}
  .b2 {{ width: 90mm; height: 90mm; left: -40mm; top: 95mm; background: radial-gradient(circle, #e6f5e4 0 60%, transparent 61%); }}

  header {{ position: absolute; top: 12mm; left: 16mm; right: 16mm; display: flex; align-items: center; justify-content: space-between; }}
  header img {{ height: 17mm; }}
  .room {{ font-weight: 800; font-size: 13pt; color: #fff; background: {navy}; padding: 2.4mm 5mm; border-radius: 30mm; letter-spacing: .3mm; }}

  .photo-wrap {{ position: absolute; top: 37mm; left: 50%; transform: translateX(-50%); width: 104mm; height: 124mm; }}
  .ring {{ position: absolute; inset: -3.2mm; border-radius: 52mm 52mm 9mm 9mm; background: linear-gradient(140deg, #00a9c1, #3aaa35); }}
  .photo {{ position: absolute; inset: 0; border-radius: 50mm 50mm 7mm 7mm; overflow: hidden; background: #f3f6f7; border: 1.6mm solid #fff; }}
  .photo img {{ width: 100%; height: 100%; object-fit: cover; object-position: 50% 12%; }}
  .photo .ph {{ width: 100%; height: 100%; display: grid; place-items: center; font-size: 60pt; color: #9cc9cd; }}

  .who {{ position: absolute; top: 168mm; left: 12mm; right: 12mm; text-align: center; }}
  .surname {{ font-size: 36pt; font-weight: 900; letter-spacing: 1.2mm; line-height: 1; text-transform: uppercase; }}
  .given {{ font-size: 19pt; font-weight: 600; margin-top: 2.6mm; color: #2c4a5e; }}
  .tags {{ margin-top: 5mm; display: flex; gap: 3mm; justify-content: center; flex-wrap: wrap; }}
  .tag {{ font-size: 14pt; font-weight: 700; padding: 2mm 6mm; border-radius: 30mm; color: #fff; background: #00a9c1; }}
  .tag:nth-child(2n) {{ background: #3aaa35; }}
  .dept {{ margin-top: 3mm; font-size: 11pt; font-weight: 600; color: #5d7584; }}

  .cta {{ position: absolute; left: 10mm; right: 10mm; bottom: 10mm; height: 76mm; border-radius: 7mm; padding: 7mm;
          background: linear-gradient(120deg, #0f2c43 0%, #11506a 55%, #0a7f8f 100%); color: #fff; display: flex; gap: 7mm; align-items: center; }}
  .qr {{ flex: none; width: 62mm; height: 62mm; background: #fff; border-radius: 4.5mm; padding: 4mm; }}
  .qr svg {{ width: 100%; height: 100%; display: block; }}
  .txt {{ flex: 1; min-width: 0; }}
  .h1 {{ font-size: 21pt; font-weight: 800; line-height: 1.12; }}
  .h2 {{ font-size: 11pt; font-weight: 500; opacity: .85; margin-top: 1.6mm; line-height: 1.35; }}
  .steps {{ display: flex; gap: 2.5mm; margin-top: 5mm; }}
  .step {{ flex: 1; background: rgba(255,255,255,.1); border: .3mm solid rgba(255,255,255,.18); border-radius: 3mm;
           padding: 2.6mm 2mm; text-align: center; font-size: 8.6pt; font-weight: 700; line-height: 1.2; }}
  .step svg {{ width: 7mm; height: 7mm; display: block; margin: 0 auto 1.3mm; color: #7fe3ee; }}
  .step:nth-child(3) svg {{ color: #ffd166; }}
  .meta {{ display: flex; gap: 5mm; margin-top: 4.5mm; font-size: 9.5pt; font-weight: 600; opacity: .95; flex-wrap: wrap; }}
  .meta span {{ display: inline-flex; align-items: center; gap: 1.5mm; }}
  .meta svg {{ width: 4.2mm; height: 4.2mm; color: #7fe3ee; }}
</style></head>
<body><div class="page">
  <div class="blob b1"></div><div class="blob b2"></div>
  <header><img src="{logo}" alt="Bolalar Milliy Tibbiyot Markazi">{room}</header>
  <div class="photo-wrap"><div class="ring"></div><div class="photo">{photo}</div></div>
  <div class="who">
    <div class="surname">{surname}</div>
    <div class="given">{given}</div>
    <div class="tags">{tags}</div>
    {dept}
  </div>
  <div class="cta">
    <div class="qr">{qr}</div>
    <div class="txt">
      <div class="h1">Shifokor faoliyatini<br>baholang!</div>
      <div class="h2">Оцените работу врача · Rate your doctor</div>
      <div class="steps">
        <div class="step">{i_scan}Skanerlang<br><span style="font-weight:500;opacity:.8">Сканируйте</span></div>
        <div class="step">{i_tg}Telegram<br><span style="font-weight:500;opacity:.8">бот</span></div>
        <div class="step">{i_star}Baholang<br><span style="font-weight:500;opacity:.8">Оцените</span></div>
      </div>
      <div class="meta"><span>{i_lock}Anonim</span><span>{i_clock}1 daqiqa</span><span>{i_tg}@{bot}</span></div>
    </div>
  </div>
</div></body></html>
"""


def banner_html(d: Doctor) -> str:
    link = f"https://t.me/{settings.bot_username}?start={d.code}"
    photo = '<div class="ph">👨‍⚕️</div>'
    if d.photo_path:
        p = Path(d.photo_path)
        p = p if p.is_absolute() else BASE_DIR / p
        if p.is_file():
            photo = f'<img src="{data_uri(p)}" alt="">'
    specialties = [s.strip() for s in re.split(r"[,/;]", d.specialty_uz) if s.strip()]
    e = html.escape
    return TEMPLATE.format(
        title=e(d.full_name),
        navy=NAVY,
        logo=data_uri(ASSETS / "logo.svg"),
        room=f'<div class="room">{e(d.room)}-kabinet</div>' if d.room else "",
        photo=photo,
        surname=e(d.last_name),
        given=e(" ".join(p for p in (d.first_name, d.patronymic) if p)),
        tags="".join(f'<span class="tag">{e(s[:1].upper() + s[1:])}</span>' for s in specialties),
        dept=f'<div class="dept">{e(d.department)}</div>' if d.department else "",
        qr=qr_svg(link),
        bot=e(settings.bot_username),
        i_scan=ICON_SCAN, i_tg=ICON_TG, i_star=ICON_STAR, i_lock=ICON_LOCK, i_clock=ICON_CLOCK,
    )


def slug(text: str) -> str:
    return re.sub(r"[^A-Za-z0-9]+", "_", text).strip("_").lower() or "doctor"


async def main(ids: list[int]) -> None:
    if not settings.bot_username:
        sys.exit("Set BOT_USERNAME in .env first.")
    await init_db()
    async with Session() as s:
        q = select(Doctor).where(Doctor.is_active.is_(True), Doctor.code.not_like("demo%")).order_by(Doctor.id)
        if ids:
            q = q.where(Doctor.id.in_(ids))
        doctors = (await s.scalars(q)).all()
    if not doctors:
        sys.exit("No doctors found. Add them first: python scripts/import_doctors.py doctors.csv")
    OUT.mkdir(exist_ok=True)
    for d in doctors:
        path = OUT / f"{d.id:03d}_{slug(d.last_name)}.html"
        path.write_text(banner_html(d), encoding="utf-8")
        print(f"{d.id:>4}  {d.full_name:<40} {path.name}")
    print(f"\nSaved {len(doctors)} banners to {OUT}\nOpen one in Chrome, press Ctrl+P, A4, margins None, "
          "tick 'Background graphics', Save as PDF.")


if __name__ == "__main__":
    asyncio.run(main([int(a) for a in sys.argv[1:] if a.isdigit()]))
