"""v2 inference pipelines."""

from app.ml.inference.abmil_inference import run_abmil_inference
from app.ml.inference.choquet_inference import run_choquet_inference
from app.ml.inference.shap_decompose import run_shap_decomposition

__all__ = ["run_abmil_inference", "run_choquet_inference", "run_shap_decomposition"]
