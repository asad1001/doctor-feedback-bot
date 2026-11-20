"""Management dashboard.

Run:  python -m dashboard        then open http://localhost:8000
"""

import hmac
import io
from contextlib import asynccontextmanager
from datetime import date
from pathlib import Path

from fastapi import Depends, FastAPI, Form, HTTPException, Request
from fastapi.responses import FileResponse, HTMLResponse, RedirectResponse, StreamingResponse
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill
from sqlalchemy import func, select
from starlette.middleware.sessions import SessionMiddleware

from bot.config import BASE_DIR, settings
from bot.db import Response, Session, init_db

from . import analytics as an

STATIC = Path(__file__).parent / "static"

@asynccontextmanager
async def lifespan(_app):
    await init_db()
    yield


app = FastAPI(title="Doctor feedback dashboard", docs_url=None, redoc_url=None, openapi_url=None, lifespan=lifespan)
app.add_middleware(
    SessionMiddleware,
    secret_key=settings.dashboard_secret or (settings.anon_salt + ":dashboard"),
    max_age=12 * 3600,
    same_site="strict",
    https_only=False,  # set True once the dashboard is served over HTTPS
)


# ------------------------------------------------------------------ auth


def require_user(request: Request) -> str:
    user = request.session.get("user")
    if not user or user not in settings.dashboard_users:
        raise HTTPException(status_code=401)
    return user


@app.get("/login", response_class=HTMLResponse)
async def login_page(error: int = 0):
    html = (STATIC / "login.html").read_text(encoding="utf-8")
    return html.replace("{{error}}", "Login yoki parol notoʻgʻri" if error else "")


@app.post("/login")
async def login(request: Request, username: str = Form(...), password: str = Form(...)):
    expected = settings.dashboard_users.get(username.strip())
    if expected and hmac.compare_digest(expected.encode(), password.encode()):
        request.session["user"] = username.strip()
        return RedirectResponse("/", status_code=303)
    return RedirectResponse("/login?error=1", status_code=303)


@app.get("/logout")
async def logout(request: Request):
    request.session.clear()
    return RedirectResponse("/login", status_code=303)


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    if request.session.get("user") not in settings.dashboard_users:
        return RedirectResponse("/login", status_code=303)
    return FileResponse(STATIC / "index.html")


# ------------------------------------------------------------------- API


def filters(date_from: date | None = None, date_to: date | None = None, specialty: str | None = None,
            department: str | None = None):
    return {"date_from": date_from, "date_to": date_to, "specialty": specialty or None,
            "department": department or None}


@app.get("/api/me")
async def me(user: str = Depends(require_user)):
    return {"user": user}


@app.get("/api/latest")
async def latest(_: str = Depends(require_user)):
    """Polled by the page every few seconds to detect new responses."""
    async with Session() as s:
        return {"latest_id": await s.scalar(select(func.max(Response.id))) or 0}


@app.get("/api/specialties")
async def specialties(_: str = Depends(require_user)):
    return sorted({d.specialty_uz for d in await an.all_doctors()})


@app.get("/api/departments")
async def departments(_: str = Depends(require_user)):
    return sorted({d.department for d in await an.all_doctors() if d.department})


@app.get("/api/overview")
async def overview(f: dict = Depends(filters), _: str = Depends(require_user)):
    rows = await an.load(**f)
    responses = [r for r, _d in rows]
    return {
        "metrics": an.metrics(responses),
        "breakdown": an.breakdown(responses),
        "timeseries": an.timeseries(responses, f["date_from"], f["date_to"]),
        "departments": an.by_department(rows),
        "recent_alerts": recent_alerts(rows),
    }


def recent_alerts(rows) -> int:
    """Alerts in the last 24 hours (for the red banner)."""
    from datetime import datetime, timedelta, timezone
    since = datetime.now(timezone.utc) - timedelta(hours=24)
    return sum(1 for r, _d in rows if an.is_alert(r) and an.local_dt(r.created_at) >= since)


@app.get("/api/doctors")
async def doctors(f: dict = Depends(filters), _: str = Depends(require_user)):
    rows = await an.load(**f)
    by_doc: dict[int, list] = {}
    for r, d in rows:
        by_doc.setdefault(d.id, []).append(r)
    out = []
    for d in await an.all_doctors():
        if f["specialty"] and d.specialty_uz != f["specialty"]:
            continue
        if f["department"] and d.department != f["department"]:
            continue
        out.append(an.doctor_dict(d) | an.metrics(by_doc.get(d.id, [])))
    return out


@app.get("/api/doctors/{doctor_id}")
async def doctor_detail(doctor_id: int, date_from: date | None = None, date_to: date | None = None,
                        _: str = Depends(require_user)):
    doctor = next((d for d in await an.all_doctors() if d.id == doctor_id), None)
    if doctor is None:
        raise HTTPException(404)
    rows = await an.load(date_from, date_to, doctor_id=doctor_id)
    responses = [r for r, _d in rows]
    return {
        "doctor": an.doctor_dict(doctor),
        "link": f"https://t.me/{settings.bot_username}?start={doctor.code}" if settings.bot_username else None,
        "metrics": an.metrics(responses),
        "breakdown": an.breakdown(responses),
        "timeseries": an.timeseries(responses, date_from, date_to),
        "responses": [an.response_dict(r, d) for r, d in rows][:200],
    }


