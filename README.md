
# Transaction Webhook Service

A Python FastAPI service that receives payment transaction webhooks, acknowledges them immediately with HTTP 202 Accepted, and processes each unique transaction exactly once after a 30-second delay.

## Live Deployment

- **Live API:** https://confluencr-fullstack-engineer-assessment.onrender.com/
- **API Documentation:** https://confluencr-fullstack-engineer-assessment.onrender.com/docs
- **Database:** PostgreSQL (Render)

## 1. Features

- Immediate webhook acknowledgement using HTTP 202.
- Persistent transaction storage.
- Idempotent webhook handling using a unique transaction ID.
- Background processing after 30 seconds.
- Transaction status tracking.
- Health-check endpoint.
- PostgreSQL in production and SQLite for local development.
- Docker Compose support.

## 2. Technology Stack

| Component | Technology |
|---|---|
| Backend | Python, FastAPI |
| Database | PostgreSQL |
| ORM | SQLAlchemy |
| Local database | SQLite |
| Background processing | In-process worker |
| Server | Uvicorn |
| Containerization | Docker |
| Deployment | Render |
| Testing | Pytest |

## 3. Architecture & Design

### Request lifecycle

1. Payment processor sends a webhook.
2. FastAPI validates the incoming transaction payload.
3. The application inserts the transaction into the database with PROCESSING status.
4. The API immediately responds with HTTP 202 Accepted.
5. The background worker periodically checks pending transactions.
6. Transactions at least 30 seconds old are marked PROCESSED.
7. The processed_at timestamp is recorded.

### Architecture diagram

```text
Payment Processor
       |
       | POST Webhook
       v
   FastAPI API
       |
       v
  Request Validation
       |
       v
  PostgreSQL Database
       |
       | Insert PROCESSING
       v
  HTTP 202 Accepted
       |
       v
 Background Worker
       |
       | Check elapsed time
       v
 Update Transaction
       |
       v
  Status: PROCESSED
```

### Database schema

Transactions table:

| Column | Type | Description |
|---|---|---|
| id | Integer | Primary key |
| transaction_id | String | Unique transaction identifier |
| source_account | String | Source account |
| destination_account | String | Destination account |
| amount | Numeric | Transaction amount |
| currency | String | Currency code |
| status | String | PROCESSING / PROCESSED |
| created_at | DateTime | Transaction creation time |
| processed_at | DateTime | Processing completion time |

A unique database constraint on transaction_id prevents duplicate transaction records.

## 4. Setup Instructions

### Prerequisites

- Python 3.11+
- pip
- Git
- Docker (optional)
- PostgreSQL (optional for local development)

### Local installation

Clone the repository:

```bash
git clone YOUR_GITHUB_REPOSITORY_URL
cd Confluencr
```

Create a virtual environment:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

Install dependencies:

```bash
pip install -r requirements.txt
```

Configure environment variables:

```bash
cp .env.example .env
```

Leave DATABASE_URL unset to use SQLite locally, or configure it to use PostgreSQL.

Start the application:

```bash
uvicorn app.main:app --reload --port 8000
```

Application URL:

http://localhost:8000

Interactive API documentation:

http://localhost:8000/docs

### Docker setup

```bash
docker compose up --build
```

### Run tests

```bash
pytest -q
```

## 5. API Documentation

### GET /

Health-check endpoint.

Response: HTTP 200

```json
{
  "status": "HEALTHY",
  "current_time": "2026-11-03T01:08:21Z"
}
```

### POST /v1/webhooks/transactions

Accepts a transaction webhook.

Request:

```json
{
  "transaction_id": "txn_abc123def456",
  "source_account": "acc_user_789",
  "destination_account": "acc_merchant_456",
  "amount": 1500,
  "currency": "INR"
}
```

Response: HTTP 202 Accepted.

The API acknowledges the request without waiting for background processing.

Repeated requests with the same transaction_id are acknowledged without creating additional records.

### GET /v1/transactions/{transaction_id}

Retrieves the transaction status.

Response: HTTP 200

```json
[
  {
    "transaction_id": "txn_abc123def456",
    "source_account": "acc_user_789",
    "destination_account": "acc_merchant_456",
    "amount": 1500.0,
    "currency": "INR",
    "status": "PROCESSING",
    "created_at": "2026-11-03T01:17:27Z",
    "processed_at": null
  }
]
```

After processing, the status changes to PROCESSED and processed_at is populated.

If the transaction does not exist, the API returns HTTP 404.

### Authentication

The current assessment implementation does not require authentication. Webhook requests are accepted without an API key or bearer token.

## 6. Idempotency

The transaction_id column has a unique database constraint.

When an existing transaction ID is received:

- The API returns HTTP 202.
- No additional database record is created.
- The original transaction status and timestamps remain unchanged.
- The transaction is not processed a second time.

## 7. Assumptions & Trade-offs

### Assumptions

- Every transaction has a unique transaction_id.
- The webhook payload contains transaction_id, source_account, destination_account, amount, and currency.
- Processing is simulated using a 30-second delay.
- The required response is HTTP 202 for accepted and duplicate webhooks.

### Technical trade-offs

**In-process worker:** Avoids introducing Redis or Celery for a small assessment. However, it requires careful handling of multiple application instances and worker lifecycle.

**PostgreSQL persistence:** Keeps accepted transactions available across application restarts.

**SQLite locally:** Simplifies development and testing without requiring a PostgreSQL installation.

**Unique constraint:** Enforces idempotency at the database level rather than relying only on application-level checks.

**No authentication:** Kept simple in accordance with the current assessment requirements. A production webhook integration should verify signatures or use another trusted authentication mechanism.

## 8. Testing & Verification

The following scenarios were tested against the live Render deployment:

| Test | Result |
|---|---|
| Health endpoint | Passed |
| Webhook acknowledgement | HTTP 202 |
| Transaction persistence | Passed |
| Initial PROCESSING status | Passed |
| Processing after 30 seconds | Passed |
| Duplicate webhook | HTTP 202 |
| Duplicate record prevention | Passed |

## 9. Project Structure

```text
Confluencr/
├── app/
│   ├── main.py
│   ├── models.py
│   ├── database.py
│   └── worker.py
├── tests/
│   └── test_api.py
├── Dockerfile
├── docker-compose.yml
├── render.yaml
├── requirements.txt
├── .env.example
├── .gitignore
└── README.md
```

---

