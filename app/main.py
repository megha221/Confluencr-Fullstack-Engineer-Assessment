import logging
from contextlib import asynccontextmanager
from datetime import datetime, timezone

from fastapi import Depends, FastAPI, HTTPException, Response, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.database import Base, engine, get_db
from app.models import Transaction
from app.schemas import HealthOut, TransactionOut, TransactionWebhook
from app.worker import start_worker, stop_worker

logging.basicConfig(level=logging.INFO)


@asynccontextmanager
async def lifespan(_: FastAPI):
    Base.metadata.create_all(bind=engine)
    start_worker()
    yield
    stop_worker()


app = FastAPI(title="Transaction Webhook Service", lifespan=lifespan)


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


@app.get("/", response_model=HealthOut)
def health():
    return HealthOut(status="HEALTHY", current_time=utcnow())


@app.post("/v1/webhooks/transactions", status_code=status.HTTP_202_ACCEPTED)
def ingest_transaction(payload: TransactionWebhook, db: Session = Depends(get_db)):
    txn = Transaction(
        transaction_id=payload.transaction_id,
        source_account=payload.source_account,
        destination_account=payload.destination_account,
        amount=payload.amount,
        currency=payload.currency,
        status="PROCESSING",
        created_at=utcnow(),
    )
    db.add(txn)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
    return Response(status_code=status.HTTP_202_ACCEPTED)


@app.get("/v1/transactions/{transaction_id}", response_model=list[TransactionOut])
def get_transaction(transaction_id: str, db: Session = Depends(get_db)):
    txn = db.query(Transaction).filter(Transaction.transaction_id == transaction_id).one_or_none()
    if txn is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="transaction not found")
    return [txn]
