"""LLM-based graph explanation agent."""

from __future__ import annotations

import logging
from typing import Any

import httpx

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """Eres un asistente que explica grafos de conocimiento oncológico en lenguaje natural.
Recibes la estructura de un grafo (nodos y aristas) de un caso de patología pulmonar.
Genera una explicación clara y concisa en español que describa:
1. Qué entidades aparecen (caso, genes, diagnósticos, patrones histológicos).
2. Cómo se relacionan entre sí (asserted vs inferred).
3. Qué implicaciones tiene para el caso (ej. patrones lepidic/acinar asociados a genes).
Mantén un tono técnico pero accesible. Evita afirmaciones diagnósticas definitivas."""

USER_PROMPT_TEMPLATE = """Explica el siguiente grafo de conocimiento para el caso {case_id}:

NODOS:
{nodes_text}

ARISTAS (relaciones):
{edges_text}

Genera una explicación en 2-4 párrafos."""


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


def _mock_explanation(nodes: list[dict], edges: list[dict], case_id: str) -> str:
    """Generate a deterministic mock explanation when no LLM is configured."""
    node_labels = [n.get("label", n.get("id", "?")) for n in nodes]
    types = {}
    for n in nodes:
        t = n.get("type", "entity")
        types[t] = types.get(t, 0) + 1
    patterns = [n.get("label", "?") for n in nodes if n.get("type") == "pattern" or "pattern" in str(n.get("id", ""))]
    genes = [n.get("label", "?") for n in nodes if n.get("type") == "gene"]
    inferred_count = sum(1 for e in edges if e.get("type") == "inferred")

    parts = [
        f"Este grafo de conocimiento corresponde al caso {case_id[:8]}... y representa "
        f"la integración de evidencia clínica, ontológica y de imagen.",
        f"Contiene {len(nodes)} entidades: {', '.join(str(v) + ' ' + k for k, v in types.items())}.",
    ]
    if patterns:
        parts.append(
            f"Los patrones histológicos detectados incluyen: {', '.join(patterns)}. "
            "Estos patrones se asocian con genes (ej. lepidic con TP53, acinar con EGFR) mediante relaciones inferidas."
        )
    if genes:
        parts.append(f"Los genes representados son: {', '.join(genes)}.")
    if inferred_count > 0:
        parts.append(
            f"Hay {inferred_count} relación(es) inferida(s) por el modelo THESIS_INTERNAL, "
            "basadas en literatura y correlaciones morfológico-moleculares."
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
) -> str:
    """Generate natural language explanation of the graph via LLM or mock."""
    nodes_text, edges_text = _format_graph_for_prompt(nodes, edges)
    user_prompt = USER_PROMPT_TEMPLATE.format(
        case_id=case_id,
        nodes_text=nodes_text,
        edges_text=edges_text,
    )

    # Skip LLM if mock
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
                            {"role": "system", "content": SYSTEM_PROMPT},
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
                        "system": SYSTEM_PROMPT,
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
