"""Server-controlled contracts for bounded warehouse execution."""

from datetime import datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class WarehouseQueryRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    operation: Literal["products", "assertions", "comparison"]
    ids: list[str] = Field(min_length=1, max_length=20)
    recorded_from: datetime
    recorded_before: datetime
    limit: int = Field(default=250, ge=1, le=500)
    maximum_bytes_billed: int = Field(default=64 * 1024 * 1024, ge=10 * 1024 * 1024, le=64 * 1024 * 1024)
    idempotency_key: str = Field(min_length=8, max_length=128, pattern=r"^[A-Za-z0-9_.:-]+$")

    @model_validator(mode="after")
    def validate_read(self):
        self.to_read()
        return self

    def to_read(self):
        from packages.knowledge.bigquery_reader import SemanticRead

        return SemanticRead(self.operation, tuple(self.ids), self.recorded_from,
                            self.recorded_before, self.limit, self.maximum_bytes_billed)


class WarehousePricePolicy(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: Literal["warehouse-price-1"] = "warehouse-price-1"
    pricing_model: Literal["on_demand"] = "on_demand"
    public_reference_uri: Literal["https://cloud.google.com/bigquery/pricing"]
    public_reference_usd_per_tib: Decimal = Field(gt=0)
    public_reference_observed_at: datetime | None = None
    account_currency: Literal["USD"] | None = None
    account_on_demand_verified: bool = False
    verified_upper_bound_usd_per_tib: Decimal | None = Field(default=None, gt=0, le=10000)
    verification_evidence_ref: str | None = Field(default=None, max_length=1000)
    verified_at: datetime | None = None
    valid_until: datetime | None = None

    @model_validator(mode="after")
    def aware_dates(self):
        for value in (self.public_reference_observed_at, self.verified_at, self.valid_until):
            if value is not None and (value.tzinfo is None or value.utcoffset() is None):
                raise ValueError("Pricing dates must include a timezone")
        return self


class WarehouseRuntimeTask(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: Literal["warehouse-runtime-task-1"] = "warehouse-runtime-task-1"
    charter_version: Literal["1.6"] = "1.6"
    profile_id: Literal["warehouse_semantic_reader"] = "warehouse_semantic_reader"
    profile_revision: Literal[1] = 1
    objective: str = "Read bounded, source-linked warehouse records without arbitrary SQL or publication authority."
    inputs: list[dict[str, str | int]] = Field(min_length=1, max_length=20)
    acceptance_criteria: list[str] = [
        "Use the fixed semantic query and exact recorded time window.",
        "Reserve the maximum query cost in the shared experiment ledger.",
        "Do not substitute local rows for unavailable warehouse results.",
    ]
    risk: Literal["medium"] = "medium"
    permissions: list[Literal["warehouse.read"]] = ["warehouse.read"]
    idempotency_key: str
    query_fingerprint: str
    maximum_bytes_billed: int
