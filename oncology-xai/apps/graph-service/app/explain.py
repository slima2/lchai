"""LLM-based graph explanation agent."""

from __future__ import annotations

import logging
from typing import Any

import httpx

logger = logging.getLogger(__name__)

SYSTEM_PROMPT_TEMPLATE = """You are an assistant that explains oncology knowledge graphs in natural language.
You receive the structure of a graph (nodes and edges) from a lung pathology case.
Generate a clear, concise explanation that describes:
1. What histological patterns were detected and their predominance.
2. Which gene mutations were predicted as positive, negative, or inconclusive.
3. For each predicted mutation, what targeted therapies or treatments are available according to current guidelines (OncoKB/FDA).
4. Which predictions are reliable (Conclusive, AUROC >= 0.70) vs which require molecular testing.
Keep a technical but accessible tone. Do NOT make definitive diagnostic statements.
Always recommend molecular confirmation for any positive prediction.
IMPORTANT: Respond entirely in {language}."""

USER_PROMPT_TEMPLATE = """Explain the following knowledge graph for case {case_id}:

NODOS:
{nodes_text}

ARISTAS (relaciones):
{edges_text}

Generate an explanation in 2-4 paragraphs in English."""


def _format_graph_for_prompt(nodes: list[dict], edges: list[dict]) -> tuple[str, str]:
    """Format nodes and edges as readable text for the LLM."""
    nodes_text = "\n".join(
        f"- {n.get('label', n.get('id', '?'))} (tipo: {n.get('type', 'entity')})"
        for n in nodes
    )
    edge_parts = []
    for e in edges:
        src = e.get("source")
        tgt = e.get("target")
        if isinstance(src, dict):
            src = src.get("id", src.get("label", "?"))
        if isinstance(tgt, dict):
            tgt = tgt.get("id", tgt.get("label", "?"))
        if isinstance(src, str) and ":" in src:
            src = src.split(":")[-1][:20]
        if isinstance(tgt, str) and ":" in tgt:
            tgt = tgt.split(":")[-1][:20]
        rel = e.get("label") or e.get("type", "relatedTo")
        inferred = " [inferida]" if e.get("type") == "inferred" else ""
        edge_parts.append(f"- {src} --[{rel}]--> {tgt}{inferred}")
    edges_text = "\n".join(edge_parts) if edge_parts else "(ninguna)"
    return nodes_text or "(ninguno)", edges_text


GENE_TREATMENTS: dict[str, str] = {
    "TP53": "No targeted therapy available. Standard treatment: platinum-based chemotherapy + immunotherapy (pembrolizumab). TP53 mutations are associated with poor prognosis.",
    "EGFR": "Targeted therapies: osimertinib (3rd gen TKI, preferred 1st line), erlotinib, gefitinib, afatinib. EGFR-mutant NSCLC responds well to TKI therapy.",
    "KRAS": "Targeted therapy: sotorasib (for G12C mutation only, ~13% of KRAS). Adagrasib also FDA-approved for G12C. Other KRAS variants lack targeted options.",
    "STK11": "No direct targeted therapy. STK11 loss predicts poor response to anti-PD-1/PD-L1 immunotherapy. Consider chemotherapy combinations.",
    "KEAP1": "No targeted therapy available. KEAP1 mutations associated with resistance to immunotherapy and poor prognosis. Platinum-based chemo is standard.",
    "RBM10": "No targeted therapy. RBM10 loss-of-function associated with aggressive disease. Standard chemotherapy/immunotherapy protocols apply.",
}


