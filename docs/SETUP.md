# WorkHours Enterprise — Complete Setup Guide

This guide walks you through every step to get the project running on a fresh
machine — from installing system dependencies to seeing the login page in your
browser. Nothing is assumed except that you have a Linux or macOS machine.

---

## Prerequisites

| Requirement | Minimum version | Check |
|---|---|---|
| Python | 3.12+ | `python3 --version` |
| PostgreSQL | 14+ | `psql --version` |
| pip | bundled with Python | `pip --version` |
| git | any | `git --version` |

---

## Step 1 — Install Python 3.12+

### Ubuntu / Debian
```bash
sudo apt update
sudo apt install -y python3.12 python3.12-venv python3.12-dev
```

Confirm:
```bash
python3.12 --version
# Python 3.12.x
```

### macOS (with Homebrew)
```bash
brew install python@3.12
python3.12 --version
```

---

## Step 2 — Install PostgreSQL 16

### Ubuntu 22.04 (Jammy)

The default Ubuntu repos ship PostgreSQL 14. Use the official PGDG repo for 16:

```bash
# 2a. Install helper packages
sudo apt install -y curl ca-certificates

# 2b. Import the PGDG signing key
sudo install -d /usr/share/postgresql-common/pgdg
sudo curl -fsSLo /usr/share/postgresql-common/pgdg/apt.postgresql.org.asc \
    https://www.postgresql.org/media/keys/ACCC4CF8.asc

# 2c. Add the PGDG repository for your Ubuntu release
sudo sh -c 'echo "deb [signed-by=/usr/share/postgresql-common/pgdg/apt.postgresql.org.asc] \
https://apt.postgresql.org/pub/repos/apt $(lsb_release -cs)-pgdg main" \
> /etc/apt/sources.list.d/pgdg.list'

# 2d. Update and install
sudo apt update
sudo apt install -y postgresql-16 postgresql-client-16

# 2e. Start and enable
sudo systemctl start postgresql
sudo systemctl enable postgresql
```

Confirm:
```bash
psql --version
# psql (PostgreSQL) 16.x
sudo systemctl status postgresql
# Active: active (running)
```

### Ubuntu 24.04 (Noble)

PostgreSQL 16 ships in the default repos on Ubuntu 24.04:

```bash
sudo apt update
sudo apt install -y postgresql-16 postgresql-client-16
sudo systemctl start postgresql
sudo systemctl enable postgresql
```

### macOS (with Homebrew)
```bash
brew install postgresql@16
brew services start postgresql@16
echo 'export PATH="/opt/homebrew/opt/postgresql@16/bin:$PATH"' >> ~/.zshrc
source ~/.zshrc
psql --version
```

---

## Step 3 — Create the database user and database

All commands below run as the `postgres` superuser.

```bash
sudo -u postgres psql
```

Inside the psql shell, run these four lines exactly:

```sql
CREATE USER workhours WITH PASSWORD 'workhours';
CREATE DATABASE workhours_db OWNER workhours;
GRANT ALL PRIVILEGES ON DATABASE workhours_db TO workhours;
\q
```

Verify the connection works:
```bash
psql -U workhours -d workhours_db -h localhost -c "SELECT current_user, current_database();"
# Enter password: workhours
# current_user | current_database
# -------------+-----------------
# workhours    | workhours_db
```

> **Note for production:** Change the password `workhours` to something strong.
> Update `DATABASE_URL` in your `.env` accordingly.

---

## Step 4 — Clone / extract the project

If you received the project as a ZIP file (`workhours-enterprise.zip`):

```bash
unzip workhours-enterprise.zip
cd workhours-enterprise
```

If it's in a Git repository:
```bash
git clone <repo-url>
cd workhours-enterprise
```

Confirm the structure:
```bash
ls
# app/  ui/  alembic/  tests/  docs/  requirements.txt  README.md ...
```

---

## Step 5 — Create a Python virtual environment

Always use a virtual environment — never install into the system Python.

```bash
python3.12 -m venv venv
source venv/bin/activate
```

You should see `(venv)` at the start of your prompt. Every command from here
onward runs inside this activated environment.

Upgrade pip first to avoid old-resolver bugs:
```bash
pip install --upgrade pip
```

---

## Step 6 — Install Python dependencies

```bash
pip install -r requirements.txt
```

This installs FastAPI, SQLAlchemy, Alembic, NiceGUI, JWT libraries, pytest,
and all other packages listed in `requirements.txt`. Expected time: 1–3 minutes.

Confirm the key packages installed correctly:
```bash
pip show fastapi sqlalchemy nicegui alembic passlib bcrypt
```

