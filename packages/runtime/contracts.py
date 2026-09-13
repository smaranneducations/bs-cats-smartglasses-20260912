from __future__ import annotations

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class RuntimeContract(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, allow_inf_nan=False)


class ObjectInput(RuntimeContract):
    object_id: Annotated[str, Field(min_length=1, max_length=160, pattern=r"^[A-Za-z0-9_.:-]+$")]
    version: Annotated[int, Field(ge=1)]


class TaskRequest(RuntimeContract):
    schema_version: Literal["runtime-task-1"] = "runtime-task-1"
    charter_version: Literal["1.6"] = "1.6"
    profile_id: Literal["catalogue_auditor", "source_policy_adviser", "workflow_planner"]
    profile_revision: Literal[1] = 1
    objective: Annotated[str, Field(min_length=8, max_length=1200)]
    inputs: Annotated[list[ObjectInput], Field(min_length=1, max_length=100)]
    acceptance_criteria: Annotated[list[str], Field(min_length=1, max_length=8)]
    risk: Literal["low", "medium"] = "low"
    workflow_family: Literal["category", "product", "feature", "comparison", "use_case", "value", "change", "compatibility", "question", "myth", "market", "commercial"] | None = None
    idempotency_key: Annotated[str, Field(min_length=8, max_length=160, pattern=r"^[A-Za-z0-9_.:-]+$")]

    @field_validator("inputs")
    @classmethod
    def distinct_inputs(cls, inputs):
        if len({item.object_id for item in inputs}) != len(inputs):
            raise ValueError("Each input object must appear once.")
        return inputs

    @field_validator("acceptance_criteria")
    @classmethod
    def bounded_criteria(cls, items):
        if any(not item.strip() or len(item) > 400 for item in items):
            raise ValueError("Acceptance criteria must contain 1-400 characters each.")
        return items


class TaskSubmission(RuntimeContract):
    task: TaskRequest


class RunRequest(RuntimeContract):
    task_id: Annotated[str, Field(pattern=r"^task_[0-9a-f]{32}$")]
