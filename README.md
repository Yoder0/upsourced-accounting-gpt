# Upsourced Accounting GPT

An internal AI assistant for accounting operations that answers questions about company procedures using your actual SOPs and internal documentation. Built as a RAG (Retrieval-Augmented Generation) proof of concept.

## How It Works

1. PDFs in `docs/` are chunked and stored in a local ChromaDB vector database
2. When you ask a question, the app combines semantic retrieval with exact-term reranking so carrier names, product acronyms, and worked examples are easier to surface together
3. Those chunks are passed to Claude as context, which generates a step-by-step answer with source citations
4. **Conversation memory** — The last 3 exchanges are passed to Claude so follow-up questions (e.g., "can you explain step 3 in more detail?") work naturally within a session
5. **Optional spreadsheet** — You can upload an Excel file in the sidebar; its data is included as context for questions about that file
6. No document content ever leaves your machine — embeddings are generated locally by ChromaDB's built-in model

## Assistant Operating Model (Prompt Redesign)

The assistant now runs each engagement in four phases:

1. **Establish Context** — confirm account type, period, methodology, and systems touched.
2. **Execute Procedure** — apply documented SOP steps with explicit calculations and citations.
3. **Produce Deliverable** — output a usable schedule/table/JE/memo, not commentary alone.
4. **Flag Exceptions & Next Steps** — state what tied, what did not, and exact follow-up/escalation actions.

### What changed for preparers

- The assistant asks more targeted clarifying questions up front, especially in first-time tieouts.
- Responses are deliverable-first (tables/schedules/workpaper-ready language) when possible.
- Operating principle is **help first, caveat second**.
- If documentation is missing for a scenario, the assistant can still provide generalized analysis with explicit caveats.

### Generalized analysis policy

When analysis relies on general accounting reasoning instead of documented procedures:

- The assistant should not assign numerical confidence percentages.
- The response should make clear that the conclusion is a working view based on available evidence, not a documented procedure.
- When the scenario is ambiguous, the assistant should provide ranked hypotheses, uncertainty language, and concrete verification/escalation steps.

## Health Benefits Workflow Tips

For health-benefits work, the assistant is most reliable when Phase 1 context is explicit before the tieout starts. Include:

- Period under review
- Client methodology: AP bill, auto-withdrawal, or manual accrual
- Systems touched: QBO, payroll platform, carrier portal, broker
- Payroll frequency and any 3-pay-period months
- Medical carrier and whether non-medical products are mixed into the same clearing account
- Whether the task is a monthly tieout, annual rate validation, or cleanup of mixed activity

The `docs/` set now includes a prepaid-benefits supplement to help with annual premiums, prior-year true-ups, prepaid assets, monthly amortization, and non-medical benefit products such as Guardian `DBL/PFL`.

## Prerequisites

- **Python 3.11+**
- **Anthropic API key** — Get one at [console.anthropic.com](https://console.anthropic.com/)

## Setup

1. **Navigate to the project**
   ```bash
   cd upsourced-accounting-gpt
   ```

2. **Create a virtual environment**
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate   # On Windows: .venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure your API key**

   Create a `.env` file in the project root with your Anthropic key:
   ```
   ANTHROPIC_API_KEY=sk-ant-your-key-here
   ```
   > Make sure the file contains the full `ANTHROPIC_API_KEY=` prefix, not just the raw key value.

5. **Add your documents**
   - Place PDF files in the `docs/` folder
   - Supported format: PDF only (see note on SRT/transcripts below)

## Running the Application

### Step 1: Ingest Documents

Run this once after adding or changing documents:

```bash
python -m src.ingest
```

This will:
- Load all PDFs from `docs/`
- Chunk them (800 tokens with 200 token overlap)
- Embed and store in a local ChromaDB database (`chroma_db/`)
- Print progress for each document

> **Re-running ingestion replaces all existing chunks** — it's safe to run as many times as you want.

### Step 2: Launch the App

```bash
streamlit run app.py
```

Open [http://localhost:8501](http://localhost:8501) in your browser and start asking questions. Use the sidebar to optionally attach an Excel file for questions about spreadsheet data. Follow-up questions (e.g., "explain step 2 in more detail") work within a session — Claude sees the last 3 exchanges.

## Project Structure

```
upsourced-accounting-gpt/
├── docs/                    # Drop PDF files here
├── src/
│   ├── ingest.py           # PDF loading, chunking, ChromaDB storage
│   ├── retrieval.py        # Hybrid retrieval + exact-term reranking
│   ├── generation.py       # Claude API call with RAG prompt
│   └── config.py           # Settings, paths, model names, conversation memory
├── evals/                  # Regression scenarios for health-benefits review
├── tools/                  # Utilities such as SOP PDF generation
├── chroma_db/              # Auto-created: local vector database (after ingestion)
├── app.py                  # Streamlit chat interface
├── requirements.txt
├── .env                    # Your API key (create this manually)
├── .env.example            # Template
└── .gitignore
```

## Adding New Documents

1. Add PDF files to `docs/`
2. Re-run ingestion: `python -m src.ingest`
3. Restart the Streamlit app if it's already running

If you add or revise SOP PDFs, re-run ingestion before testing the change. Retrieval will not pick up new content until the Chroma database is rebuilt.

## Using Call Transcripts (Grain, Zoom, etc.)

Raw `.srt` subtitle files don't ingest well — the timestamp lines pollute the chunks. Before adding a transcript:

1. Clean the transcript: remove all timestamp lines and subtitle index numbers, join fragmented sentences, remove filler words ("um", "uh")
2. Paste the clean text into a Google Doc
3. Export as PDF → File → Download → PDF
4. Drop the PDF in `docs/` and re-run ingestion

## Known Limitations

- **POC** — Not production-ready; no auth, no multi-user support
- **Manual doc sync** — You must re-run ingestion when docs change
- **PDF only** — No native support for `.docx`, `.txt`, or Google Docs
- **Local only** — ChromaDB runs on a single machine; not shared across team members

## Regression Pack

Use the scenarios in `evals/health_benefits_regression_cases.json` when you change prompts, retrieval, or SOPs. The first goal is to prevent regressions on:

- Annual prepaid DBL/PFL handling
- Annualized payroll-vs-invoice rate validation
- Mixed medical and non-medical clearing activity
- Three-pay-period timing variances
- Pending carrier credits after employee terminations

## Future Roadmap

- Live Google Drive sync for automatic doc updates
- Slack bot integration for team-wide access
- Danswer/Onyx migration for production deployment
- Client-specific knowledge bases
- Usage analytics and training gap reporting
