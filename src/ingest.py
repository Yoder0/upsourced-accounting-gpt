"""
Document ingestion pipeline for Upsourced Accounting GPT.
Loads PDFs from /docs, chunks them, and stores in ChromaDB using its
built-in default embedding model (all-MiniLM-L6-v2) — no external API needed.
"""

import logging
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import chromadb
from chromadb.config import Settings
from PyPDF2 import PdfReader
import tiktoken

from config import (
    CHROMA_COLLECTION_NAME,
    CHROMA_PERSIST_DIR,
    CHUNK_OVERLAP_TOKENS,
    CHUNK_SIZE_TOKENS,
    DOCS_DIR,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Use cl100k_base for accurate token counting during chunking
TOKENIZER = tiktoken.get_encoding("cl100k_base")

PRODUCT_TAG_RULES = {
    "medical": ("anthem", "medical", "health insurance"),
    "guardian": ("guardian",),
    "dental": ("dental",),
    "vision": ("vision",),
    "life": ("life insurance", "basic life", "supplemental life"),
    "dbl": ("dbl", "disability benefits law"),
    "pfl": ("pfl", "paid family leave"),
    "non_medical": (
        "non-medical",
        "non medical",
        "dental",
        "vision",
        "life",
        "dbl",
        "pfl",
        "disability",
    ),
    "annual_tieout": ("annual tieout", "annualized", "x26", "x24", "x12"),
    "prepaid": ("prepaid", "annual premium", "true-up", "amortization", "amortize"),
}


def chunk_text_by_tokens(
    text: str,
    chunk_size: int = CHUNK_SIZE_TOKENS,
    overlap: int = CHUNK_OVERLAP_TOKENS,
) -> list[str]:
    """
    Split text into chunks of approximately chunk_size tokens with overlap.
    Tries to break at sentence boundaries when possible.
    """
    tokens = TOKENIZER.encode(text)
    chunks = []
    start = 0

    while start < len(tokens):
        end = min(start + chunk_size, len(tokens))
        chunk_tokens = tokens[start:end]
        chunk_text = TOKENIZER.decode(chunk_tokens)

        # Try to break at a sentence boundary to avoid mid-sentence cuts
        if end < len(tokens):
            last_sentence_end = max(
                chunk_text.rfind(". "),
                chunk_text.rfind("! "),
                chunk_text.rfind("? "),
            )
            if last_sentence_end > chunk_size // 2:
                chunk_text = chunk_text[: last_sentence_end + 1]
                chunk_tokens = TOKENIZER.encode(chunk_text)

        chunks.append(chunk_text.strip())
        start = end - overlap if end < len(tokens) else len(tokens)

    return chunks


def load_pdf_text(filepath: Path) -> list[tuple[int, str]]:
    """
    Load text from a PDF. Returns list of (page_number, page_text) tuples (1-indexed).
    """
    # TODO: Consider pypdf (successor to PyPDF2) for better extraction of complex PDFs
    reader = PdfReader(filepath)
    pages = []
    for i, page in enumerate(reader.pages):
        try:
            text = page.extract_text()
            if text and text.strip():
                pages.append((i + 1, text.strip()))
        except Exception as e:
            logger.warning(f"Failed to extract page {i + 1} from {filepath.name}: {e}")
    return pages


def extract_document_title(pages: list[tuple[int, str]], pdf_path: Path) -> str:
    """
    Infer a readable document title from the first non-empty line.
    """
    if not pages:
        return pdf_path.stem

    first_page_lines = [line.strip() for line in pages[0][1].splitlines() if line.strip()]
    return first_page_lines[0] if first_page_lines else pdf_path.stem


def infer_chunk_metadata(chunk_text: str, document_title: str) -> dict:
    """
    Infer citation-friendly metadata from chunk text.
    """
    lines = [line.strip() for line in chunk_text.splitlines() if line.strip()]

    section_title = ""
    step_or_condition = ""
    scenario_label = ""

    section_pattern = re.compile(r"^\d+\.\s+.+")
    step_pattern = re.compile(r"^(Step|Condition)\s+\d+:\s+.+", re.IGNORECASE)
    scenario_pattern = re.compile(r"^SCENARIO\s+[A-Z].+", re.IGNORECASE)

    for line in lines:
        if not section_title and section_pattern.match(line):
            section_title = line
        if not step_or_condition and step_pattern.match(line):
            step_or_condition = line
        if not scenario_label and scenario_pattern.match(line):
            scenario_label = line

    if not section_title:
        for line in lines:
            if "annual tieout" in line.lower():
                section_title = line
                break

    lower_text = chunk_text.lower()
    product_tags = [
        tag
        for tag, patterns in PRODUCT_TAG_RULES.items()
        if any(pattern in lower_text for pattern in patterns)
    ]

    return {
        "document_title": document_title,
        "section_title": section_title,
        "step_or_condition": step_or_condition,
        "scenario_label": scenario_label,
        "product_tags": ", ".join(product_tags),
    }


def ingest_documents() -> None:
    """
    Main ingestion pipeline:
    1. Load all PDFs from docs/
    2. Chunk with 800 token size, 200 token overlap
    3. Store in ChromaDB — its built-in model handles embeddings automatically
    """
    DOCS_DIR.mkdir(parents=True, exist_ok=True)
    pdf_files = list(DOCS_DIR.glob("*.pdf"))

    if not pdf_files:
        logger.warning(f"No PDF files found in {DOCS_DIR}. Add PDFs and run again.")
        return

    CHROMA_PERSIST_DIR.mkdir(parents=True, exist_ok=True)
    chroma_client = chromadb.PersistentClient(
        path=str(CHROMA_PERSIST_DIR),
        settings=Settings(anonymized_telemetry=False),
    )

    all_ids = []
    all_documents = []
    all_metadatas = []

    total_docs = len(pdf_files)
    for doc_idx, pdf_path in enumerate(pdf_files, start=1):
        logger.info(f"Processing document {doc_idx}/{total_docs}: {pdf_path.name}")

        try:
            pages = load_pdf_text(pdf_path)
        except Exception as e:
            logger.warning(f"Skipping {pdf_path.name} - failed to load: {e}")
            continue

        if not pages:
            logger.warning(f"Skipping {pdf_path.name} - no text extracted")
            continue

        document_title = extract_document_title(pages, pdf_path)

        # Join pages and track boundaries so we can attribute chunks to pages
        full_text_parts = []
        page_boundaries = []
        current_pos = 0
        for page_num, page_text in pages:
            page_boundaries.append((page_num, current_pos, current_pos + len(page_text)))
            full_text_parts.append(page_text)
            current_pos += len(page_text) + 2  # +2 for \n\n separator

        full_text = "\n\n".join(full_text_parts)
        chunks = chunk_text_by_tokens(full_text)
        if not chunks:
            continue

        # Attribute each chunk to the page where it starts
        char_pos = 0
        for chunk_idx, chunk in enumerate(chunks):
            chunk_start = full_text.find(chunk, char_pos)
            if chunk_start < 0:
                chunk_start = char_pos
            char_pos = chunk_start + len(chunk)

            page_num = 1
            for pnum, pstart, pend in page_boundaries:
                if pstart <= chunk_start < pend:
                    page_num = pnum
                    break

            chunk_id = f"{pdf_path.stem}_p{page_num}_c{chunk_idx}"
            inferred_meta = infer_chunk_metadata(chunk, document_title)
            all_ids.append(chunk_id)
            all_documents.append(chunk)
            all_metadatas.append(
                {
                    "source_file": pdf_path.name,
                    "page_number": page_num,
                    "chunk_index": chunk_idx,
                    "document_title": inferred_meta["document_title"],
                    "section_title": inferred_meta["section_title"],
                    "step_or_condition": inferred_meta["step_or_condition"],
                    "scenario_label": inferred_meta["scenario_label"],
                    "product_tags": inferred_meta["product_tags"],
                }
            )

    if not all_ids:
        logger.warning("No chunks to store. Check that PDFs contain extractable text.")
        return

    # Replace existing collection for clean re-ingestion
    try:
        chroma_client.delete_collection(CHROMA_COLLECTION_NAME)
    except Exception:
        pass
    collection = chroma_client.create_collection(
        name=CHROMA_COLLECTION_NAME,
        metadata={"description": "Upsourced Accounting SOPs and documentation"},
    )

    # Add documents — ChromaDB embeds them automatically using its built-in model
    batch_size = 100
    for i in range(0, len(all_ids), batch_size):
        end = min(i + batch_size, len(all_ids))
        collection.add(
            ids=all_ids[i:end],
            documents=all_documents[i:end],
            metadatas=all_metadatas[i:end],
        )

    logger.info(f"Ingestion complete. Stored {len(all_ids)} chunks from {total_docs} documents.")


if __name__ == "__main__":
    ingest_documents()
