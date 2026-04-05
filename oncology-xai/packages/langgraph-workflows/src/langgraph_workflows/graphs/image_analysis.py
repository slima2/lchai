"""ImageAnalysisGraph — LangGraph workflow (DERCAS 13.1.1).

ValidateInput → LoadImage → ResolveROI → RunCTransPathEmbedding →
RunFuzzyArcLossV3Subcenters → ComputePatternComposition →
BuildMorphologicProfile → RunMutationModels →
ComputeSHAPGlobalIfMissing → ComputeSHAPCaseForce →
AssembleResultBundle → PolicyCheck → PersistAndAudit → Finalize
"""

from __future__ import annotations

import logging
from typing import Any, Literal
from uuid import uuid4

from langgraph.graph import StateGraph, END

from langgraph_workflows.state import GraphState, update_exec
from langgraph_workflows.tools.model import get_model_client
from langgraph_workflows.tools.storage import get_storage_tool

logger = logging.getLogger(__name__)

# Pattern palette (DERCAS section 7)
PATTERN_PALETTE = {
    "lepidic": (0, 0, 255),
    "acinar": (255, 0, 0),
    "papillary": (255, 255, 0),
    "micropapillary": (255, 0, 255),
    "solid": (128, 0, 0),
    "cribriform": (0, 255, 255),
}

# Mutation threshold (default 0.5)
MUTATION_THRESHOLD = 0.5


async def validate_input(state: GraphState) -> GraphState:
    """Validate that required inputs are present."""
    state = update_exec(state, status="running", progress=0.0, current_node="validate_input")
    inputs = state.get("inputs", {})

    if not inputs.get("image_id") and not inputs.get("image_uri"):
        state = update_exec(
            state, error={"code": "VALIDATION_ERROR", "message": "image_id or image_uri required"}
        )
        state["execution"]["status"] = "failed"
        return state

    ctx = state.get("context", {})
    if not ctx.get("case_id"):
        state = update_exec(
            state, error={"code": "VALIDATION_ERROR", "message": "case_id is required in context"}
        )
        state["execution"]["status"] = "failed"

    return state


async def load_image(state: GraphState) -> GraphState:
    """Download image bytes from MinIO/S3 using the storage tool."""
    state = update_exec(state, progress=0.05, current_node="load_image")
    inputs = state.get("inputs", {})
    storage = get_storage_tool()

    uri = inputs.get("image_uri", "")
    if not uri and inputs.get("image_id"):
        uri = f"images/{inputs['image_id']}"

    try:
        key = storage.key_from_uri(uri) if uri.startswith("s3://") else uri
        image_bytes = storage.download_file(key)
        state["_image_bytes"] = image_bytes
        logger.info("Loaded image: %d bytes from %s", len(image_bytes), key)
    except Exception as exc:
        logger.error("Failed to load image: %s", exc)
        state["_image_bytes"] = b""
        state = update_exec(state, error={"code": "LOAD_ERROR", "message": str(exc)})

    return state


async def resolve_roi(state: GraphState) -> GraphState:
    """Resolve ROI specification: bbox, polygon, mask, or full-image."""
    state = update_exec(state, progress=0.10, current_node="resolve_roi")
    inputs = state.get("inputs", {})
    inter = dict(state.get("_intermediate", {}))

    roi_spec = inputs.get("roi", None)
    if roi_spec:
        inter["roi_type"] = roi_spec.get("type", "full")
        inter["roi_data"] = roi_spec
    else:
        inter["roi_type"] = "full"
        inter["roi_data"] = None

    state["_intermediate"] = inter
    return state


async def run_ctranspath_embedding(state: GraphState) -> GraphState:
    """Extract CTransPath embeddings from image tiles."""
    state = update_exec(state, progress=0.25, current_node="run_ctranspath_embedding")
    inter = dict(state.get("_intermediate", {}))

    image_bytes = state.get("_image_bytes", b"")
    model_client = get_model_client()

    # The embedding extraction is handled internally by the pattern prediction
    # Store embedding dimension for downstream use
    inter["embedding_dim"] = 512
    inter["image_size"] = len(image_bytes)

    state["_intermediate"] = inter
    return state