You should see version numbers for each. Pay attention to `bcrypt` — it must
show **4.0.1** (the version pinned in `requirements.txt`). If it shows 4.1+
password hashing will break with a `module 'bcrypt' has no attribute '__about__'`
error at runtime:

```bash
pip show bcrypt | grep Version
# Version: 4.0.1   ← correct
```

---

## Step 7 — Configure environment variables

Copy the example file and edit it:

```bash
cp .env.example .env
```

Open `.env` in any editor:
```bash
nano .env       # or: vim .env / code .env
```

There are three things you **must** change before the app will run:

### 7a. Generate a real SECRET_KEY

```bash
python3 -c "import secrets; print(secrets.token_urlsafe(64))"
```

Copy the output (a long random string) and paste it as the `SECRET_KEY` value.

### 7b. Set the DATABASE_URL

If you used the exact username, password, and database name from Step 3, the
default value already works:

```
DATABASE_URL=postgresql+psycopg2://workhours:workhours@localhost:5432/workhours_db
```

If you used different credentials, update this line:
```
DATABASE_URL=postgresql+psycopg2://YOUR_USER:YOUR_PASSWORD@localhost:5432/YOUR_DB_NAME
```

### 7c. Leave all other values as-is for local development

Your final `.env` should look like this (with your own `SECRET_KEY`):

```
APP_NAME=WorkHours Enterprise
APP_ENV=development
DEBUG=true

DATABASE_URL=postgresql+psycopg2://workhours:workhours@localhost:5432/workhours_db
DB_POOL_MIN=5
DB_POOL_MAX=20

SECRET_KEY=<your-generated-64-character-random-string>
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7
BCRYPT_ROUNDS=12

CORS_ORIGINS=["http://localhost:8000","http://localhost:8080"]

DEFAULT_PAGE_SIZE=20
MAX_PAGE_SIZE=100

LOGIN_RATE_LIMIT=10/minute

UI_HOST=0.0.0.0
UI_PORT=8080
API_BASE_URL=http://localhost:8000/api/v1
```

---

## Step 8 — Run database migrations

This creates all five tables and seeds demo data (1 admin, 5 employees, 5
projects, 10 sample work entries):

```bash
alembic upgrade head
```

Expected output:
```
INFO  [alembic.runtime.migration] Context impl PostgreSQLImpl.
INFO  [alembic.runtime.migration] Will assume non-transactional DDL.
INFO  [alembic.runtime.migration] Running upgrade  -> 0001, create users table
INFO  [alembic.runtime.migration] Running upgrade 0001 -> 0002, create projects table
INFO  [alembic.runtime.migration] Running upgrade 0002 -> 0003, create work_entries table
INFO  [alembic.runtime.migration] Running upgrade 0003 -> 0004, create audit_logs table
INFO  [alembic.runtime.migration] Running upgrade 0004 -> 0005, create refresh_tokens table
INFO  [alembic.runtime.migration] Running upgrade 0005 -> 0006, seed initial data
```

Verify the tables and seed data were created:
```bash
psql -U workhours -d workhours_db -h localhost
```

Inside psql:
```sql
\dt
-- Should show: users, projects, work_entries, audit_logs, refresh_tokens

SELECT username, role FROM users;
--  username  |   role
-- -----------+----------
--  admin     | admin
--  mitanshu  | employee
--  priya     | employee
--  rahul     | employee
--  sneha     | employee
--  arjun     | employee

\q
```

---

## Step 9 — Run the backend API server

Open **Terminal 1** and run:

```bash
source venv/bin/activate       # if not already active
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Expected output:
```
INFO:     Started server process [xxxxx]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
```

Test it:
```bash
curl http://localhost:8000/health
# {"status":"ok"}
```

The interactive API docs are now available at:
- **Swagger UI:** http://localhost:8000/docs
- **ReDoc:** http://localhost:8000/redoc

Leave this terminal running.

---

## Step 10 — Run the frontend UI server

Open **Terminal 2** and run:

```bash
cd workhours-enterprise         # make sure you're in the project root
source venv/bin/activate
python -m ui.main
```

Expected output:
```
NiceGUI ready to go on http://0.0.0.0:8080, and http://0.0.0.0:8080
```

---

## Step 11 — Open the application in your browser

Go to: **http://localhost:8080**

You will be redirected to the login page automatically.

### Demo accounts (all use password `ChangeMe123`)

| Username | Role | What you can do |
|---|---|---|
| `admin` | Admin | Full access: approve/reject, manage users/projects, view reports and audit log |
| `mitanshu` | Employee | Submit hours, view own history |
| `priya` | Employee | Submit hours, view own history |
| `rahul` | Employee | Submit hours, view own history |
| `sneha` | Employee | Submit hours, view own history |
| `arjun` | Employee | Submit hours, view own history |

> **Important:** Change all passwords immediately if you are running this on
> any non-local machine. Any seeded password left as `ChangeMe123` is a
> security risk.

---

## Step 12 — Run the test suite (optional but recommended)

In a third terminal (or after stopping the servers):

```bash
source venv/bin/activate
pytest tests/ -v
```

Expected result:
```
tests/integration/test_entry_business_rules.py::test_duplicate_entry_raises_conflict_error PASSED
tests/integration/test_entry_business_rules.py::test_different_project_same_day_is_allowed PASSED
tests/integration/test_entry_business_rules.py::test_employee_cannot_see_another_employees_entries PASSED
tests/integration/test_entry_business_rules.py::test_employee_cannot_bypass_scoping_by_passing_another_employee_id PASSED
tests/integration/test_entry_business_rules.py::test_admin_can_see_all_employees_entries PASSED
tests/integration/test_entry_concurrency.py::test_unique_constraint_enforced_by_database_independent_of_application_precheck PASSED
tests/integration/test_entry_concurrency.py::test_hours_check_constraint_enforced_by_database PASSED
tests/integration/test_ui_pages_render.py::test_login_page_renders PASSED
tests/integration/test_ui_pages_render.py::test_login_form_submit_calls_api_with_entered_credentials PASSED
tests/integration/test_ui_pages_render.py::test_employee_dashboard_redirects_when_logged_out PASSED
tests/integration/test_ui_pages_render.py::test_admin_dashboard_redirects_when_logged_out PASSED
tests/integration/test_ui_pages_render.py::test_employee_dashboard_redirects_on_genuinely_expired_session PASSED

12 passed in x.xxs
```

---

## Troubleshooting

### `connection refused` on port 5432
PostgreSQL is not running. Fix:
```bash
sudo systemctl start postgresql
sudo systemctl status postgresql
```

### `FATAL: password authentication failed for user "workhours"`
The user or password doesn't match what's in `.env`. Re-check Step 3 and Step 7b.
You can reset the password inside psql:
```bash
sudo -u postgres psql
ALTER USER workhours WITH PASSWORD 'workhours';
\q
```

### `module 'bcrypt' has no attribute '__about__'`
The wrong bcrypt version is installed. Fix:
```bash
pip install "bcrypt==4.0.1"
pip show bcrypt | grep Version
# Version: 4.0.1
```

### `alembic upgrade head` fails with `relation already exists`
The tables already exist from a previous run. Either drop and recreate the
database, or check the migration state:
```bash
alembic current          # shows which migration is currently applied
alembic history          # shows the full migration chain
```

To start completely fresh:
```bash
sudo -u postgres psql
DROP DATABASE workhours_db;
CREATE DATABASE workhours_db OWNER workhours;
GRANT ALL PRIVILEGES ON DATABASE workhours_db TO workhours;
\q
alembic upgrade head
```

### `ModuleNotFoundError: No module named 'app'`
You're running Python from the wrong directory. Always run commands from the
project root (the folder that contains `app/`, `ui/`, `alembic/`, etc.) and
with the virtual environment activated:
```bash
cd workhours-enterprise
source venv/bin/activate
```

### `address already in use` on port 8000 or 8080
Another process is occupying the port. Find and kill it:
```bash
# Port 8000 (backend)
lsof -i :8000
kill -9 <PID>

# Port 8080 (frontend)
lsof -i :8080
kill -9 <PID>
```

Or change the ports in `.env`:
```
UI_PORT=8090
API_BASE_URL=http://localhost:8001/api/v1
```
And start uvicorn on the new port: `uvicorn app.main:app --port 8001`

### NiceGUI shows `Storage secret missing`
The `SECRET_KEY` in your `.env` is still the placeholder value. Follow Step 7a
to generate a real one and paste it in.

---

## Quick start cheat-sheet (after first-time setup)

Once everything is installed and configured, starting the project in future
sessions is just:

**Terminal 1 — Backend:**
```bash
cd workhours-enterprise
source venv/bin/activate
uvicorn app.main:app --reload --port 8000
```

**Terminal 2 — Frontend:**
```bash
cd workhours-enterprise
source venv/bin/activate
python -m ui.main
```

Then open **http://localhost:8080**.

---

## Development tools (optional)

Run the linter:
```bash
ruff check app/ ui/
```

Auto-format:
```bash
black app/ ui/
isort --profile black app/ ui/
```

Type-check:
```bash
mypy app/ --ignore-missing-imports
```

Generate a new migration after changing a model:
```bash
alembic revision --autogenerate -m "describe your change"
alembic upgrade head
```

Roll back the last migration:
```bash
alembic downgrade -1
```