@app.get("/api/responses")
async def responses(f: dict = Depends(filters), doctor_id: int | None = None, only_comments: bool = False,
                    only_corruption: bool = False, only_alerts: bool = False, limit: int = 300, _: str = Depends(require_user)):
    rows = await an.load(**f, doctor_id=doctor_id)
    if only_comments:
        rows = [(r, d) for r, d in rows if r.q8_comment]
    if only_corruption:
        rows = [(r, d) for r, d in rows if r.q7_corruption]
    if only_alerts:
        rows = [(r, d) for r, d in rows if an.is_alert(r)]
    return [an.response_dict(r, d) for r, d in rows[: max(1, min(limit, 2000))]]


# ----------------------------------------------------------- Excel export

LABELS = {
    "q2_communication": {"full": "Toʻliq tushuntirdi", "partial": "Qisman", "none": "Tushuntirmadi"},
    "q3_timeliness": {"on_time": "Oʻz vaqtida", "waited_15_20": "15-20 daqiqa", "long_wait": "Uzoq kutdi"},
    "q4_thoroughness": {"enough": "Yetarli", "partial": "Qisman", "rushed": "Shoshilinch"},
    "q5_outcome": {"full": "Toʻliq qoniqdi", "partial": "Qisman", "not": "Qoniqmadi"},
}


@app.get("/api/export.xlsx")
async def export(f: dict = Depends(filters), _: str = Depends(require_user)):
    rows = await an.load(**f)
    wb = Workbook()
    header_font, header_fill = Font(bold=True, color="FFFFFF"), PatternFill("solid", fgColor="1F6F78")

    ws = wb.active
    ws.title = "Shifokorlar"
    by_doc: dict[int, list] = {}
    for r, d in rows:
        by_doc.setdefault(d.id, []).append(r)
    head = ["Shifokor", "Mutaxassislik", "Boʻlim", "Kabinet", "Javoblar", "Sifat indeksi %", "CSAT %", "Muomala (1-5)", "NPS", "Tushuntirish %", "Oʻz vaqtida %",
            "Koʻrik yetarli %", "Qoniqish %", "Korrupsiya holatlari"]
    ws.append(head)
    for d in await an.all_doctors():
        m = an.metrics(by_doc.get(d.id, []))
        if f["specialty"] and d.specialty_uz != f["specialty"] or f["department"] and d.department != f["department"]:
            continue
        ws.append([d.full_name, d.specialty_uz, d.department or "", d.room or "", m["count"], m["quality"], m["csat"],
                   m["empathy_avg"], m["nps"], m["communication_pct"],
                   m["on_time_pct"], m["thorough_pct"], m["satisfied_pct"], m["corruption_count"]])

    ws2 = wb.create_sheet("Barcha javoblar")
    ws2.append(["Sana", "Shifokor", "Mutaxassislik", "Boʻlim", "Til", "Muomala (1-5)", "Tushuntirish", "Vaqt", "Koʻrik",
                "Natija", "Tavsiya (1-10)", "Korrupsiya", "Izoh"])
    for r, d in rows:
        x = an.response_dict(r, d)
        ws2.append([x["created_at"], x["doctor"], x["specialty"], x["department"] or "", x["language"], x["q1_empathy"],
                    LABELS["q2_communication"][x["q2_communication"]], LABELS["q3_timeliness"][x["q3_timeliness"]],
                    LABELS["q4_thoroughness"][x["q4_thoroughness"]], LABELS["q5_outcome"][x["q5_outcome"]],
                    x["q6_nps"], "Ha" if x["q7_corruption"] else "Yoʻq", x["q8_comment"] or ""])

    for sheet in (ws, ws2):
        for cell in sheet[1]:
            cell.font, cell.fill = header_font, header_fill
        for col in sheet.columns:
            width = max(len(str(c.value or "")) for c in col[:200])
            sheet.column_dimensions[col[0].column_letter].width = min(max(10, width + 2), 60)
        sheet.freeze_panes = "A2"

    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)
    name = f"baholash_{f['date_from'] or 'boshidan'}_{f['date_to'] or date.today()}.xlsx"
    return StreamingResponse(buf, media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                             headers={"Content-Disposition": f'attachment; filename="{name}"'})


@app.get("/photo/{doctor_id}")
async def photo(doctor_id: int, _: str = Depends(require_user)):
    doctor = next((d for d in await an.all_doctors() if d.id == doctor_id), None)
    if doctor and doctor.photo_path:
        path = Path(doctor.photo_path)
        path = path if path.is_absolute() else BASE_DIR / path
        if path.is_file():
            return FileResponse(path)
    raise HTTPException(404)
