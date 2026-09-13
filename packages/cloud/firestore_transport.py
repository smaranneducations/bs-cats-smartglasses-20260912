from __future__ import annotations

from datetime import datetime, timezone
import math
import os
import subprocess
import time

import httpx

PROJECT = "bs-cats-smartglasses-20260912"
DATABASE = "(default)"
DOCUMENTS = f"projects/{PROJECT}/databases/{DATABASE}/documents"
BASE = "https://firestore.googleapis.com/v1/" + DOCUMENTS
ACTION_UNITS = {
    "beginTransaction": "transaction_begin",
    "batchGet": "document_read",
    "commit": "document_write",
    "rollback": "transaction_rollback",
    "runQuery": "document_read",
}


class CloudAdmissionDenied(RuntimeError):
    pass


class ProviderFailure(RuntimeError):
    def __init__(self, operation, status=None):
        self.operation, self.status = operation, status
        super().__init__(f"Cloud operation {operation} could not complete; status={status}.")


class TransactionAborted(ProviderFailure):
    pass


class AmbiguousCommit(ProviderFailure):
    """A receipt must resolve this state; never blindly replay the mutation."""


def deny_unreconciled_operation(operation, units):
    raise CloudAdmissionDenied("Cloud document operations require reconciled accounting and an explicit admission adapter.")


def bounded_production_admission(operation, units):
    """Fail closed unless the deployed service explicitly enables small Firestore operations."""
    if os.getenv("FIRESTORE_OPERATIONS_ENABLED") != "1":
        raise CloudAdmissionDenied("Bounded Firestore operations are not enabled for this service revision.")
    limits = {
        "transaction_begin": 1,
        "transaction_rollback": 1,
        "document_write": 10,
        "document_read": 500,
    }
    if operation not in limits or isinstance(units, bool) or not isinstance(units, int) or not 1 <= units <= limits[operation]:
        raise CloudAdmissionDenied("The Firestore operation exceeds its per-request admission limit.")


def encode_value(value):
    if value is None:
        return {"nullValue": None}
    if isinstance(value, bool):
        return {"booleanValue": value}
    if isinstance(value, int):
        if not -(2**63) <= value < 2**63:
            raise ValueError("Firestore integers must fit signed 64-bit storage.")
        return {"integerValue": str(value)}
    if isinstance(value, float):
        if not math.isfinite(value):
            raise ValueError("Non-finite cloud values are not permitted.")
        return {"doubleValue": value}
    if isinstance(value, str):
        return {"stringValue": value}
    if isinstance(value, datetime):
        if value.tzinfo is None:
            raise ValueError("Cloud timestamps require a timezone.")
        return {"timestampValue": value.astimezone(timezone.utc).isoformat()}
    if isinstance(value, list):
        if any(isinstance(item, list) for item in value):
            raise ValueError("Firestore does not support directly nested arrays.")
        return {"arrayValue": {"values": [encode_value(item) for item in value]}}
    if isinstance(value, dict) and all(isinstance(key, str) for key in value):
        return {"mapValue": {"fields": {key: encode_value(item) for key, item in value.items()}}}
    raise ValueError("Unsupported cloud value type.")


def decode_value(value):
    if "nullValue" in value:
        return None
    if "booleanValue" in value:
        return value["booleanValue"]
    if "integerValue" in value:
        return int(value["integerValue"])
    if "doubleValue" in value:
        result = float(value["doubleValue"])
        if not math.isfinite(result):
            raise ValueError("Non-finite cloud values are not permitted.")
        return result
    if "stringValue" in value:
        return value["stringValue"]
    if "timestampValue" in value:
        return value["timestampValue"]
    if "mapValue" in value:
        return {key: decode_value(item) for key, item in value["mapValue"].get("fields", {}).items()}
    if "arrayValue" in value:
        return [decode_value(item) for item in value["arrayValue"].get("values", [])]
    raise ValueError("Unsupported Firestore response value.")


def document_fields(data):
    return {key: encode_value(value) for key, value in data.items()}


def document_data(document):
    return {key: decode_value(value) for key, value in document.get("fields", {}).items()}