def _mock_explanation(nodes: list[dict], edges: list[dict], case_id: str) -> str:
    """Generate a deterministic explanation with treatment recommendations."""
    types: dict[str, int] = {}
    for n in nodes:
        t = n.get("type", "entity")
        types[t] = types.get(t, 0) + 1

    patterns = [n.get("label", "?") for n in nodes if n.get("type") == "pattern" or "pattern" in str(n.get("id", "")).lower()]
    genes = [n.get("label", "?") for n in nodes if n.get("type") == "gene"]
    treatments = [n.get("label", "?") for n in nodes if n.get("type") == "treatment"]

    pos_genes = [g for g in genes if "[POS]" in g]
    neg_genes = [g for g in genes if "[NEG]" in g]
    inc_genes = [g for g in genes if "[INCONCLUSIVE]" in g]

    parts = []

    if patterns:
        parts.append(
            f"**Histological patterns detected:** {', '.join(patterns)}."
        )

    if pos_genes:
        parts.append(
            f"**Mutations predicted as POSITIVE:** {', '.join(pos_genes)}. "
            "These predictions should be confirmed with standard molecular testing (NGS/PCR)."
        )
        parts.append("**Treatment options based on predicted mutations:**")
        for g in pos_genes:
            gene_name = g.split("[")[0].strip()
            tx = GENE_TREATMENTS.get(gene_name, "Consult oncology guidelines.")
            parts.append(f"- **{gene_name}:** {tx}")

    if neg_genes:
        parts.append(
            f"**Likely wild-type (negative):** {', '.join(neg_genes)}."
        )

    if inc_genes:
        parts.append(
            f"**Inconclusive predictions (require molecular testing):** {', '.join(inc_genes)}. "
            "The model AUROC < 0.70 for these genes — histological features alone are insufficient for reliable prediction."
        )

    if treatments:
        parts.append(f"**Treatments in knowledge graph:** {', '.join(treatments)}.")

    parts.append(
        "**Disclaimer:** This analysis is for research purposes only (THESIS_INTERNAL evidence). "
        "All mutation predictions must be confirmed by standard molecular pathology before clinical decision-making."
    )

    return "\n\n".join(parts)


async def generate_explanation(
    case_id: str,
    nodes: list[dict[str, Any]],
    edges: list[dict[str, Any]],
    *,
    openai_api_key: str = "",
    anthropic_api_key: str = "",
    llm_provider: str = "openai",
    language: str = "English",
) -> str:
    """Generate natural language explanation of the graph via LLM or mock."""
    LANG_MAP = {"en": "English", "es": "Spanish", "de": "German", "fr": "French", "pt": "Portuguese"}
    lang_name = LANG_MAP.get(language, language) if len(language) <= 3 else language
    system_prompt = SYSTEM_PROMPT_TEMPLATE.format(language=lang_name)

    nodes_text, edges_text = _format_graph_for_prompt(nodes, edges)
    user_prompt = USER_PROMPT_TEMPLATE.format(
        case_id=case_id,
        nodes_text=nodes_text,
        edges_text=edges_text,
    )

    if llm_provider == "mock":
        return _mock_explanation(nodes, edges, case_id)

    # Try OpenAI
    if llm_provider == "openai" and openai_api_key:
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.post(
                    "https://api.openai.com/v1/chat/completions",
                    headers={"Authorization": f"Bearer {openai_api_key}"},
                    json={
                        "model": "gpt-4o-mini",
                        "messages": [
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": user_prompt},
                        ],
                        "temperature": 0.3,
                        "max_tokens": 800,
                    },
                )
                if resp.status_code == 200:
                    data = resp.json()
                    choice = data.get("choices", [{}])[0]
                    return (choice.get("message", {}).get("content") or "").strip()
        except Exception as e:
            logger.warning("OpenAI explanation failed: %s — falling back to mock", e)

    # Try Anthropic
    if llm_provider == "anthropic" and anthropic_api_key:
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.post(
                    "https://api.anthropic.com/v1/messages",
                    headers={
                        "x-api-key": anthropic_api_key,
                        "anthropic-version": "2023-06-01",
                        "Content-Type": "application/json",
                    },
                    json={
                        "model": "claude-3-5-haiku-20241022",
                        "max_tokens": 800,
                        "system": system_prompt,
                        "messages": [{"role": "user", "content": user_prompt}],
                    },
                )
                if resp.status_code == 200:
                    data = resp.json()
                    for block in data.get("content", []):
                        if block.get("type") == "text":
                            return block.get("text", "").strip()
        except Exception as e:
            logger.warning("Anthropic explanation failed: %s — falling back to mock", e)

    return _mock_explanation(nodes, edges, case_id)
