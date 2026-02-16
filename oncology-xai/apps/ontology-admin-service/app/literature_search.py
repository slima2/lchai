"""Literature search engine — batch queries to PubMed, arXiv, Semantic Scholar.

Searches public academic APIs for recent papers on lung adenocarcinoma
histologic patterns, genetic mutations, and targeted therapies.
Extracts abstracts for downstream LLM relation extraction.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any

import httpx

logger = logging.getLogger(__name__)

# ──────────────────────────────────────────────────────────────────────
# Search queries (domain-specific, curated for LUAD research)
# ──────────────────────────────────────────────────────────────────────

DEFAULT_QUERIES = [
    # Pattern ↔ mutation associations
    "lung adenocarcinoma histologic pattern EGFR KRAS mutation association",
    "lepidic acinar papillary micropapillary solid pattern lung cancer prognosis",
    "lung adenocarcinoma morphology molecular subtypes targetable mutations",
    # Treatment ↔ mutation
    "EGFR mutant NSCLC targeted therapy osimertinib resistance",
    "KRAS G12C lung cancer sotorasib adagrasib clinical trial",
    "ALK rearrangement NSCLC alectinib lorlatinib treatment",
    "BRAF V600E lung adenocarcinoma dabrafenib trametinib",
    "RET fusion NSCLC selpercatinib pralsetinib",
    "MET exon 14 skipping lung cancer capmatinib tepotinib",
    "HER2 ERBB2 NSCLC trastuzumab deruxtecan",
    # Emerging
    "NSCLC immunotherapy biomarker PD-L1 TMB",
    "lung cancer histopathology deep learning mutation prediction",
]

MAX_RESULTS_PER_SOURCE = 5


# ──────────────────────────────────────────────────────────────────────
# PubMed (NCBI E-utilities — free, no API key required for low volume)
# ──────────────────────────────────────────────────────────────────────

async def search_pubmed(query: str, max_results: int = MAX_RESULTS_PER_SOURCE) -> list[dict[str, Any]]:
    """Search PubMed and return abstracts."""
    results = []
    try:
        async with httpx.AsyncClient(timeout=20.0) as client:
            # Step 1: ESearch
            search_resp = await client.get(
                "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi",
                params={
                    "db": "pubmed", "term": query, "retmax": max_results,
                    "sort": "relevance", "retmode": "json",
                },
            )
            if search_resp.status_code != 200:
                return []
            ids = search_resp.json().get("esearchresult", {}).get("idlist", [])
            if not ids:
                return []

            # Step 2: EFetch abstracts
            fetch_resp = await client.get(
                "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi",
                params={
                    "db": "pubmed", "id": ",".join(ids),
                    "rettype": "abstract", "retmode": "xml",
                },
            )
            if fetch_resp.status_code != 200:
                return []

            # Parse XML simply (extract title + abstract text)
            xml_text = fetch_resp.text
            for pmid in ids:
                # Extract abstract sections around PMID
                title = _extract_xml_tag(xml_text, "ArticleTitle")
                abstract = _extract_xml_tag(xml_text, "AbstractText")
                if title or abstract:
                    results.append({
                        "source": "PubMed",
                        "id": f"PMID:{pmid}",
                        "title": title[:300] if title else "",
                        "abstract": abstract[:2000] if abstract else "",
                        "url": f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/",
                        "query": query,
                    })
                    # Remove used content to get next article
                    if title:
                        xml_text = xml_text.replace(title, "", 1)
    except Exception as e:
        logger.warning("PubMed search failed for '%s': %s", query[:50], e)
    return results


# ──────────────────────────────────────────────────────────────────────
# Semantic Scholar (free API, 100 req/5min without key)
# ──────────────────────────────────────────────────────────────────────

async def search_semantic_scholar(query: str, max_results: int = MAX_RESULTS_PER_SOURCE) -> list[dict[str, Any]]:
    """Search Semantic Scholar for papers (with retry on 429)."""
    results = []
    try:
        async with httpx.AsyncClient(timeout=20.0) as client:
            for attempt in range(3):
                resp = await client.get(
                    "https://api.semanticscholar.org/graph/v1/paper/search",
                    params={
                        "query": query, "limit": max_results,
                        "fields": "title,abstract,url,year,citationCount",
                    },
                )
                if resp.status_code == 429:
                    wait = 5 * (attempt + 1)
                    logger.info("Semantic Scholar rate-limited, waiting %ds...", wait)
                    await asyncio.sleep(wait)
                    continue
                break
            if resp.status_code != 200:
                return []
            data = resp.json().get("data", [])
            for paper in data:
                if paper.get("abstract"):
                    results.append({
                        "source": "SemanticScholar",
                        "id": paper.get("paperId", ""),
                        "title": (paper.get("title") or "")[:300],
                        "abstract": (paper.get("abstract") or "")[:2000],
                        "url": paper.get("url", ""),
                        "year": paper.get("year"),
                        "citations": paper.get("citationCount", 0),
                        "query": query,
                    })
    except Exception as e:
        logger.warning("Semantic Scholar search failed for '%s': %s", query[:50], e)
    return results


# ──────────────────────────────────────────────────────────────────────
# arXiv (free, no auth)
# ──────────────────────────────────────────────────────────────────────

async def search_arxiv(query: str, max_results: int = MAX_RESULTS_PER_SOURCE) -> list[dict[str, Any]]:
    """Search arXiv for papers (cs.AI, q-bio, cs.LG categories)."""
    results = []
    try:
        async with httpx.AsyncClient(timeout=20.0, follow_redirects=True) as client:
            resp = await client.get(
                "https://export.arxiv.org/api/query",
                params={
                    "search_query": f"all:{query}",
                    "start": 0, "max_results": max_results,
                    "sortBy": "relevance",
                },
            )
            if resp.status_code != 200:
                return []
            # Simple XML parse
            xml = resp.text
            entries = xml.split("<entry>")[1:]  # skip feed header
            for entry in entries[:max_results]:
                title = _extract_xml_tag(entry, "title")
                summary = _extract_xml_tag(entry, "summary")
                arxiv_id = _extract_xml_tag(entry, "id")
                if title and summary:
                    results.append({
                        "source": "arXiv",
                        "id": arxiv_id or "",
                        "title": title.strip()[:300],
                        "abstract": summary.strip()[:2000],
                        "url": arxiv_id or "",
                        "query": query,
                    })
    except Exception as e:
        logger.warning("arXiv search failed for '%s': %s", query[:50], e)
    return results


# ──────────────────────────────────────────────────────────────────────
# Batch search: all sources, all queries
# ──────────────────────────────────────────────────────────────────────

async def batch_literature_search(
    queries: list[str] | None = None,
    sources: list[str] | None = None,
    max_per_source: int = MAX_RESULTS_PER_SOURCE,
) -> list[dict[str, Any]]:
    """Run batch search across all sources and queries. Returns list of papers."""
    queries = queries or DEFAULT_QUERIES
    sources = sources or ["pubmed", "semantic_scholar", "arxiv"]
    all_papers: list[dict] = []
    seen_titles: set[str] = set()

    for qi, query in enumerate(queries):
        for source in sources:
            if source == "pubmed":
                papers = await search_pubmed(query, max_per_source)
            elif source == "semantic_scholar":
                papers = await search_semantic_scholar(query, max_per_source)
                # Rate limit: Semantic Scholar allows 100 req/5min → wait 3.5s between calls
                await asyncio.sleep(3.5)
            elif source == "arxiv":
                papers = await search_arxiv(query, max_per_source)
                # arXiv asks for 3s delay between calls
                await asyncio.sleep(3.0)
            else:
                continue

            for p in papers:
                title_key = p.get("title", "").lower().strip()[:100]
                if title_key and title_key not in seen_titles:
                    seen_titles.add(title_key)
                    all_papers.append(p)

        logger.info("Batch search [%d/%d]: query='%s' — %d total papers so far", qi + 1, len(queries), query[:40], len(all_papers))

    logger.info("Batch literature search complete: %d unique papers from %d queries", len(all_papers), len(queries))
    return all_papers


# ──────────────────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────────────────

def _extract_xml_tag(xml: str, tag: str) -> str:
    """Simple XML tag extraction (no lxml dependency)."""
    start = xml.find(f"<{tag}")
    if start == -1:
        return ""
    # Find end of opening tag
    close_bracket = xml.find(">", start)
    if close_bracket == -1:
        return ""
    end = xml.find(f"</{tag}>", close_bracket)
    if end == -1:
        return ""
    return xml[close_bracket + 1:end].strip()
