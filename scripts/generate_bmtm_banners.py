"""Door banners in the management design (BMTM), one per doctor with a photo.

    python scripts/generate_bmtm_banners.py            all doctors in doctors_bmtm.csv
    python scripts/generate_bmtm_banners.py Samadov    only matching last names

Writes banners_bmtm/<n>_<name>.html. scripts/render_banners.mjs turns them into
print PNGs and one PDF. All text is in the new Uzbek alphabet.
"""

import base64
import csv
import html
import sys
from pathlib import Path

import cv2

BASE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE))

from bot.config import settings  # noqa: E402
from scripts.generate_banners import qr_svg  # noqa: E402

CSV = BASE / "doctors_bmtm.csv"
OUT = BASE / "banners_bmtm"
BG = BASE / "assets" / "bmtm_banner_base.jpg"
BOT = settings.bot_username or "bmtm_baholash_bot"
NAVY = "#02416c"

# Photo frame (template is 900 x 1080 px): right side follows the teal arc.
TOP = "M0 207 C30 186 70 166 120 156 C170 149 215 150 250 152"
ARC = "M250 152 C295 140 335 160 362 197 C420 250 470 330 474 440 C478 560 495 680 500 800"
FRAME = TOP + " C295 140 335 160 362 197 C420 250 470 330 474 440 C478 560 495 680 500 800 L190 792 C150 773 80 755 0 717 Z"

ICONS = {
    "heart": '<path d="M12 20.5s-7.3-4.4-9.2-8.9C1.4 8 3.6 4.5 7 4.5c2 0 3.5 1.1 5 2.9 1.5-1.8 3-2.9 5-2.9 3.4 0 5.6 3.5 4.2 7.1-1.9 4.5-9.2 8.9-9.2 8.9z"/><path d="M4.5 12h3.5l1.5-3 3 6 1.5-3h5.5"/>',
    "brain": '<path d="M9.5 4A3 3 0 0 0 6.5 6.6 3 3 0 0 0 4 9.6c0 1 .4 1.8 1 2.4-.6.6-1 1.5-1 2.6a3.5 3.5 0 0 0 3 3.5 3 3 0 0 0 5 1.4V5.5A2.4 2.4 0 0 0 9.5 4zM14.5 4a3 3 0 0 1 3 2.6 3 3 0 0 1 2.5 3c0 1-.4 1.8-1 2.4.6.6 1 1.5 1 2.6a3.5 3.5 0 0 1-3 3.5 3 3 0 0 1-5 1.4V5.5A2.4 2.4 0 0 1 14.5 4z"/><path d="M8 10.5c1.2 0 2 .7 2 2M16 10.5c-1.2 0-2 .7-2 2M7.5 15c1 0 1.8-.4 2.3-1M16.5 15c-1 0-1.8-.4-2.3-1"/>',
    "eye": '<path d="M2 12s3.6-6.5 10-6.5S22 12 22 12s-3.6 6.5-10 6.5S2 12 2 12z"/><circle cx="12" cy="12" r="3"/>',
    "ear": '<path d="M7 9a5 5 0 0 1 10 0c0 3.2-2.6 3.8-3.1 6.6-.4 2.2-1.6 4-4 4A3.2 3.2 0 0 1 6.8 17"/><path d="M10 9.6a2 2 0 0 1 4 .2c0 1.4-1.6 1.8-1.6 3.4"/>',
    "tooth": '<path d="M7.6 3.5c-2.5 0-4.1 2-4.1 4.6 0 2 .8 3.4 1.4 5.4.6 2 .8 7 2.6 7 1.6 0 1.7-5.5 4.5-5.5s2.9 5.5 4.5 5.5c1.8 0 2-5 2.6-7 .6-2 1.4-3.4 1.4-5.4 0-2.6-1.6-4.6-4.1-4.6-1.8 0-2.6 1-4.4 1s-2.6-1-4.4-1z"/>',
    "kidney": '<path d="M14.5 3.5c-3.6 0-6.5 3.6-6.5 8.5s2.9 8.5 6.5 8.5c2.6 0 4.5-1.8 4.5-4.3 0-2-1.7-2.7-1.7-4.2s1.7-2.2 1.7-4.2c0-2.5-1.9-4.3-4.5-4.3z"/><path d="M8.3 12H4.5M4.5 12v6"/>',
    "lungs": '<path d="M12 3.5v7.5M12 11c-1.4 0-2.4.9-2.9 2M12 11c1.4 0 2.4.9 2.9 2"/><path d="M8 7c-2.5 0-4.5 4-4.5 8.4 0 2.5 1 3.6 2.6 3.6 2.4 0 2.9-1.5 2.9-4V8.4C9 7.6 8.6 7 8 7zM16 7c2.5 0 4.5 4 4.5 8.4 0 2.5-1 3.6-2.6 3.6-2.4 0-2.9-1.5-2.9-4V8.4c0-.8.4-1.4 1-1.4z"/>',
    "drop": '<path d="M12 3s6.5 7 6.5 11.5a6.5 6.5 0 0 1-13 0C5.5 10 12 3 12 3z"/><path d="M9 15a3 3 0 0 0 3 3"/>',
    "dna": '<path d="M7 3c0 5 10 7 10 12 0 3-2 5-2 6M17 3c0 5-10 7-10 12 0 3 2 5 2 6M8.6 6h6.8M8.6 18h6.8M10 9.5h4M10 14.5h4"/>',
    "shield": '<path d="M12 3l7.5 3v5.5c0 4.6-3.2 8.2-7.5 9.5-4.3-1.3-7.5-4.9-7.5-9.5V6z"/><path d="M12 8.5v6M9 11.5h6"/>',
    "steth": '<path d="M6 3.5v5a4.5 4.5 0 0 0 9 0v-5M4.5 3.5h3M13.5 3.5h3M10.5 13v2.5a4.5 4.5 0 0 0 9 0V13"/><circle cx="19.5" cy="11" r="2"/>',
}

