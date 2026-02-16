"""Common state definitions for LangGraph workflows (DERCAS 13.2)."""

from typing import Any, TypedDict

from pydantic import BaseModel, Field


class Identity(BaseModel):
    correlation_id: str
    user_id: str | None = None
    roles: list[str] = Field(default_factory=list)


class Context(BaseModel):
    patient_id: str | None = None
    case_id: str | None = None


class Inputs(BaseModel):
    image_id: str | None = None
    image_uri: str | None = None
    ehr_id: str | None = None
    ehr_text: str | None = None
    ontology_versions: dict[str, str] = Field(default_factory=dict)


class Execution(BaseModel):
    job_id: str | None = None
    status: str = "pending"
    progress: float = 0.0
    current_node: str | None = None
    errors: list[dict[str, Any]] = Field(default_factory=list)


class Outputs(BaseModel):
    result_bundle_id: str | None = None
    pattern_outputs: list[dict[str, Any]] = Field(default_factory=list)
    genetic_outputs: list[dict[str, Any]] = Field(default_factory=list)
    xai_artifacts: list[dict[str, Any]] = Field(default_factory=list)
    shap_artifacts: list[dict[str, Any]] = Field(default_factory=list)
    entities: list[dict[str, Any]] = Field(default_factory=list)
    mappings: list[dict[str, Any]] = Field(default_factory=list)
    graph_snapshot_id: str | None = None
    report_id: str | None = None
    report_uri: str | None = None


class GraphState(TypedDict, total=False):
    identity: dict[str, Any]
    context: dict[str, Any]
    inputs: dict[str, Any]
    execution: dict[str, Any]
    outputs: dict[str, Any]
    _image_bytes: bytes | None
    _ehr_text: str | None
    _intermediate: dict[str, Any]


def create_initial_state(
    correlation_id: str,
    user_id: str | None = None,
    roles: list[str] | None = None,
    case_id: str | None = None,
    patient_id: str | None = None,
) -> GraphState:
    return GraphState(
        identity=Identity(correlation_id=correlation_id, user_id=user_id, roles=roles or []).model_dump(),
        context=Context(patient_id=patient_id, case_id=case_id).model_dump(),
        inputs=Inputs().model_dump(),
        execution=Execution().model_dump(),
        outputs=Outputs().model_dump(),
    )


def update_exec(state: GraphState, **kwargs) -> GraphState:
    ex = dict(state.get("execution", {}))
    ex.update(kwargs)
    if "error" in kwargs:
        errs = ex.get("errors", [])
        errs.append(kwargs.pop("error"))
        ex["errors"] = errs
    state["execution"] = ex
    return state
