# Transaction Webhook Service

Python service that accepts payment-processor webhooks, acknowledges them immediately (`202` in well under 500ms), and processes each unique `transaction_id` once after a 30-second delay.

## Endpoints

| Method | Path | Purpose |
| --- | --- | --- |
| `GET` | `/` | Health check |
| `POST` | `/v1/webhooks/transactions` | Ingest webhook (`202 Accepted`) |
| `GET` | `/v1/transactions/{transaction_id}` | Lookup status (array of one row) |

Webhook body:

```json
{
  "transaction_id": "txn_abc123def456",
  "source_account": "acc_user_789",
  "destination_account": "acc_merchant_456",
  "amount": 1500,
  "currency": "INR"
}
```

## How it works

1. The webhook handler inserts a row with `status=PROCESSING` and returns `202`. It does not wait for processing.
2. A unique constraint on `transaction_id` makes retries idempotent: duplicates still get `202` and are not processed twice.
3. A background worker periodically marks rows `PROCESSED` once they are at least 30 seconds old, then sets `processed_at`.

Persisting first, then processing, means a restart does not lose accepted webhooks.

## Technical choices

- **FastAPI** — small, fast HTTP API with typed request/response models.
- **SQLAlchemy + PostgreSQL** — persistent storage and a unique constraint for idempotency. SQLite is used automatically if `DATABASE_URL` is unset (local/tests).
- **In-process worker** — no Redis/Celery. The 30s delay is simulated by waiting until `created_at + 30s` before flipping status, which stays correct across retries and restarts.

## Run locally

Python 3.11+.

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --reload --port 8000
```

Without Postgres, leave `DATABASE_URL` unset (or comment it out) to use a local SQLite file.

With Docker (API + Postgres):

```bash
docker compose up --build
```

## Test

```bash
pytest -q
```

Manual checks:

```bash
# health
curl -s http://localhost:8000/

# ingest (expect 202, fast)
curl -s -o /dev/null -w "%{http_code} %{time_total}\n" \
  -X POST http://localhost:8000/v1/webhooks/transactions \
  -H "Content-Type: application/json" \
  -d '{"transaction_id":"txn_abc123def456","source_account":"acc_user_789","destination_account":"acc_merchant_456","amount":1500,"currency":"INR"}'

# status: PROCESSING immediately, PROCESSED after ~30s
curl -s http://localhost:8000/v1/transactions/txn_abc123def456
```

Duplicate the same POST several times; the lookup still returns a single row.

## Deploy (Render)

The public API must be on the cloud. One path:

1. Push this repo to GitHub.
2. Create a [Render](https://render.com) account and use **Blueprint** with `render.yaml`, or create:
   - a **PostgreSQL** database
   - a **Web Service** (Python) with start command `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
3. Set `DATABASE_URL` from the Render Postgres connection string (use the **internal** URL if the API is also on Render).
4. Confirm `GET /` returns `HEALTHY`.

Public URL goes in the submission README once deployed:

```
https://YOUR-SERVICE.onrender.com
```
