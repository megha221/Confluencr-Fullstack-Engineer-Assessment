from datetime import datetime, timezone
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, field_serializer


class TransactionWebhook(BaseModel):
    transaction_id: str = Field(min_length=1, max_length=128)
    source_account: str = Field(min_length=1, max_length=128)
    destination_account: str = Field(min_length=1, max_length=128)
    amount: Decimal
    currency: str = Field(min_length=1, max_length=8)


def to_iso_z(value: datetime) -> str:
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


class TransactionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    transaction_id: str
    source_account: str
    destination_account: str
    amount: Decimal
    currency: str
    status: str
    created_at: datetime
    processed_at: datetime | None

    @field_serializer("amount")
    def serialize_amount(self, value: Decimal) -> float:
        return float(value)

    @field_serializer("created_at", "processed_at")
    def serialize_dt(self, value: datetime | None) -> str | None:
        if value is None:
            return None
        return to_iso_z(value)


class HealthOut(BaseModel):
    status: str
    current_time: datetime

    @field_serializer("current_time")
    def serialize_current_time(self, value: datetime) -> str:
        return to_iso_z(value)
