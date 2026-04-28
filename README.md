# Playto Pay Payout Engine

Mini payment infrastructure system built with:

- Django + Django REST Framework
- PostgreSQL
- Celery + Redis
- React + Vite + Tailwind + shadcn-style UI components

## Features

- Merchant ledger with `CREDIT` and `DEBIT` entries
- Balance computation from DB aggregation
- Idempotent payout creation
- Row-level locking with `SELECT FOR UPDATE`
- Payout state machine with refund-on-failure
- Celery-based background payout processing
- Frontend dashboard with polling payout status
- Seed command for demo merchants and balances
- Test coverage for idempotency, tasks, state transitions, and concurrency

## Project Structure

```text
core/                       Django settings and Celery bootstrap
payouts/                    Models, APIs, state machine, tasks, tests
frontend/                   React dashboard
docker-compose.yml          Local dev stack
README.md                   Setup and deployment guide
EXPLAINER.md                Architecture answers
```

## Local Setup

### 1. Backend

Create and activate a virtual environment, then install dependencies:

```bash
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

Set environment variables:

```env
DJANGO_SECRET_KEY=replace-me
DJANGO_DEBUG=True
DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1
DJANGO_TIME_ZONE=UTC

DB_ENGINE=django.db.backends.postgresql
POSTGRES_DB=payout_engine
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_CONN_MAX_AGE=60

REDIS_URL=redis://127.0.0.1:6379/0
CELERY_BROKER_URL=redis://127.0.0.1:6379/0
CELERY_RESULT_BACKEND=django-db
CELERY_TASK_TIME_LIMIT=1800

CORS_ALLOWED_ORIGINS=http://localhost:5173,http://127.0.0.1:5173
CORS_ALLOW_CREDENTIALS=True
```

Run migrations and seed demo data:

```bash
python manage.py migrate
python manage.py seed
```

Start the Django API:

```bash
python manage.py runserver
```

### 2. Celery worker

In a separate terminal:

```bash
celery -A core worker -l info
```

### 3. Frontend

```bash
cd frontend
npm install
```

Set the frontend API URL:

```env
VITE_API_BASE_URL=http://127.0.0.1:8000/api/v1
```

Start the frontend:

```bash
npm run dev
```

## API Endpoints

- `GET /api/v1/merchants/<id>/balance`
- `POST /api/v1/payouts`
- `GET /api/v1/payouts?merchant_id=<id>`
- `GET /api/v1/ledger?merchant_id=<id>`

### Sample payout request

```json
{
  "merchant_id": 1,
  "amount_paise": 6000,
  "bank_account_id": "bank_acc_001",
  "idempotency_key": "merchant-1-001"
}
```

## Running Tests

SQLite works for most tests:

```bash
set DB_ENGINE=django.db.backends.sqlite3
python manage.py test payouts
```

Note: the concurrency test is intentionally skipped on SQLite because proper `SELECT FOR UPDATE` behavior requires a database such as PostgreSQL.

## Docker Compose

Run the local stack:

```bash
docker compose up --build
```

Services included:

- `db` - PostgreSQL
- `redis` - Redis
- `backend` - Django API
- `worker` - Celery worker
- `frontend` - Vite dev server

## Deploy Backend to Render

Use Render if you want a managed web service plus managed Postgres and Redis.

### Recommended services

- 1 Render Web Service for Django
- 1 Render Background Worker for Celery
- 1 Render Postgres database
- 1 Render Redis instance

### Backend build command

```bash
pip install -r requirements.txt
python manage.py migrate
```

### Backend start command

```bash
gunicorn core.wsgi:application
```

### Worker start command

```bash
celery -A core worker -l info
```

### Render env vars

```env
DJANGO_SECRET_KEY=...
DJANGO_DEBUG=False
DJANGO_ALLOWED_HOSTS=<your-render-domain>
DJANGO_TIME_ZONE=UTC

POSTGRES_DB=...
POSTGRES_USER=...
POSTGRES_PASSWORD=...
POSTGRES_HOST=...
POSTGRES_PORT=5432
POSTGRES_CONN_MAX_AGE=60

REDIS_URL=...
CELERY_BROKER_URL=...
CELERY_RESULT_BACKEND=django-db

CORS_ALLOWED_ORIGINS=https://<your-vercel-domain>
CORS_ALLOW_CREDENTIALS=True
```

## Deploy Backend to Railway

Railway is also a good fit for this stack.

### Railway services

- Django web service
- Celery worker service
- PostgreSQL plugin
- Redis plugin

### Web start command

```bash
gunicorn core.wsgi:application
```

### Worker start command

```bash
celery -A core worker -l info
```

Set the same environment variables as the Render section, using Railway-provided Postgres and Redis connection values.

## Deploy Frontend to Vercel

Import the `frontend/` directory as a Vercel project.

### Vercel settings

- Framework preset: `Vite`
- Build command: `npm run build`
- Output directory: `dist`

### Frontend env var

```env
VITE_API_BASE_URL=https://<your-backend-domain>/api/v1
```

After deploy, update the backend CORS setting so it includes the Vercel domain.

## Seed Live Database

After the backend is deployed and migrations are complete, run:

```bash
python manage.py seed
```

How you run it depends on platform:

- Render: open a shell for the web service and run the command
- Railway: open the service shell and run the command

This command is idempotent for the seeded merchants and seeded credit entries.

## Production Notes

- Use PostgreSQL in production, not SQLite
- Run Celery worker separately from the Django web service
- Keep `DJANGO_DEBUG=False`
- Restrict `DJANGO_ALLOWED_HOSTS`
- Restrict `CORS_ALLOWED_ORIGINS` to your frontend domain
- Use a strong `DJANGO_SECRET_KEY`

## What I could not do from here

I prepared the deployment docs and commands, but I did not actually deploy to Render, Railway, or Vercel because that requires access to your cloud accounts and credentials.
