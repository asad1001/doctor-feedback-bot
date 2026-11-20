# Doctor feedback bot (Bolalar milliy tibbiyot markazi)

A Telegram bot that collects anonymous patient feedback about individual doctors.
Every doctor's door banner has a QR code. Scanning it opens **the same bot** with
that doctor already selected, the patient picks a language (Uzbek, Russian,
English) and answers 8 short questions with buttons. Answers go into a database
that the analytics dashboard (next phase) will read.

## One bot for all doctors

You do **not** need a bot per doctor. Telegram supports "deep links":

```
https://t.me/<your_bot>?start=<doctor_code>
```

Each doctor gets a unique random code (for example `sxYjPyT6`). Their QR code
contains their own link, and when the patient presses **Start** the bot receives
the code and knows which doctor is being rated. 1 bot, 1 token, 1 database,
any number of doctors.

## 1. Create the bot in Telegram (2 minutes)

1. In Telegram open **@BotFather** and send `/newbot`.
2. Enter a display name, e.g. `BMTM Fikr-mulohaza`.
3. Enter a username that ends with `bot`, e.g. `bmtm_feedback_bot`.
4. BotFather replies with a **token** like `123456789:AA...`. Keep it secret.
5. Optional, but nice: `/setuserpic` (clinic logo), `/setdescription`
   (text shown before Start), `/setabouttext`.

## 2. Install and configure

Requires Python 3.10+.

```bash
cd doctor-feedback-bot
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt

cp .env.example .env               # Windows: copy .env.example .env
```

Edit `.env`:

* `BOT_TOKEN`: the token from BotFather
* `BOT_USERNAME`: the bot's username without `@`
* `ANON_SALT`: a long random string, generate with
  `python -c "import secrets; print(secrets.token_hex(32))"`

## 3. Add doctors and generate QR codes

Fill a CSV like `doctors.example.csv` (open/save it in Excel as **CSV UTF-8**):

| last_name | first_name | patronymic | specialty_uz | specialty_ru | specialty_en | department | room | photo |
|---|---|---|---|---|---|---|---|---|
| Karimova | Dilnoza | Rustamovna | Pediatr | Педиатр | Pediatrician | Pediatriya boʻlimi | 12 | photos/karimova.jpg |

`department` (boʻlim) powers the department view on the dashboard, and
`room` (kabinet) is shown in the bot and under the QR code.

`photo` is optional: if set, the bot shows the doctor's photo so the patient can
confirm they are rating the right person. Re-running the import updates
existing doctors instead of duplicating them.

```bash
python scripts/import_doctors.py doctors.csv
python scripts/generate_qr.py
```

`qr_codes/` now contains, per doctor, an `.svg` (vector, give this to the banner
designer) and a `.png` with the name underneath, plus `links.csv` with every
doctor's link.

> Each doctor's code is permanent. Don't delete `data/feedback.db` once banners
> are printed, or the printed QR codes will stop matching.

### Door banners

```bash
python scripts/generate_banners.py
```

Creates a print-ready A4 banner per doctor in `banners/` (photo, name,
specialty, room, logo, QR code). Open the `.html` file in Chrome or Edge,
press Ctrl+P, choose A4, margins "None", tick "Background graphics", and save
as PDF or print. Put photos in `photos/` (portrait, at least 1000 px tall).

If a banner was already printed with a code (e.g. on another computer), add
a `code` column to the CSV so the doctor keeps that exact QR code.

## 4. Run

```bash
python -m bot
```

Scan a QR code with your phone to test. For production, run it on a server
(any small VPS) as a service, e.g. with systemd or Docker, so it restarts on
reboot.

## 5. Management dashboard

A password-protected website with live analytics. It reads the same database
as the bot, so run it **alongside** the bot (a second terminal).

1. Add logins to `.env` (one or more, comma separated):
   ```
   DASHBOARD_USERS=director:StrongPassword1,quality:StrongPassword2
   DASHBOARD_SECRET=another-long-random-string
   ```
2. Start it in a second terminal (activate `.venv` first):
   ```
   python -m dashboard
   ```
3. Open **http://localhost:8000** and log in.

What it shows (UZ / RU / EN switch at the top):

* **Overview:** quality index, responses, CSAT, NPS, courtesy average,
  % seen on time, % fully explained, corruption reports, trend chart, NPS
  distribution and trend, waiting time by department, answer breakdown, best
  doctors and doctors needing attention, red banner for alerts in the last 24 h
* **Doctors:** sortable table of all doctors with every metric, click a row
  to open that doctor's page (trend, breakdown, all responses)
* **Comments:** all free-text feedback, newest first
* **Departments:** quality, CSAT, NPS and waiting times per department
* **Alerts:** corruption reports and very low ratings (filter: corruption only)
* **Filters:** period (7/30/90 days, year, all, custom dates) and specialty
* **Excel export** of the current filter (summary per doctor + all responses)
* **Live:** the page checks for new responses every 10 seconds

### Try it with demo data

```
python scripts/seed_demo.py            # 12 demo doctors, ~1000 responses
python scripts/seed_demo.py --remove   # delete them again before going live
```

### Metrics

* **Quality index (main KPI, HCAHPS-style "top-box")**: the share of best
  possible answers across Q1–Q5 (courtesy 5, fully explained, on time,
  sufficient exam, fully satisfied). 100% = every patient gave the top answer
  to every question. Doctors are ranked by it.