FACE = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")


def photo_box(path: Path) -> tuple[float, float, float]:
    """left, top, width (template px) so the face sits like in the design."""
    img = cv2.imread(str(path))
    h, w = img.shape[:2]
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    faces = FACE.detectMultiScale(gray, 1.1, 6, minSize=(w // 12, w // 12))
    if len(faces):
        fx, fy, fw, fh = max(faces, key=lambda f: f[2] * f[3])
    else:  # fallback: assume a centred head in the upper third
        fw = w * 0.22
        fx, fy = (w - fw) / 2, h * 0.14
    face_w, cx, top_y = 120.0, 270.0, 205.0  # target face width, centre x, face top
    frame_l, frame_r, frame_t, frame_b = 0, 505, 145, 800
    s = face_w / fw
    while True:
        left = cx - (fx + fw / 2) * s
        top = top_y - fy * s
        left = min(frame_l, max(left, frame_r - w * s))
        top = min(frame_t, max(top, frame_b - h * s))
        if w * s >= frame_r - frame_l and h * s >= frame_b - frame_t:
            return left, top, w * s
        s *= 1.03


def data_uri(path: Path) -> str:
    mime = "image/png" if path.suffix.lower() == ".png" else "image/jpeg"
    return f"data:{mime};base64,{base64.b64encode(path.read_bytes()).decode()}"


TEMPLATE = """<!doctype html><html lang="uz"><head><meta charset="utf-8"><title>{title}</title>
<link href="https://fonts.googleapis.com/css2?family=Montserrat:wght@500;600;700;800&family=Playfair+Display:ital,wght@1,700&display=swap" rel="stylesheet">
<style>
@page {{ size: 250mm 300mm; margin: 0 }}
* {{ box-sizing: border-box; margin: 0; padding: 0 }}
html, body {{ width: 900px; height: 1080px; overflow: hidden; background: #fff }}
body {{ font-family: Montserrat, Arial, sans-serif; position: relative; color: {navy} }}
@media print {{ html, body {{ zoom: 1.0 }} body {{ transform-origin: 0 0; transform: scale(1.0) }} }}
.bg {{ position: absolute; inset: 0; width: 900px; height: 1080px }}
svg.layer {{ position: absolute; left: 0; top: 0; width: 900px; height: 1080px }}
.name {{ position: absolute; left: 458px; top: 262px; width: 450px; height: 136px; background: {navy};
  border-radius: 40px 0 0 40px; color: #fff; display: flex; flex-direction: column; justify-content: center;
  padding: 0 30px 0 34px; text-align: center }}
.name .l {{ display: inline-block; align-self: center; font-weight: 700; font-size: 58px; line-height: 1.05; white-space: nowrap }}
.name .f {{ display: inline-block; align-self: center; font-weight: 700; font-size: 38px; line-height: 1.2; white-space: nowrap; margin-top: 2px }}
.deg {{ position: absolute; left: 520px; width: 350px; top: 400px; height: 58px; display: flex; align-items: center; gap: 14px }}
.deg i {{ flex: 1; height: 3px; border-radius: 2px; background: linear-gradient(90deg, #2f8fb0, #4fb37f) }}
.deg b {{ font-family: "Playfair Display", Georgia, serif; font-style: italic; font-weight: 700; font-size: 48px; color: #0d3b66; white-space: nowrap }}
.deg.none {{ gap: 0 }} .deg.none b {{ display: none }}
.spec {{ position: absolute; left: 517px; top: 466px; width: 360px; height: 82px; border-radius: 41px; background: #c6e7de;
  display: flex; align-items: center; gap: 12px; padding: 0 24px 0 26px }}
.spec svg {{ width: 62px; height: 62px; flex: none; fill: none; stroke: #13897f; stroke-width: 1.5;
  stroke-linecap: round; stroke-linejoin: round }}
.spec span {{ font-weight: 700; font-size: 38px; white-space: nowrap; flex: 1; min-width: 0; overflow: hidden; text-align: center }}
.wipe {{ position: absolute; background: #fefefe }}
.qr {{ position: absolute; left: 46px; top: 791px; width: 186px; height: 186px }}
.qr svg {{ width: 100%; height: 100% }}
.head {{ position: absolute; left: 293px; top: 792px; width: 370px; font-weight: 700; font-size: 28.5px; line-height: 1.22; color: #0d3b66 }}
.sub {{ position: absolute; left: 293px; top: 868px; width: 370px; font-weight: 500; font-size: 17px; color: #0d3b66; white-space: nowrap }}
</style></head><body>
<img class="bg" src="{bg}">
<svg class="layer" viewBox="0 0 900 1080">
  <defs><clipPath id="frame"><path d="{frame}"/></clipPath>
  <linearGradient id="arc" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#1aa6a0"/><stop offset="1" stop-color="#0d7590"/></linearGradient></defs>
  <g clip-path="url(#frame)"><rect x="0" y="150" width="530" height="660" fill="#eef4f8"/>
  <image href="{photo}" x="{px:.1f}" y="{py:.1f}" width="{pw:.1f}" preserveAspectRatio="xMidYMin meet"/></g>
  <path d="{top}" fill="none" stroke="#f4fafc" stroke-width="6"/>
  <path d="{arc}" fill="none" stroke="#ffffff" stroke-width="24" stroke-opacity=".7" transform="translate(-8 0)"/>
  <path d="{arc}" fill="none" stroke="url(#arc)" stroke-width="16"/>
</svg>
<div class="name"><div class="l fit">{last}</div><div class="f fit">{first}</div></div>
<div class="spec"><svg viewBox="0 0 24 24">{icon}</svg><span class="fit">{specialty}</span></div>
{degree}
<div class="wipe" style="left:38px;top:784px;width:202px;height:198px"></div>
<div class="wipe" style="left:284px;top:788px;width:382px;height:106px"></div>
<div class="qr">{qr}</div>
<div class="head">Şifokor faoliyatini<br>baholang!</div>
<div class="sub fit">Özingizning fikringiz biz uçun muhim</div>
<script>
document.fonts.ready.then(() => {{
  for (const el of document.querySelectorAll('.fit')) {{
    const max = el.parentElement.classList.contains('spec') ? el.clientWidth : el.parentElement.clientWidth - 70;
    let size = parseFloat(getComputedStyle(el).fontSize);
    while (el.scrollWidth > (el.classList.contains('l') || el.classList.contains('f') ? 384 : max) && size > 10) {{
      size -= 0.5; el.style.fontSize = size + 'px';
    }}
  }}
  document.body.dataset.ready = '1';
}});
</script>
</body></html>"""


def main(filters: list[str]) -> None:
    OUT.mkdir(exist_ok=True)
    bg = data_uri(BG)
    with open(CSV, encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))
    n = 0
    for i, r in enumerate(rows, start=1):
        if filters and not any(x.lower() in r["last_name"].lower() for x in filters):
            continue
        if not r["photo"]:
            continue
        photo = BASE / r["photo"]
        px, py, pw = photo_box(photo)
        first = " ".join(x for x in (r["first_name"], r["patronymic"]) if x)
        deg = html.escape(r["degree"].replace("dotsent", "Dotsent"))
        degree = f'<div class="deg{"" if deg else " none"}"><i></i><b>{deg}</b><i></i></div>'
        link = f"https://t.me/{BOT}?start={r['code']}"
        page = TEMPLATE.format(
            title=html.escape(f'{r["last_name"]} {first}'), navy=NAVY, bg=bg, frame=FRAME, arc=ARC, top=TOP,
            photo=data_uri(photo), px=px, py=py, pw=pw, last=html.escape(r["last_name"]),
            first=html.escape(first), icon=ICONS.get(r["icon"], ICONS["steth"]),
            specialty=html.escape(r["specialty_uz"]), degree=degree, qr=qr_svg(link))
        name = f"{i:02d}_{Path(r['photo']).stem}.html"
        (OUT / name).write_text(page, encoding="utf-8")
        n += 1
    print(f"{n} banners written to {OUT}/")


if __name__ == "__main__":
    main(sys.argv[1:])