class ShortLivedGoogleToken:
    """Memory-only access tokens; no copied account keys or project .env reads.

    Production uses its attached service identity. Local CLI identity requires an
    explicit constructor opt-in and uses the already authenticated gcloud CLI.
    """

    def __init__(self, allow_local_cli=False):
        self.allow_local_cli = allow_local_cli
        self._token, self._until = None, 0

    def __call__(self):
        if self._token and time.monotonic() < self._until:
            return self._token
        if os.getenv("K_SERVICE"):
            try:
                with httpx.Client(timeout=3, trust_env=False, follow_redirects=False) as client:
                    response = client.get("http://metadata.google.internal/computeMetadata/v1/instance/service-accounts/default/token", headers={"Metadata-Flavor": "Google"})
                    if response.status_code != 200:
                        raise ProviderFailure("service_identity", response.status_code)
                    data = response.json()
                token, lifetime = data["access_token"], int(data["expires_in"])
            except (httpx.HTTPError, KeyError, TypeError, ValueError):
                raise ProviderFailure("service_identity") from None
        elif self.allow_local_cli:
            try:
                completed = subprocess.run(["gcloud", "auth", "print-access-token", "--quiet"], capture_output=True, text=True, timeout=15, check=False)
                if completed.returncode:
                    raise ProviderFailure("local_cli_identity", completed.returncode)
                token, lifetime = completed.stdout.strip(), 240
            except (OSError, subprocess.TimeoutExpired):
                raise ProviderFailure("local_cli_identity") from None
        else:
            raise CloudAdmissionDenied("No authorized workload identity or explicit local CLI identity is available.")
        if not token or len(token) > 8192 or any(character.isspace() for character in token):
            raise ProviderFailure("identity_token_format")
        self._token, self._until = token, time.monotonic() + max(0, min(lifetime - 60, 240))
        return token


class FirestoreTransport:
    """Fixed-project REST transport. Admission runs before token retrieval."""

    def __init__(self, token_source=None, admission=deny_unreconciled_operation, client=None):
        self.token_source = token_source or ShortLivedGoogleToken()
        self.admission = admission
        self.client = client

    def call(self, action, body):
        if action not in ACTION_UNITS:
            raise ValueError("Cloud operation is not allowlisted.")
        if action == "batchGet":
            names = body.get("documents", [])
            if not 1 <= len(names) <= 20 or any(not name.startswith(DOCUMENTS + "/") for name in names):
                raise ValueError("The cloud read must stay within the fixed project and document budget.")
            units = len(names)
        elif action == "commit":
            writes = body.get("writes", [])
            if not 1 <= len(writes) <= 10:
                raise ValueError("The cloud write budget was exceeded.")
            if any(not write.get("update", {}).get("name", "").startswith(DOCUMENTS + "/") for write in writes):
                raise ValueError("Only same-project document updates are supported.")
            units = len(writes)
        elif action == "runQuery":
            query = body.get("structuredQuery", {})
            collections = query.get("from", [])
            limit = query.get("limit", 0)
            collection = collections[0].get("collectionId") if len(collections) == 1 else None
            if collection == "admin_feedback":
                if not isinstance(limit, int) or not 1 <= limit <= 20:
                    raise ValueError("Admin feedback reads require a limit of at most twenty.")
            elif collection == "governed_objects":
                if query.get("where") or not isinstance(limit, int) or not 1 <= limit <= 500:
                    raise ValueError("Current-object reads must be bounded and cannot supply an arbitrary filter.")
            elif collection == "governed_object_versions":
                field_filter = query.get("where", {}).get("fieldFilter", {})
                order = query.get("orderBy", [])
                value = field_filter.get("value", {}).get("stringValue", "")
                if (field_filter.get("field", {}).get("fieldPath") != "object_id"
                        or field_filter.get("op") != "EQUAL" or not value
                        or order != [{"field": {"fieldPath": "version"}, "direction": "ASCENDING"}]
                        or not isinstance(limit, int) or not 1 <= limit <= 100):
                    raise ValueError("History reads require one bounded object ID and ascending version order.")
            else:
                raise ValueError("The cloud query collection is not allowlisted.")
            units = limit
        else:
            units = 1
        self.admission(ACTION_UNITS[action], units)
        headers = {"Authorization": "Bearer " + self.token_source(), "Content-Type": "application/json"}
        owned = self.client is None
        client = self.client or httpx.Client(timeout=10, follow_redirects=False, trust_env=False)
        try:
            response = client.post(BASE + ":" + action, headers=headers, json=body)
            if response.status_code == 409:
                raise TransactionAborted(action, 409)
            if response.status_code >= 500 and action == "commit":
                raise AmbiguousCommit(action, response.status_code)
            if not 200 <= response.status_code < 300:
                raise ProviderFailure(action, response.status_code)
            try:
                return response.json()
            except ValueError:
                if action == "commit":
                    raise AmbiguousCommit(action, response.status_code) from None
                raise ProviderFailure(action, response.status_code) from None
        except httpx.HTTPError:
            if action == "commit":
                raise AmbiguousCommit(action) from None
            raise ProviderFailure(action) from None
        finally:
            if owned:
                client.close()
