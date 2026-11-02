import logging
import threading
import time
from datetime import datetime, timedelta, timezone

from sqlalchemy import update

from app.config import settings
from app.database import SessionLocal
from app.models import Transaction

logger = logging.getLogger(__name__)

_stop = threading.Event()
_thread: threading.Thread | None = None


def process_due_transactions() -> int:
    cutoff = datetime.now(timezone.utc) - timedelta(seconds=settings.process_delay_seconds)
    now = datetime.now(timezone.utc)

    with SessionLocal() as db:
        result = db.execute(
            update(Transaction)
            .where(Transaction.status == "PROCESSING")
            .where(Transaction.created_at <= cutoff)
            .values(status="PROCESSED", processed_at=now)
        )
        db.commit()
        return result.rowcount or 0


def _run() -> None:
    while not _stop.is_set():
        try:
            processed = process_due_transactions()
            if processed:
                logger.info("processed %s transaction(s)", processed)
        except Exception:
            logger.exception("worker failed")
        _stop.wait(settings.worker_poll_seconds)


def start_worker() -> None:
    global _thread
    if _thread and _thread.is_alive():
        return
    _stop.clear()
    _thread = threading.Thread(target=_run, name="transaction-worker", daemon=True)
    _thread.start()


def stop_worker() -> None:
    _stop.set()
    if _thread:
        _thread.join(timeout=2)
