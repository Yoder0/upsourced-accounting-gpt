"""
Central configuration for Upsourced Accounting GPT.
Loads API keys from .env and defines all tunable settings.
"""

import os
from pathlib import Path

from dotenv import load_dotenv

# Load environment variables from .env file (project root)
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(_PROJECT_ROOT / ".env")

# -----------------------------------------------------------------------------
# API Keys (loaded from .env - NEVER hardcode)
# -----------------------------------------------------------------------------
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")

# -----------------------------------------------------------------------------
# Paths
# -----------------------------------------------------------------------------
# Project root (parent of src/)
PROJECT_ROOT = _PROJECT_ROOT
DOCS_DIR = PROJECT_ROOT / "docs"
CHROMA_PERSIST_DIR = PROJECT_ROOT / "chroma_db"

# -----------------------------------------------------------------------------
# Chunking Settings
# -----------------------------------------------------------------------------
CHUNK_SIZE_TOKENS = 800
CHUNK_OVERLAP_TOKENS = 200

# -----------------------------------------------------------------------------
# Retrieval Settings
# -----------------------------------------------------------------------------
RETRIEVAL_TOP_K = 8
SEMANTIC_RETRIEVAL_CANDIDATES = 12
KEYWORD_RETRIEVAL_CANDIDATES = 12

# -----------------------------------------------------------------------------
# Conversation Memory
# -----------------------------------------------------------------------------
CONVERSATION_HISTORY_TURNS = 3  # number of prior exchanges passed to Claude

# -----------------------------------------------------------------------------
# Prompt/Behavior Controls
# -----------------------------------------------------------------------------
# Options: "strict_block", "guided_analysis"
NO_DOC_FALLBACK_MODE = "guided_analysis"
# Options: "table-first", "narrative-first"
DEFAULT_DELIVERABLE_STYLE = "table-first"
# Options: "concise", "standard", "detailed"
PHASE_WALKTHROUGH_VERBOSITY = "standard"

# -----------------------------------------------------------------------------
# Model Names
# -----------------------------------------------------------------------------
CLAUDE_MODEL = "claude-sonnet-4-20250514"

# -----------------------------------------------------------------------------
# Extended Thinking
# -----------------------------------------------------------------------------
EXTENDED_THINKING_ENABLED = True
THINKING_BUDGET_TOKENS = 10000

# -----------------------------------------------------------------------------
# ChromaDB
# -----------------------------------------------------------------------------
CHROMA_COLLECTION_NAME = "upsourced_accounting_docs"

def validate_config() -> list[str]:
    """
    Validate that required config is present. Returns list of error messages.
    """
    errors = []
    if not ANTHROPIC_API_KEY:
        errors.append("ANTHROPIC_API_KEY is not set in .env")
    if NO_DOC_FALLBACK_MODE not in {"strict_block", "guided_analysis"}:
        errors.append(
            "NO_DOC_FALLBACK_MODE must be 'strict_block' or 'guided_analysis'"
        )
    if DEFAULT_DELIVERABLE_STYLE not in {"table-first", "narrative-first"}:
        errors.append(
            "DEFAULT_DELIVERABLE_STYLE must be 'table-first' or 'narrative-first'"
        )
    if PHASE_WALKTHROUGH_VERBOSITY not in {"concise", "standard", "detailed"}:
        errors.append(
            "PHASE_WALKTHROUGH_VERBOSITY must be 'concise', 'standard', or 'detailed'"
        )
    return errors

