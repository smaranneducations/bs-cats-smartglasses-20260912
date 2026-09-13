"""Authenticated warehouse execution; no budget-arming or billing-edit route."""

import os
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException

from packages.contracts.warehouse_execution import WarehousePricePolicy, WarehouseQueryRequest
from packages.knowledge.bigquery_reader import (
    AdmissionDenied, BigQueryTransport, ExistingGcloudIdentity, WarehouseError,
)
from packages.knowledge.warehouse_execution import WarehouseExecutionService
from services.api.src.runtime_routes import local_ledger

ROOT = Path(__file__).resolve().parents[3]


def warehouse_router(get_store, require_access):
    router = APIRouter()

    def service():
        price = WarehousePricePolicy.model_validate_json((ROOT / "config/warehouse-pricing.json").read_text())
        environment = os.getenv("ENVIRONMENT", "production").lower()
        enabled = environment in ("local", "development", "test") and os.getenv("WAREHOUSE_QUERY_ADAPTER_ENABLED") == "1"
        return WarehouseExecutionService(local_ledger(), get_store(), price,
            lambda: BigQueryTransport(ExistingGcloudIdentity(explicitly_enabled=enabled)), enabled=enabled)

    def actor(principal):
        def value(name):
            return principal.get(name) if isinstance(principal, dict) else getattr(principal, name, None)
        if value("role") not in ("editor", "reviewer") or value("actor_type") not in ("agent", "human") or not value("actor_id"):
            raise HTTPException(403, "Authenticated editor access is required")
        return value("actor_id")

    def invoke(function):
        try:
            return function()
        except AdmissionDenied as error:
            raise HTTPException(409, str(error)) from None
        except WarehouseError:
            raise HTTPException(503, "Warehouse outcome unavailable; resume the same ticket rather than creating another job") from None
        except (KeyError, ValueError):
            raise HTTPException(422, "Warehouse inputs or configuration are not valid") from None

    @router.get("/v1/warehouse/status")
    def status(principal=Depends(require_access)):
        return invoke(lambda: service().status())

    @router.post("/v1/warehouse/queries")
    def execute(request: WarehouseQueryRequest, principal=Depends(require_access)):
        actor_id = actor(principal)
        return invoke(lambda: service().execute(request, actor_id))

    @router.post("/v1/warehouse/queries/{query_id}/resume")
    def resume(query_id: str, principal=Depends(require_access)):
        actor_id = actor(principal)
        if len(query_id) != 35 or not query_id.startswith("wq_") or any(character not in "0123456789abcdef" for character in query_id[3:]):
            raise HTTPException(422, "Invalid warehouse ticket identifier")
        return invoke(lambda: service().resume(query_id, actor_id))

    return router
