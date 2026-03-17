"""
Retrieval module for Upsourced Accounting GPT.
Queries ChromaDB for the top-k most relevant chunks to a user question.
Uses hybrid retrieval: semantic search plus lightweight keyword reranking.
"""

from collections import defaultdict
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import chromadb
from chromadb.config import Settings
import streamlit as st

from config import (
    CHROMA_COLLECTION_NAME,
    CHROMA_PERSIST_DIR,
    KEYWORD_RETRIEVAL_CANDIDATES,
    RETRIEVAL_TOP_K,
    SEMANTIC_RETRIEVAL_CANDIDATES,
)

STOPWORDS = {
    "a",
    "an",
    "and",
    "are",
    "as",
    "at",
    "be",
    "by",
    "for",
    "from",
    "how",
    "i",
    "if",
    "in",
    "is",
    "it",
    "month",
    "of",
    "on",
    "or",
    "our",
    "should",
    "the",
    "this",
    "to",
    "what",
    "when",
    "which",
    "with",
}


def _normalize_query_terms(query: str) -> list[str]:
    """
    Extract exact-match terms that are useful for keyword reranking.
    """
    normalized = query.lower().replace("/", " ").replace("-", " ")
    tokens = re.findall(r"[a-z0-9]+", normalized)
    unique_terms = []
    seen = set()
    for token in tokens:
        if len(token) < 3 or token in STOPWORDS or token in seen:
            continue
        seen.add(token)
        unique_terms.append(token)
    return unique_terms


def _keyword_score(query_terms: list[str], text: str, metadata: dict) -> int:
    """
    Score a chunk by exact-term overlap across the text and metadata fields.
    """
    product_tags = metadata.get("product_tags", "")
    if isinstance(product_tags, list):
        product_tags = " ".join(product_tags)

    searchable_parts = [
        text.lower(),
        str(metadata.get("document_title", "")).lower(),
        str(metadata.get("section_title", "")).lower(),
        str(metadata.get("step_or_condition", "")).lower(),
        str(metadata.get("scenario_label", "")).lower(),
        str(product_tags).lower(),
    ]
    searchable_text = "\n".join(part for part in searchable_parts if part)

    score = 0
    for term in query_terms:
        if re.search(rf"\b{re.escape(term)}\b", searchable_text):
            score += 3
        elif term in searchable_text:
            score += 1
    return score


def _build_chunk(doc: str, meta: dict) -> dict:
    """
    Normalize collection results into the chunk shape used by the app.
    """
    product_tags = meta.get("product_tags", "")
    if isinstance(product_tags, str):
        product_tags = [tag.strip() for tag in product_tags.split(",") if tag.strip()]

    return {
        "text": doc,
        "source_file": meta.get("source_file", "Unknown"),
        "page_number": meta.get("page_number", 0),
        "document_title": meta.get("document_title", ""),
        "section_title": meta.get("section_title", ""),
        "step_or_condition": meta.get("step_or_condition", ""),
        "scenario_label": meta.get("scenario_label", ""),
        "product_tags": product_tags,
    }


@st.cache_resource
def _get_chroma_client() -> chromadb.PersistentClient:
    """Cached ChromaDB client shared across all users and sessions."""
    return chromadb.PersistentClient(
        path=str(CHROMA_PERSIST_DIR),
        settings=Settings(anonymized_telemetry=False),
    )


def retrieve(query: str, top_k: int = RETRIEVAL_TOP_K) -> list[dict]:
    """
    Retrieve the top_k most relevant chunks for a user question.

    ChromaDB embeds the query automatically using the same built-in model
    that was used during ingestion — no external API required.

    Returns list of dicts with text plus source metadata.
    """
    chroma_client = _get_chroma_client()

    try:
        collection = chroma_client.get_collection(CHROMA_COLLECTION_NAME)
    except Exception:
        return []

    query_terms = _normalize_query_terms(query)

    semantic_results = collection.query(
        query_texts=[query],
        n_results=max(top_k, SEMANTIC_RETRIEVAL_CANDIDATES),
        include=["documents", "metadatas"],
    )

    scored_candidates: dict[str, dict] = defaultdict(dict)

    if semantic_results["documents"] and semantic_results["documents"][0]:
        semantic_count = len(semantic_results["documents"][0])
        for idx, (chunk_id, doc, meta) in enumerate(
            zip(
                semantic_results["ids"][0],
                semantic_results["documents"][0],
                semantic_results["metadatas"][0],
            )
        ):
            scored_candidates[chunk_id] = {
                "chunk": _build_chunk(doc, meta),
                "score": (semantic_count - idx) * 10,
            }

    if query_terms:
        all_docs = collection.get(include=["documents", "metadatas"])
        keyword_matches = []
        for chunk_id, doc, meta in zip(
            all_docs["ids"],
            all_docs["documents"],
            all_docs["metadatas"],
        ):
            score = _keyword_score(query_terms, doc, meta)
            if score > 0:
                keyword_matches.append((score, chunk_id, doc, meta))

        keyword_matches.sort(key=lambda item: item[0], reverse=True)
        for score, chunk_id, doc, meta in keyword_matches[:KEYWORD_RETRIEVAL_CANDIDATES]:
            if chunk_id not in scored_candidates:
                scored_candidates[chunk_id] = {
                    "chunk": _build_chunk(doc, meta),
                    "score": 0,
                }
            scored_candidates[chunk_id]["score"] += score

    ranked = sorted(
        scored_candidates.values(),
        key=lambda item: (
            item["score"],
            item["chunk"].get("page_number", 0),
        ),
        reverse=True,
    )

    return [item["chunk"] for item in ranked[:top_k]]