* **CSAT**: % of patients fully satisfied with the outcome (Q5).
* **NPS**: see below.

### NPS

Patients rate 1 to 10. Promoters = 9-10, detractors = 1-6.
NPS = % promoters − % detractors (from −100 to +100; above 50 is excellent).

## 6. Telegram alerts for management

The bot can instantly message a management Telegram group when a patient
answers **"Yes" to the corruption question**, rates courtesy **1-2**, or
rates recommendation **1-3**. Alerts contain the doctor and answers, never
the patient.

1. Create a Telegram group for management and add your bot to it.
2. In the group send `/chatid`. The bot replies with `ALERT_CHAT_ID=-100...`.
3. Put that line into `.env` and restart the bot.

## Deploy to Render (website + bot in one service)

On a server the bot does not use polling. The dashboard web service receives
Telegram messages on `/telegram/webhook`, so **one Render Web Service runs
both the website and the bot**. Render sets `RENDER_EXTERNAL_URL` itself; on
startup the app tells Telegram to send updates there.

1. Render → New → Web Service → your GitHub repo (or use `render.yaml`).
2. Build command: `pip install -r requirements.txt`
3. Start command: `uvicorn dashboard.app:app --host 0.0.0.0 --port $PORT`
4. Environment variables: `BOT_TOKEN`, `BOT_USERNAME`, `ANON_SALT`,
   `DASHBOARD_USERS`, `DASHBOARD_SECRET`, optional `ALERT_CHAT_ID`,
   and `PYTHON_VERSION=3.12.7`.
5. Deploy. The log should show `Telegram webhook set to https://...`.
6. **Stop `python -m bot` on your laptop.** While the server runs the bot,
   `python -m bot` refuses to start (use `--force` only if you want to take
   the bot back to your laptop; redeploy Render to give it back).

Notes for the free plan:
* The service sleeps after ~15 minutes without visitors. The first patient
  message wakes it, so the first answer can take up to a minute; after that
  it is instant.
* The free disk is not permanent: on every redeploy/restart the SQLite file
  goes back to the version in git, and new responses are lost. Fine for a
  demo; for real use create a Render PostgreSQL database and set
  `DATABASE_URL` to its connection string (Postgres is supported out of the box).

## Going live (24/7)

On a laptop the bot stops when the laptop sleeps. For real use, rent a small
Linux server (VPS, 1 GB RAM is enough; a provider in Uzbekistan is safest
for data rules), copy the project there, and run `python -m bot` and
`python -m dashboard` as services. Put the dashboard behind a domain with
HTTPS (e.g. Caddy or Nginx) and set `https_only=True` in `dashboard/app.py`.

## The patient flow

1. Scan QR → Telegram opens the bot → **Start**
2. Choose language: 🇺🇿 / 🇷🇺 / 🇬🇧
3. See the doctor's name, specialty (and photo), plus an anonymity note
4. Q1–Q7 as buttons (the same message updates, so the chat stays clean)
5. Q8 free text, or **Skip**
6. Thank-you message

## Anonymity and anti-spam

* The `responses` table stores **no** Telegram ID, name or phone number.
* To allow only **one rating per person per doctor per day**, the bot keeps a
  separate `submission_locks` table with a salted hash of the Telegram ID, the
  doctor and the date. Rows from previous days are deleted automatically, and
  the lock table is never linked to a response. This matters most for Q7
  (corruption), where patients must feel safe answering "Yes".
* Doctor codes are random, so nobody can guess other doctors' links.

## Data model (for the dashboard)

`doctors`: id, code, last_name, first_name, patronymic, specialty_uz/ru/en,
photo_path, is_active, created_at

`responses`: one row per completed survey

| column | values |
|---|---|
| doctor_id | → doctors.id |
| language | `uz` / `ru` / `en` |
| q1_empathy | 1–5 |
| q2_communication | `full` / `partial` / `none` |
| q3_timeliness | `on_time` / `waited_15_20` / `long_wait` |
| q4_thoroughness | `enough` / `partial` / `rushed` |
| q5_outcome | `full` / `partial` / `not` |
| q6_nps | 1–10 |
| q7_corruption | true = money/gift was asked or offered |
| q8_comment | text or empty |
| created_at | UTC timestamp |

Answers are stored as codes, not text, so results can be compared across
languages. Only completed surveys are saved.

SQLite is the default (zero setup). For the dashboard with several users,
switch to PostgreSQL by installing `asyncpg` and changing `DATABASE_URL`.

## Editing texts

All questions and translations are in `bot/texts.py`. You can reword labels
freely, but don't change the answer codes once real data exists.

## Project layout

```
bot/
  __main__.py   start the bot
  config.py     reads .env
  db.py         database models, anonymity + daily limit
  handlers.py   conversation flow
  texts.py      questions in uz / ru / en
  alerts.py     management alerts
dashboard/
  __main__.py   start the dashboard
  app.py        web server, login, API, Excel export
  analytics.py  metrics (NPS, averages, breakdowns, trends)
  static/       dashboard pages
scripts/
  import_doctors.py
  generate_qr.py
  seed_demo.py  demo data
doctors.example.csv
```