async def run_fuzzyarcloss_v3(state: GraphState) -> GraphState:
    """Run FuzzyArcLoss v3 SubCenters for pattern classification."""
    state = update_exec(state, progress=0.40, current_node="run_fuzzyarcloss_v3_subcenters")
    model_client = get_model_client()

    image_bytes = state.get("_image_bytes", b"")
    inputs = state.get("inputs", {})
    thresholds = inputs.get("thresholds", {})

    try:
        pattern_outputs = await model_client.predict_patterns(image_bytes, thresholds)
    except Exception as exc:
        logger.error("Pattern prediction failed: %s", exc)
        pattern_outputs = model_client._mock_patterns()
        state = update_exec(state, error={"code": "PATTERN_ERROR", "message": str(exc)})

    outputs = dict(state.get("outputs", {}))
    outputs["pattern_outputs"] = pattern_outputs
    state["outputs"] = outputs

    await model_client.close()
    return state


async def compute_pattern_composition(state: GraphState) -> GraphState:
    """Compute pattern composition from tile-level predictions.

    Normalises percentages so they sum to 100% and determines
    the predominant pattern.
    """
    state = update_exec(state, progress=0.50, current_node="compute_pattern_composition")
    outputs = dict(state.get("outputs", {}))
    patterns = outputs.get("pattern_outputs", [])

    if patterns:
        total_pct = sum(p.get("percentage", 0) for p in patterns)
        if total_pct > 0:
            for p in patterns:
                p["percentage"] = round(p["percentage"] / total_pct * 100, 2)
        # Determine predominant pattern
        predominant = max(patterns, key=lambda p: p.get("percentage", 0))
        inter = dict(state.get("_intermediate", {}))
        inter["predominant_pattern"] = predominant["pattern"]
        inter["pattern_composition"] = {p["pattern"]: p["percentage"] for p in patterns}
        state["_intermediate"] = inter

    outputs["pattern_outputs"] = patterns
    state["outputs"] = outputs
    return state


async def build_morphologic_profile(state: GraphState) -> GraphState:
    """Build the morphologic feature vector for mutation prediction.

    Features: n_tiles_total + pct_* for each pattern (7 features).
    """
    state = update_exec(state, progress=0.55, current_node="build_morphologic_profile")
    inter = dict(state.get("_intermediate", {}))
    outputs = dict(state.get("outputs", {}))
    patterns = outputs.get("pattern_outputs", [])

    # Build morphologic profile dict
    composition = {p["pattern"]: p.get("percentage", 0) for p in patterns}
    profile = {
        "n_tiles_total": inter.get("n_tiles_total", len(patterns) * 20),
        "pct_lepidic": composition.get("lepidic", 0),
        "pct_acinar": composition.get("acinar", 0),
        "pct_papillary": composition.get("papillary", 0),
        "pct_micropapillary": composition.get("micropapillary", 0),
        "pct_solid": composition.get("solid", 0),
        "pct_cribriform": composition.get("cribriform", 0),
    }

    inter["morphologic_profile"] = profile
    state["_intermediate"] = inter
    return state


async def run_mutation_models(state: GraphState) -> GraphState:
    """Run XGBoost mutation prediction models for EGFR, KRAS, TP53."""
    state = update_exec(state, progress=0.65, current_node="run_mutation_models")
    inter = dict(state.get("_intermediate", {}))
    profile = inter.get("morphologic_profile", {})

    model_client = get_model_client()

    try:
        genetic_outputs = await model_client.predict_mutations(profile)
    except Exception as exc:
        logger.error("Mutation prediction failed: %s", exc)
        genetic_outputs = model_client._mock_mutations()
        state = update_exec(state, error={"code": "MUTATION_ERROR", "message": str(exc)})

    # Apply threshold classification
    for g in genetic_outputs:
        score = g.get("score", 0)
        if score >= MUTATION_THRESHOLD + 0.1:
            g["status"] = "POS"
        elif score <= MUTATION_THRESHOLD - 0.1:
            g["status"] = "NEG"
        else:
            g["status"] = "INCONCLUSIVE"

    outputs = dict(state.get("outputs", {}))
    outputs["genetic_outputs"] = genetic_outputs
    state["outputs"] = outputs

    await model_client.close()
    return state


