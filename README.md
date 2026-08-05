# DuxOS Water Monitoring System

Ariana Residency CHS's water monitoring + staff attendance system.

**Stack:** static HTML/CSS/JS frontend (unchanged), FastAPI backend, PostgreSQL
database, deployed on Railway. Originally built on Google Apps Script +
Google Sheets; migrated to this stack while preserving every existing
workflow (see "Migration history" below).

## Architecture

```
index.html  →  FastAPI (app/)  →  PostgreSQL
 (static)       REST API           (SQLAlchemy models, Alembic migrations)
```

- **Frontend** (`index.html`) — two independent SPA modules in one page,
  switched by the "Water Monitoring / Attendance" toggle at the top. All
  DOM/CSS/view logic is untouched from the original; only the network layer
  (`API_URL`/`ATT_API_URL`, `submitToBackend`, `loadDashboard`, `apiGet`,
  `apiPost`) talks to the new backend instead of Google Apps Script.
  - **Water Monitoring** (`App`): staff-PIN-gated Meter Reading and Tank
    Status forms, plus a public read-only Dashboard.
  - **Attendance** (`Att`): QR/PIN check-in, a live Duty Board, and a
    PIN-gated Admin panel (staff CRUD, QR codes, attendance log/export).
- **Backend** (`app/`) — FastAPI, SQLAlchemy 2.x, Pydantic v2. Fully isolated
  routers: `app/routers/water.py` (meter/tank/dashboard),
  `app/routers/attendance.py` (staff/check-in/admin), `app/routers/health.py`.
  Response field names deliberately mirror the original Apps Script API
  (camelCase, e.g. `wingA`, `ugDomesticAB`) so the frontend's request/response
  handling didn't need to change.
- **Database** — PostgreSQL. Six tables: `meter_readings`, `tank_status`,
  `staff`, `attendance` (FK → `staff`), `wings`, `app_config`. Schema in
  `app/models.py`, migrations in `alembic/versions/`.
- **`Code.gs`** — the original Apps Script backend, kept in the repo as
  historical reference / rollback path. No longer deployed.

## Local development

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # point DATABASE_URL at a local/dev Postgres
alembic upgrade head
uvicorn app.main:app --reload
```

Serve the frontend separately as a static file (`npm start`, which runs
`npx serve .`), or open `index.html` directly — just make sure `WEB_APP_URL`
near the top of the first `<script>` block points at wherever the backend
is running.

Interactive API docs are auto-generated at `/docs` (Swagger UI) and `/redoc`
whenever the backend is running.

## Railway deployment

The project lives in the `humble-comfort` Railway project as two services:
`Postgres-roie` (the database) and `duxos-water-backend` (this API). The
existing `duxos-water-monitoring` service continues to serve the static
frontend.

1. Provision a Postgres database in the project (Railway does this with
   `railway add -d postgres`, or via the dashboard).
2. Create the backend service and set its environment variables — at
   minimum `DATABASE_URL` referencing the Postgres service
   (`${{Postgres-roie.DATABASE_URL}}` in Railway's variable syntax).
3. Deploy: `railway up -s duxos-water-backend`. The Dockerfile's `CMD` runs
   `alembic upgrade head` before starting `uvicorn`, so every deploy
   auto-applies any new migrations.
4. Generate a public domain for the service (`railway domain -s
   duxos-water-backend`) and update `WEB_APP_URL` in `index.html` to match.

### Environment variables

| Variable | Default | Purpose |
|---|---|---|
| `DATABASE_URL` | `postgresql+psycopg2://postgres:postgres@localhost:5432/postgres` | Postgres connection string. Railway injects this automatically when Postgres is referenced. |
| `DEFAULT_ADMIN_PIN` | `1234` | Fallback Attendance admin PIN, used only if no `pin` row exists yet in `app_config`. |
| `TIMEZONE` | `Asia/Kolkata` | Timezone used for all "today" / session-window calculations (matches the original Apps Script deployment's `Session.getScriptTimeZone()`). |
| `CORS_ORIGINS` | `*` | Comma-separated allowed origins. |

## Database migrations

Schema changes go through Alembic:

```bash
alembic revision --autogenerate -m "describe the change"
alembic upgrade head
```

## Data migration from Excel

`scripts/migrate_excel.py` is a standalone, re-runnable tool that imports a
Google Sheets Excel export (Meter_Readings, Tank_Status, Att_Staff,
Att_Attendance sheets) into Postgres:

```bash
python scripts/migrate_excel.py --file "/path/to/export.xlsx" [--dry-run]
```

It validates every row, skips anything already imported (checked against
the same natural keys the database enforces uniqueness on — safe to re-run),
and prints an imported/skipped/failed report per sheet. `Att_Config` and
`Staff_Directory` are intentionally not migrated: the former had no saved
rows in production (the app was still running on hardcoded defaults, which
the backend also falls back to), and the latter is empty and unused by any
code path.

Note: the live Google Sheet's `Att_Attendance` tab never actually had a
`Shift` column, even though the app writes/expects one — historical
attendance rows import with `shift = NULL` rather than a guessed value.

## Access codes

- **Water Monitoring staff PINs** are hardcoded in `index.html`
  (`STAFF_PINS`) — a soft deterrent against casual/resident access, not
  real security, since anyone can view the page source. Don't use this to
  gate anything sensitive.
- **Attendance staff codes** are per-person, generated and stored server-side
  (visible to admins in the Admin → Staff tab).
- **Attendance admin PIN** (default `1234`, stored in `app_config`) is
  enforced server-side: every admin action that adds/removes staff, edits
  config, or clears data requires the correct PIN, checked in
  `app/routers/attendance.py`. The raw PIN is never sent to the browser —
  the client only gets a yes/no from `/api/attendance/verify-pin`.

## Developer notes

- The Attendance and Water Monitoring modules are fully isolated — separate
  tables, separate routers, no shared queries. Neither can break the other.
- `staff` uses soft delete (`deleted_at`), not a hard `DELETE` — this keeps
  `attendance` rows' foreign key valid forever and means a removed staff
  member's name still resolves correctly in historical logs (an improvement
  over the Sheets version, which hard-deleted the row and fell back to
  showing "(removed staff)").
- New Meter Reading / Tank Status submissions store `reading_date`/
  `reading_time` from the server clock at insert time, not by parsing the
  client's locale-formatted display string (which varies by device locale
  and was never authoritative in the original design either — the Apps
  Script backend's own "today" logic already relied on its server-generated
  timestamp, not the client-sent date/time text).

## Migration history

This project was originally built on Google Apps Script + Google Sheets
(see `Code.gs`). It was migrated to FastAPI + PostgreSQL on Railway with:
- Zero changes to the frontend's DOM, CSS, or view logic — only its network
  layer was repointed.
- Zero data loss — all production rows (verified by exact count and spot
  checks against the Google Sheets export) were imported.
- The same admin-PIN security model already hardened in `Code.gs`
  (PIN never sent to the client, checked server-side on every mutating
  admin action) carried over identically to the new backend.
