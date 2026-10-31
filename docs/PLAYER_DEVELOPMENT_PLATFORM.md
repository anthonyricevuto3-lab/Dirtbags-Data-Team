# Player Development Platform — milestone 1

Upload a TrackMan CSV, store validated pitch records, and review a pitcher's outing in a React dashboard. The existing report generators and JSON player profiles are unchanged. This is an additional local application, not a migration of historical reports.

## Start with PostgreSQL (recommended)

Install Docker Desktop with Compose, then from the repository root:

```sh
docker compose up --build
```

Open http://localhost:5000. The app runs database migrations before starting. PostgreSQL is on the private Compose network; the application port binds only to your computer's loopback address. The database persists in the `player-development-db` volume. `docker compose down` preserves it; adding `-v` deletes the data.

For the first upload, choose `tests/fixtures/synthetic_outing.csv`, enter Game ID `demo-20261031-1`, date `2026-10-31`, and opponent `Demo Opponent`. Select **Demo Pitcher** and its outing. Upload again to verify zero inserted and six skipped pitches. The fixture is invented and contains no team data.

## Local development without Docker

From the repository root, create/activate a Python 3.12 virtual environment and install dependencies:

```sh
python -m venv .venv
# Windows PowerShell: .venv\Scripts\Activate.ps1
# macOS/Linux: source .venv/bin/activate
pip install -r requirements-platform.txt
alembic upgrade head
flask --app src.player_development.app:create_app run
```

With no `DATABASE_URL`, these commands use `development.db` (SQLite) for a lightweight local smoke test. PostgreSQL is the target database; SQLite tests alone do not establish PostgreSQL compatibility.

In another terminal:

```sh
cd frontend
npm ci
npm run dev
```

Open the Vite URL shown in the terminal. The development server proxies `/api` to Flask. Alternatively, `npm run build` creates the assets served directly by Flask at port 5000.

To use a separately installed PostgreSQL instance, set `DATABASE_URL` before running both Alembic and Flask:

```sh
# POSIX example; replace credentials and database with your local setup
export DATABASE_URL='postgresql+psycopg://USER:PASSWORD@localhost:5432/DATABASE'
```

PowerShell uses `$env:DATABASE_URL = 'postgresql+psycopg://...'`. Do not commit real credentials.

## Data contract

- One upload belongs to one game. The entered game ID/date/opponent are authoritative. Split multi-game exports before uploading. Use different IDs for doubleheaders; a player's outing is one player/game pair.
- Required pitch columns: `PitcherId` (preferred) or `Pitcher`, `PitchNo`, `TaggedPitchType` (or `AutoPitchType`), and `PitchCall`. Canonical equivalents from `TrackmanSchema` are supported.
- Supply `Pitcher` alongside `PitcherId` for display names. Name-only identity is supported with a visible warning: identical names cannot reliably distinguish players. This release assumes one TrackMan identity namespace.
- Pitch numbers must be positive integers unique per player/game. Reused pitch numbers from multiple sessions must be resolved before import.
- Optional measurements: `RelSpeed`, `SpinRate`, `InducedVertBreak`, `HorzBreak`, `PlateLocSide`, `PlateLocHeight`. Missing values stay NULL; nonnumeric/nonfinite measurements reject the upload.
- TrackMan `PlateLocSide`/`PlateLocHeight` are converted from feet to canonical inches. Canonical `plate_x`/`plate_z` are already inches. Movement is inches; velocity is mph; spin is rpm.
- `InducedVertBreak` is preferred; raw `VertBreak` is deliberately not treated as induced break. Verify vendor-specific aliases/units before using a new feed.
- The existing custom-tag rules and live/warmup filter are reused. When a file contains both Live and Warmup, only Live rows remain. Warmup-only bullpen files remain usable. No plate-appearance outcomes are inferred by the new importer.
- UTF-8 CSV, maximum 10 MB request / 50,000 pitch rows. Duplicate headers, inconsistent field counts, ambiguous aliases, and duplicate pitch identities inside one file reject the whole upload.

## Integrity and corrections

`players → outings ← games`, with `pitches → outings` and `pitches → imports → games`.

Foreign keys and unique constraints enforce identities. Each import has a SHA-256 file checksum; each pitch stores the normalized record used for equality checks and its original import ID. Raw CSV bytes are not persisted by this application.

A repeated file is a no-op. A reordered/overlapping file skips identical normalized pitches and inserts new ones. If any existing pitch identity has different stored values, the entire transaction rolls back with HTTP 409. No partial new pitches or import records survive. A concurrent uniqueness conflict is retried once in a fresh transaction.

This release intentionally has no correction editor. Resolve conflicts through a future reviewed correction workflow, not by inventing a new game ID. File bytes, ignored metadata, and source version histories are not a complete audit trail yet. Failed uploads return actionable errors but are not persisted in an import-history UI.

## API

| Method | Route | Result |
| --- | --- | --- |
| GET | `/api/health` | Database/schema availability |
| POST | `/api/imports` | Multipart `file`, `game_id`, `played_on`, `opponent`; inserted/skipped counts and warnings |
| GET | `/api/players` | Player identities and names |
| GET | `/api/players/:id/outings` | Outing history and pitch counts |
| GET | `/api/outings/:id` | SQL arsenal aggregates and pitch locations |

Whiff percentage is swinging strikes / swings, not swinging strikes / all pitches. Unknown calls make the affected group's whiff rate unavailable. No swings also yields NULL, not zero. Velocity averages exclude missing observations and include their sample count. Strikeout rate and times-through-order splits are not implemented because this milestone does not yet model completed plate appearances. The reference strike zone is a fixed ±8.5 inches / 18–42 inches rectangle, not a batter-specific judgment.

## Verification

```sh
python -m pytest tests/test_player_development.py -q
cd frontend
npm ci
npm run build
```

The test suite migrates a fresh SQLite database per test by default. For PostgreSQL, point `TEST_DATABASE_URL` at a **dedicated disposable database**. The fixture deletes all rows in the platform tables between tests. Never point it at real team data. GitHub Actions supplies a PostgreSQL 16 service and runs these tests plus the TypeScript/production build.

The pre-existing `tests/test_metrics.py` has three failures reproduced at base commit `31f7d47`: strike-rate fixture expectation, zone-unit expectation, and `Velocity AVG` vs `Velo AVG`. Those report tests and implementations are unchanged by this feature.

## Scope and next steps

Implemented: schema/migration, atomic import, deduplication/conflict detection, API, pitcher/outing selection, arsenal table, location chart, synthetic fixture, Compose and CI configuration.

Next: compare outings, coach notes/goals, authentication and permissions, a reviewed correction workflow, background imports, PDF integration, richer plate-appearance data, pagination and measured query optimization. No cloud hosting, user accounts, authorization, or private-team-data deployment is included. Keep this milestone local until access control is added. The Compose credentials are development-only.