async def compute_shap_global(state: GraphState) -> GraphState:
    """Compute SHAP global explanations (bar + beeswarm) per gene."""
    state = update_exec(state, progress=0.75, current_node="compute_shap_global")
    inter = dict(state.get("_intermediate", {}))
    profile = inter.get("morphologic_profile", {})
    outputs = dict(state.get("outputs", {}))
    genetic = outputs.get("genetic_outputs", [])

    genes = [g["mutation"] for g in genetic]
    model_client = get_model_client()

    try:
        shap_artifacts = await model_client.generate_shap(profile, genes)
    except Exception as exc:
        logger.error("SHAP generation failed: %s", exc)
        shap_artifacts = model_client._mock_shap(genes)
        state = update_exec(state, error={"code": "SHAP_ERROR", "message": str(exc)})

    # Keep only global artifacts (bar + beeswarm)
    global_artifacts = [a for a in shap_artifacts if a["artifact_type"] in ("shap_bar", "shap_beeswarm")]
    inter["shap_global_artifacts"] = global_artifacts

    # Keep force plot artifacts separately
    force_artifacts = [a for a in shap_artifacts if a["artifact_type"] == "shap_force"]
    inter["shap_force_artifacts"] = force_artifacts

    state["_intermediate"] = inter
    outputs["shap_artifacts"] = shap_artifacts
    state["outputs"] = outputs

    await model_client.close()
    return state


async def compute_shap_case_force(state: GraphState) -> GraphState:
    """Attach per-case SHAP force plots (already generated in global step)."""
    state = update_exec(state, progress=0.80, current_node="compute_shap_case_force")
    inter = dict(state.get("_intermediate", {}))
    outputs = dict(state.get("outputs", {}))

    # Force artifacts were generated alongside global ones
    force_artifacts = inter.get("shap_force_artifacts", [])
    xai = outputs.get("xai_artifacts", [])
    xai.extend(force_artifacts)
    outputs["xai_artifacts"] = xai
    state["outputs"] = outputs
    return state


async def assemble_result_bundle(state: GraphState) -> GraphState:
    """Assemble the complete ResultBundle with all outputs."""
    state = update_exec(state, progress=0.85, current_node="assemble_result_bundle")
    outputs = dict(state.get("outputs", {}))
    inter = dict(state.get("_intermediate", {}))
    ctx = state.get("context", {})

    bundle_id = f"rb_{uuid4().hex[:16]}"
    outputs["result_bundle_id"] = bundle_id

    # Add XAI artifacts from SHAP
    shap_all = inter.get("shap_global_artifacts", []) + inter.get("shap_force_artifacts", [])
    existing_xai = outputs.get("xai_artifacts", [])
    # Deduplicate
    seen_uris = {a.get("uri") for a in existing_xai}
    for a in shap_all:
        if a.get("uri") not in seen_uris:
            existing_xai.append(a)
            seen_uris.add(a.get("uri"))
    outputs["xai_artifacts"] = existing_xai

    # Summary
    outputs["summary"] = {
        "bundle_id": bundle_id,
        "case_id": ctx.get("case_id"),
        "predominant_pattern": inter.get("predominant_pattern"),
        "pattern_composition": inter.get("pattern_composition", {}),
        "n_patterns": len(outputs.get("pattern_outputs", [])),
        "n_mutations": len(outputs.get("genetic_outputs", [])),
        "n_xai_artifacts": len(existing_xai),
        "evidence_source": "THESIS_INTERNAL",
        "intended_use": "research / decision support (non-diagnostic)",
    }

    state["outputs"] = outputs
    return state


async def policy_check(state: GraphState) -> GraphState:
    """Apply clinical policy checks on results.

    Flags low-confidence patterns and inconclusive mutations for review.
    """
    state = update_exec(state, progress=0.90, current_node="policy_check")
    outputs = dict(state.get("outputs", {}))
    inter = dict(state.get("_intermediate", {}))

    flags: list[dict[str, str]] = []

    # Check pattern conclusiveness
    for p in outputs.get("pattern_outputs", []):
        if not p.get("is_conclusive", True):
            flags.append({
                "type": "LOW_CONFIDENCE_PATTERN",
                "pattern": p["pattern"],
                "score": str(p.get("score", 0)),
            })

    # Check inconclusive mutations
    for g in outputs.get("genetic_outputs", []):
        if g.get("status") == "INCONCLUSIVE":
            flags.append({
                "type": "INCONCLUSIVE_MUTATION",
                "mutation": g["mutation"],
                "score": str(g.get("score", 0)),
            })

    inter["policy_flags"] = flags
    if flags:
        inter["review_required"] = True
        logger.info("Policy check: %d flags raised, review required", len(flags))

    state["_intermediate"] = inter
    return state


