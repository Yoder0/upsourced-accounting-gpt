"""
Upsourced Accounting GPT - Streamlit Chat Interface
Main entry point for the RAG assistant.
"""

import sys
from io import BytesIO
from pathlib import Path

# Add src to path so we can import from config, retrieval, generation
sys.path.insert(0, str(Path(__file__).parent / "src"))

import PyPDF2
import pandas as pd
import streamlit as st

from config import NO_DOC_FALLBACK_MODE, CHROMA_PERSIST_DIR, validate_config
from retrieval import retrieve
from generation import generate_answer
from ingest import ingest_documents

# -----------------------------------------------------------------------------
# Auto-ingestion on fresh cloud deployments (no chroma_db folder present)
# -----------------------------------------------------------------------------
if not CHROMA_PERSIST_DIR.exists() or not any(CHROMA_PERSIST_DIR.iterdir()):
    with st.spinner("Building knowledge base from documents... (~1 minute)"):
        ingest_documents()

# -----------------------------------------------------------------------------
# Page Config
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="Upsourced Accounting GPT",
    page_icon="📊",
    layout="centered",
    initial_sidebar_state="collapsed",
)

# -----------------------------------------------------------------------------
# Custom Styling
# -----------------------------------------------------------------------------
st.markdown(
    """
    <style>
    /* Clean, professional look */
    .main-header {
        font-size: 2rem;
        font-weight: 700;
        color: #1e3a5f;
        margin-bottom: 0.25rem;
    }
    .subtitle {
        font-size: 1rem;
        color: #5a6c7d;
        margin-bottom: 2rem;
    }
    .source-citation {
        font-size: 0.85rem;
        color: #5a6c7d;
        background: #f0f4f8;
        padding: 0.75rem 1rem;
        border-radius: 0.5rem;
        margin-top: 1rem;
        border-left: 4px solid #1e3a5f;
    }
    .source-citation strong {
        color: #1e3a5f;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# -----------------------------------------------------------------------------
# Initialize Session State
# -----------------------------------------------------------------------------
if "messages" not in st.session_state:
    st.session_state.messages = []

# -----------------------------------------------------------------------------
# Header
# -----------------------------------------------------------------------------
st.markdown('<p class="main-header">Upsourced Accounting GPT</p>', unsafe_allow_html=True)
st.markdown(
    '<p class="subtitle">Your AI accounting ops assistant — ask me anything about our procedures and processes</p>',
    unsafe_allow_html=True,
)

# -----------------------------------------------------------------------------
# Validate Config
# -----------------------------------------------------------------------------
config_errors = validate_config()
if config_errors:
    st.error(
        "**Configuration issues:**\n\n" + "\n".join(f"• {e}" for e in config_errors)
        + "\n\nPlease fix these before using the app."
    )
    st.stop()

# -----------------------------------------------------------------------------
# Sidebar: Spreadsheet Upload
# -----------------------------------------------------------------------------
spreadsheet_context = None
pdf_context = None

ROW_LIMIT = 500
PDF_PAGE_LIMIT = 50


def format_source_label(source: dict) -> str:
    """
    Format citation metadata for display in the UI.
    """
    label = f"{source['source_file']} — Page {source['page_number']}"
    if source.get("section_title"):
        label += f" — {source['section_title']}"
    elif source.get("step_or_condition"):
        label += f" — {source['step_or_condition']}"
    elif source.get("scenario_label"):
        label += f" — {source['scenario_label']}"
    return label


def _excel_engine_for_filename(filename: str) -> str:
    name = filename.lower()
    if name.endswith(".xlsx"):
        return "openpyxl"
    if name.endswith(".xls"):
        return "xlrd"
    raise ValueError(f"Unsupported spreadsheet format for file: {filename}")


@st.cache_data(show_spinner=False)
def get_excel_sheet_names(file_bytes: bytes, filename: str) -> list[str]:
    """
    Read sheet names once per uploaded spreadsheet.
    """
    engine = _excel_engine_for_filename(filename)
    try:
        xl = pd.ExcelFile(BytesIO(file_bytes), engine=engine)
        return xl.sheet_names
    except ImportError as e:
        if engine == "xlrd":
            raise ValueError(
                "Reading .xls files requires the xlrd package. "
                "Install it with: pip install xlrd"
            ) from e
        raise


@st.cache_data(show_spinner=False)
def parse_excel_sheet(
    file_bytes: bytes,
    filename: str,
    sheet_name: str,
    row_limit: int,
) -> tuple[pd.DataFrame, int, str]:
    """
    Parse selected spreadsheet sheet once per file/sheet.
    Returns (dataframe_truncated_to_limit, original_total_rows, markdown_text).
    """
    engine = _excel_engine_for_filename(filename)
    try:
        df_full = pd.read_excel(
            BytesIO(file_bytes),
            sheet_name=sheet_name,
            engine=engine,
        )
    except ImportError as e:
        if engine == "xlrd":
            raise ValueError(
                "Reading .xls files requires the xlrd package. "
                "Install it with: pip install xlrd"
            ) from e
        raise

    total_rows = len(df_full)
    df_to_send = df_full
    if total_rows > row_limit:
        df_to_send = df_full.head(row_limit)

    return df_to_send, total_rows, df_to_send.to_markdown(index=False)


@st.cache_data(show_spinner=False)
def parse_pdf_text(file_bytes: bytes, page_limit: int) -> tuple[str, int, int]:
    """
    Extract text from uploaded PDF once per file.
    Returns (joined_page_text, pages_read, total_pages).
    """
    reader = PyPDF2.PdfReader(BytesIO(file_bytes))
    total_pages = len(reader.pages)
    pages_to_read = min(total_pages, page_limit)
    pages = []
    for i in range(pages_to_read):
        text = reader.pages[i].extract_text() or ""
        pages.append(f"--- Page {i + 1} ---\n{text}")
    return "\n\n".join(pages), pages_to_read, total_pages

with st.sidebar:
    with st.expander("Health Benefits Phase 1 Checklist", expanded=False):
        st.markdown(
            "- Period under review\n"
            "- Client methodology: AP bill, auto-withdrawal, or manual accrual\n"
            "- Systems touched: QBO, payroll platform, carrier portal, broker\n"
            "- Payroll frequency and any 3-pay-period months\n"
            "- Medical carrier and any non-medical products in the same clearing account\n"
            "- Whether the task is a monthly tieout, annual rate validation, or mixed-activity cleanup"
        )

    st.markdown("### Upload Spreadsheet(s)")
    st.markdown("Attach one or more Excel files to ask questions about their data alongside the documentation.")

    uploaded_files = st.file_uploader(
        "Choose spreadsheet(s)",
        type=["xlsx", "xls"],
        accept_multiple_files=True,
        label_visibility="collapsed",
    )

    if uploaded_files:
        all_spreadsheet_sections = []
        for uploaded_file in uploaded_files:
            try:
                file_bytes = uploaded_file.getvalue()
                sheet_names = get_excel_sheet_names(file_bytes, uploaded_file.name)

                if len(sheet_names) > 1:
                    selected_sheet = st.selectbox(
                        f"{uploaded_file.name} — sheet", sheet_names
                    )
                else:
                    selected_sheet = sheet_names[0]

                df, total_rows, df_markdown = parse_excel_sheet(
                    file_bytes, uploaded_file.name, selected_sheet, ROW_LIMIT
                )

                if total_rows > ROW_LIMIT:
                    row_note = f" (first {ROW_LIMIT} of {total_rows} rows)"
                else:
                    row_note = ""

                with st.expander(f"📄 {uploaded_file.name} — {len(df)} rows, {len(df.columns)} cols{row_note}", expanded=False):
                    if row_note:
                        st.warning(f"Only the first {ROW_LIMIT} rows will be sent to Claude.")
                    df_display = df.copy()
                    for _c in df_display.select_dtypes(include="object").columns:
                        df_display[_c] = df_display[_c].fillna("").astype(str)
                    st.dataframe(df_display, width="stretch")

                all_spreadsheet_sections.append(
                    f"Filename: {uploaded_file.name}\n"
                    f"Sheet: {selected_sheet}\n\n"
                    f"{df_markdown}"
                )

            except Exception as e:
                st.error(f"Could not read **{uploaded_file.name}**: {e}")

        if all_spreadsheet_sections:
            spreadsheet_context = "\n\n===\n\n".join(all_spreadsheet_sections)

    st.markdown("---")
    st.markdown("### Upload PDF(s)")
    st.markdown("Attach one or more PDF files to review against the documentation.")

    uploaded_pdfs = st.file_uploader(
        "Choose PDF file(s)",
        type=["pdf"],
        accept_multiple_files=True,
        label_visibility="collapsed",
    )

    if uploaded_pdfs:
        all_pdf_sections = []
        for uploaded_pdf in uploaded_pdfs:
            try:
                file_bytes = uploaded_pdf.getvalue()
                joined_pages, pages_to_read, total_pages = parse_pdf_text(
                    file_bytes, PDF_PAGE_LIMIT
                )
                page_note = (
                    f" (first {PDF_PAGE_LIMIT} of {total_pages} pages)"
                    if total_pages > PDF_PAGE_LIMIT
                    else ""
                )

                all_pdf_sections.append(
                    f"Filename: {uploaded_pdf.name}\n\n" + joined_pages
                )

                with st.expander(f"📑 {uploaded_pdf.name} — {pages_to_read} page(s){page_note}", expanded=False):
                    if page_note:
                        st.warning("Only the first 50 pages will be sent to Claude.")
                    st.caption(f"✅ Successfully loaded and ready to query.")
            except Exception as e:
                st.warning(f"Could not read **{uploaded_pdf.name}**: {e}")

        if all_pdf_sections:
            pdf_context = "\n\n===\n\n".join(all_pdf_sections)

# -----------------------------------------------------------------------------
# Chat Interface
# -----------------------------------------------------------------------------
# Display chat history
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])
        if message["role"] == "assistant":
            sources = message.get("sources", [])
            thinking = message.get("thinking", "")
            thinking_failed = message.get("thinking_failed", False)

            if thinking:
                badge_str = " ".join(f"**[{i + 1}]**" for i in range(len(sources)))
                st.markdown(f"Sources: {badge_str}")
                with st.expander("🧠 Show reasoning"):
                    for i, src in enumerate(sources, 1):
                        st.markdown(
                            f"[{i}] **{format_source_label(src)}**"
                        )
                    st.markdown("---")
                    st.markdown(thinking)
            elif sources:
                st.markdown("---")
                st.markdown("**Sources:**")
                for src in sources:
                    st.markdown(
                        f'<div class="source-citation">'
                            f"<strong>{format_source_label(src)}</strong>"
                        f"</div>",
                        unsafe_allow_html=True,
                    )
                if thinking_failed:
                    st.caption("⚠️ Reasoning unavailable for this response.")

# Chat input
st.caption(
    "Phase 1 tip: include period, account, client methodology, and systems touched "
    "(QBO, payroll platform, carrier/AP) for faster execution."
)

if prompt := st.chat_input("Ask a question about our procedures..."):
    # Add user message to history and display
    st.session_state.messages.append({"role": "user", "content": prompt})

    with st.chat_message("user"):
        st.markdown(prompt)

    # Generate response
    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
            try:
                # Retrieve relevant chunks
                chunks = retrieve(prompt)
                thinking_content = ""
                thinking_failed = False
                if not chunks:
                    if NO_DOC_FALLBACK_MODE == "strict_block":
                        answer_content = (
                            "I don't have any documentation loaded yet. "
                            "Please run the ingestion script first to add PDFs from the "
                            "/docs folder."
                        )
                        sources = []
                    else:
                        prior_history = st.session_state.messages[:-1]
                        answer_content, thinking_content, thinking_failed = generate_answer(
                            prompt,
                            chunks,
                            spreadsheet_context,
                            pdf_context=pdf_context,
                            conversation_history=prior_history,
                        )
                        sources = []
                        st.caption(
                            "No documentation chunks were retrieved for this request. "
                            "Response generated with caveats and verification guidance."
                        )
                else:
                    # Generate answer with Claude (pass spreadsheet if one is uploaded)
                    prior_history = st.session_state.messages[:-1]
                    answer_content, thinking_content, thinking_failed = generate_answer(
                        prompt, chunks, spreadsheet_context,
                        pdf_context=pdf_context, conversation_history=prior_history,
                    )
                    sources = [
                        {
                            "source_file": c["source_file"],
                            "page_number": c["page_number"],
                            "section_title": c.get("section_title", ""),
                            "step_or_condition": c.get("step_or_condition", ""),
                            "scenario_label": c.get("scenario_label", ""),
                        }
                        for c in chunks
                    ]

                st.markdown(answer_content)

                if thinking_content:
                    badge_str = " ".join(f"**[{i + 1}]**" for i in range(len(sources)))
                    st.markdown(f"Sources: {badge_str}")
                    with st.expander("🧠 Show reasoning"):
                        for i, src in enumerate(sources, 1):
                            st.markdown(
                                f"[{i}] **{format_source_label(src)}**"
                            )
                        st.markdown("---")
                        st.markdown(thinking_content)
                else:
                    if sources:
                        st.markdown("---")
                        st.markdown("**Sources:**")
                        for src in sources:
                            st.markdown(
                                f'<div class="source-citation">'
                                f"<strong>{format_source_label(src)}</strong>"
                                f"</div>",
                                unsafe_allow_html=True,
                            )
                    if thinking_failed:
                        st.caption("⚠️ Reasoning unavailable for this response.")

                # Store in history
                st.session_state.messages.append(
                    {
                        "role": "assistant",
                        "content": answer_content,
                        "sources": sources,
                        "thinking": thinking_content,
                        "thinking_failed": thinking_failed,
                    }
                )
            except Exception as e:
                st.error(f"Something went wrong: {str(e)}")
                # Don't add failed responses to history

