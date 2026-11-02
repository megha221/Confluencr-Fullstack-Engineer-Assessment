import os

os.environ["DATABASE_URL"] = "sqlite:///./test_transactions.db"
os.environ["PROCESS_DELAY_SECONDS"] = "1"
os.environ["WORKER_POLL_SECONDS"] = "0.1"

from pathlib import Path

from fastapi.testclient import TestClient

from app.config import settings

settings.database_url = os.environ["DATABASE_URL"]
settings.process_delay_seconds = 1
settings.worker_poll_seconds = 0.1

from app.database import Base, engine
from app.main import app

PAYLOAD = {
    "transaction_id": "txn_abc123def456",
    "source_account": "acc_user_789",
    "destination_account": "acc_merchant_456",
    "amount": 1500,
    "currency": "INR",
}


def setup_module():
    Path("test_transactions.db").unlink(missing_ok=True)
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)


def teardown_module():
    Path("test_transactions.db").unlink(missing_ok=True)


def test_health_and_webhook_flow():
    with TestClient(app) as client:
        health = client.get("/")
        assert health.status_code == 200
        body = health.json()
        assert body["status"] == "HEALTHY"
        assert body["current_time"].endswith("Z")

        accepted = client.post("/v1/webhooks/transactions", json=PAYLOAD)
        assert accepted.status_code == 202

        duplicate = client.post("/v1/webhooks/transactions", json=PAYLOAD)
        assert duplicate.status_code == 202

        pending = client.get("/v1/transactions/txn_abc123def456")
        assert pending.status_code == 200
        rows = pending.json()
        assert len(rows) == 1
        assert rows[0]["status"] == "PROCESSING"
        assert rows[0]["processed_at"] is None

        import time

        deadline = time.time() + 5
        status = "PROCESSING"
        while time.time() < deadline:
            rows = client.get("/v1/transactions/txn_abc123def456").json()
            status = rows[0]["status"]
            if status == "PROCESSED":
                assert rows[0]["processed_at"] is not None
                break
            time.sleep(0.2)
        assert status == "PROCESSED"

        missing = client.get("/v1/transactions/does-not-exist")
        assert missing.status_code == 404