async def persist_and_audit(state: GraphState) -> GraphState:
    """Persist results to storage and emit audit event.

    In production this writes to MinIO and publishes to RabbitMQ.
    """
    state = update_exec(state, progress=0.95, current_node="persist_and_audit")
    outputs = dict(state.get("outputs", {}))
    inter = dict(state.get("_intermediate", {}))
    ctx = state.get("context", {})
    identity = state.get("identity", {})

    storage = get_storage_tool()
    bundle_id = outputs.get("result_bundle_id", "unknown")

    # Persist pattern composition as JSON
    import json
    composition = inter.get("pattern_composition", {})
    if composition:
        comp_json = json.dumps(composition, indent=2).encode("utf-8")
        comp_uri = storage.upload_file(
            f"results/{bundle_id}/pattern_composition.json", comp_json, "application/json"
        )
        logger.info("Persisted pattern composition to %s", comp_uri)

    # Persist morphologic profile
    profile = inter.get("morphologic_profile", {})
    if profile:
        profile_json = json.dumps(profile, indent=2).encode("utf-8")
        storage.upload_file(
            f"results/{bundle_id}/morphologic_profile.json", profile_json, "application/json"
        )

    # Audit trail entry (in-memory representation; actual emit happens in service layer)
    inter["audit_entry"] = {
        "event_type": "inference.completed",
        "case_id": ctx.get("case_id"),
        "entity_type": "ResultBundle",
        "entity_id": bundle_id,
        "user_id": identity.get("user_id"),
        "correlation_id": identity.get("correlation_id"),
    }
    state["_intermediate"] = inter
    return state


async def finalize(state: GraphState) -> GraphState:
    """Mark workflow as completed and clean up transient state."""
    ex = dict(state.get("execution", {}))
    if ex.get("status") != "failed":
        ex["status"] = "completed"
    ex["progress"] = 1.0
    ex["current_node"] = "finalize"
    state["execution"] = ex

    # Clean up transient data
    state.pop("_image_bytes", None)
    return state


def _should_continue(state: GraphState) -> Literal["continue", "end"]:
    if state.get("execution", {}).get("status") == "failed":
        return "end"
    return "continue"


def create_image_analysis_graph():
    """Build and compile the ImageAnalysisGraph."""
    wf = StateGraph(GraphState)

    wf.add_node("validate_input", validate_input)
    wf.add_node("load_image", load_image)
    wf.add_node("resolve_roi", resolve_roi)
    wf.add_node("run_ctranspath_embedding", run_ctranspath_embedding)
    wf.add_node("run_fuzzyarcloss_v3", run_fuzzyarcloss_v3)
    wf.add_node("compute_pattern_composition", compute_pattern_composition)
    wf.add_node("build_morphologic_profile", build_morphologic_profile)
    wf.add_node("run_mutation_models", run_mutation_models)
    wf.add_node("compute_shap_global", compute_shap_global)
    wf.add_node("compute_shap_case_force", compute_shap_case_force)
    wf.add_node("assemble_result_bundle", assemble_result_bundle)
    wf.add_node("policy_check", policy_check)
    wf.add_node("persist_and_audit", persist_and_audit)
    wf.add_node("finalize", finalize)

    wf.set_entry_point("validate_input")

    wf.add_conditional_edges("validate_input", _should_continue, {"continue": "load_image", "end": "finalize"})
    wf.add_edge("load_image", "resolve_roi")
    wf.add_edge("resolve_roi", "run_ctranspath_embedding")
    wf.add_edge("run_ctranspath_embedding", "run_fuzzyarcloss_v3")
    wf.add_edge("run_fuzzyarcloss_v3", "compute_pattern_composition")
    wf.add_edge("compute_pattern_composition", "build_morphologic_profile")
    wf.add_edge("build_morphologic_profile", "run_mutation_models")
    wf.add_edge("run_mutation_models", "compute_shap_global")
    wf.add_edge("compute_shap_global", "compute_shap_case_force")
    wf.add_edge("compute_shap_case_force", "assemble_result_bundle")
    wf.add_edge("assemble_result_bundle", "policy_check")
    wf.add_edge("policy_check", "persist_and_audit")
    wf.add_edge("persist_and_audit", "finalize")
    wf.add_edge("finalize", END)

    return wf.compile()
