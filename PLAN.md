# Deployment Plan: Multi-User Access via Streamlit Community Cloud

**Goal:** Deploy the app to a public URL so your boss (and eventually the team) can access it from any browser, with no local setup required.

**Estimated time:** 45–60 minutes  
**Cost:** Free (Streamlit Community Cloud has a free tier)  
**Result:** A shareable URL like `https://upsourced-accounting-gpt.streamlit.app`

---

## Status — Mar 17, 2026

**Deployment complete.** The app is live and accessible to anyone with the link.

**Live URL:** https://upsourced-accounting-gpt-zcbb7bwccar3xsosxsnnh5.streamlit.app/

| What | Status |
|---|---|
| Model name verified (`claude-sonnet-4-20250514`) | Done |
| ChromaDB `@st.cache_resource` caching added to `src/retrieval.py` | Done |
| Auto-ingestion block added to `app.py` | Done |
| `.gitignore` updated (chroma_db excluded, `.streamlit/config.toml` committed) | Done |
| `.streamlit/config.toml` created | Done |
| GitHub repo created: `Yoder0/upsourced-accounting-gpt` (private) | Done |
| Pushed to GitHub — all docs/ PDFs included, `.env` excluded | Done |
| Deployed to Streamlit Community Cloud with `ANTHROPIC_API_KEY` secret | Done |
| Live and tested | Done |

---

## Overview of What We're Doing

Right now the app only runs on your laptop. To make it shareable:

1. Fix two small code issues that will break the deployed app
2. Push the project to a GitHub repository
3. Add a startup routine so the vector database builds itself on the cloud server
4. Deploy on Streamlit Community Cloud and add your API key as a secret
5. Share the URL

---

## Step 1: Fix the Model Name in `config.py`

Before deploying, verify the Claude model name is correct. Open `src/config.py` and check line 47:

```python
CLAUDE_MODEL = "claude-sonnet-4-20250514"
```

Go to [console.anthropic.com/docs/models](https://console.anthropic.com/docs/models) and confirm the exact model identifier string. If it's wrong, the app will fail on every query in production. Common correct formats are:
- `claude-3-7-sonnet-20250219`
- `claude-3-5-sonnet-20241022`

Copy the exact string from the Anthropic docs and update `config.py` to match.

---

## Step 2: Cache the ChromaDB Client

Currently `retrieval.py` creates a new database connection on every single user query. On a shared deployment with multiple users this is wasteful and will slow down responses. Add Streamlit's resource caching so the connection is created once and reused.

In `src/retrieval.py`, replace the `retrieve()` function with a version that uses a cached client. The pattern is:

```python
import streamlit as st

@st.cache_resource
def _get_chroma_client():
    return chromadb.PersistentClient(
        path=str(CHROMA_PERSIST_DIR),
        settings=Settings(anonymized_telemetry=False),
    )
```

Then inside `retrieve()`, call `_get_chroma_client()` instead of creating a new client each time.

> **Note:** `@st.cache_resource` is Streamlit's mechanism for sharing expensive objects (database connections, API clients) across all users and sessions. It creates the object once per server process.

---

## Step 3: Add Auto-Ingestion on Startup

Streamlit Community Cloud is a fresh server with no persistent disk — it won't have your `chroma_db/` folder. The app needs to build it automatically when it starts up, using the PDF files committed to the repo.

Add this block near the top of `app.py`, after the imports and before `st.set_page_config`:

```python
from src.ingest import ingest_documents
from config import CHROMA_PERSIST_DIR

# On a fresh deployment (no chroma_db folder), run ingestion automatically.
# This builds the vector database from the PDFs in docs/ on first startup.
if not CHROMA_PERSIST_DIR.exists() or not any(CHROMA_PERSIST_DIR.iterdir()):
    with st.spinner("Building knowledge base from documents... (first-time setup, ~1 minute)"):
        ingest_documents()
```

This only runs when there's no database present (i.e., first deploy or a fresh server). Normal restarts skip it.

---

## Step 4: Update `.gitignore`

The current `.gitignore` excludes `chroma_db/` and `.streamlit/` — both of which need to change for deployment.

Open `.gitignore` and make these changes:

**Remove this line:**
```
chroma_db/
```
The `chroma_db/` line can stay removed since Step 3 auto-builds it. The folder won't be committed (it's large and binary), and the auto-ingest code handles it.

**Change this line:**
```
.streamlit/
```
To:
```
.streamlit/secrets.toml
```
You want to commit `.streamlit/config.toml` (app configuration) but NOT `secrets.toml` (which will contain your API key locally). Keeping the whole `.streamlit/` folder ignored was fine when running locally, but now you need to commit the config file.

---

## Step 5: Add a Streamlit Config File

Create the file `.streamlit/config.toml` in your project root with the following content:

```toml
[server]
headless = true
enableCORS = false

[theme]
primaryColor = "#1e3a5f"
backgroundColor = "#ffffff"
secondaryBackgroundColor = "#f0f4f8"
textColor = "#1a1a1a"
```

This ensures the app runs correctly in a headless cloud environment and applies your brand colors as the Streamlit theme. This file **should** be committed to GitHub.

---

## Step 6: Create a GitHub Repository

Streamlit Community Cloud deploys directly from GitHub. If you don't already have the project in a repo:

1. Go to [github.com](https://github.com) and create a new **private** repository named `upsourced-accounting-gpt`
2. On your machine, open Terminal and navigate to the project folder:
   ```bash
   cd ~/Desktop/upsourced-accounting-gpt
   git init
   git add .
   git commit -m "Initial commit"
   git branch -M main
   git remote add origin https://github.com/YOUR_USERNAME/upsourced-accounting-gpt.git
   git push -u origin main
   ```

> **Important:** Make sure `.env` is in your `.gitignore` (it already is) and that you never commit it. Your API key must never go to GitHub.

**Verify before pushing:**
- Run `git status` and confirm `.env` is not listed in the files to be committed
- Confirm `docs/` contains your PDF files and they will be committed (they need to be in the repo for auto-ingestion to work)

---

## Step 7: Deploy on Streamlit Community Cloud

1. Go to [share.streamlit.io](https://share.streamlit.io) and sign in with your GitHub account
2. Click **"New app"**
3. Fill in the form:
   - **Repository:** `YOUR_USERNAME/upsourced-accounting-gpt`
   - **Branch:** `main`
   - **Main file path:** `app.py`
4. Click **"Advanced settings"** before deploying
5. In the **Secrets** section, paste:
   ```toml
   ANTHROPIC_API_KEY = "sk-ant-your-actual-key-here"
   ```
   This is the cloud equivalent of your local `.env` file. Streamlit encrypts and stores it securely — it never appears in your repo.
6. Click **"Deploy"**

The app will take 2–4 minutes to build on first deploy. You'll see a log of the build process. Once it shows a green checkmark, your URL is live.

---

## Step 8: Test and Share

1. Open the URL (will be something like `https://upsourced-accounting-gpt.streamlit.app`)
2. On first load, the auto-ingestion spinner will appear for ~60 seconds while it builds the vector database from your docs
3. Ask a test question to confirm it's working end-to-end
4. Share the URL with your boss

> **Note on first-load time:** The very first request after a cold start (or after Streamlit "sleeps" the app due to inactivity) will trigger ingestion again. Subsequent requests in the same session are fast. This is a known limitation of the free Community Cloud tier — apps sleep after ~7 days of inactivity.

---

## Step 9: Updating Documents Going Forward

When you add new PDFs to `docs/`, the process is:

1. Drop the PDF into `docs/`
2. Commit and push to GitHub:
   ```bash
   git add docs/
   git commit -m "Add [document name]"
   git push
   ```
3. In the Streamlit Cloud dashboard, click **"Reboot app"** — this triggers a fresh deploy which will auto-ingest the new files

This replaces the current manual `python -m src.ingest` step with a git push.

---

## Step 10: Set Up Google Sheets Conversation Logging

Once deployed, there's no persistent filesystem on Community Cloud — any log file written by the app gets wiped on restart. Google Sheets is the simplest solution: every question and answer gets appended as a new row to a sheet you can view live, share with your boss, and use to identify which questions the app handles poorly.

### What gets logged

Each row in the sheet will capture:
- Timestamp
- A session ID (random ID per browser session, so you can group a conversation together)
- The user's question
- The app's answer
- Which source documents were cited
- A thumbs up / thumbs down rating (populated later when you add the feedback button)

### Part A: Create the Google Sheet

1. Go to [sheets.google.com](https://sheets.google.com) and create a new spreadsheet
2. Name it **"Upsourced GPT — Conversation Log"**
3. In Row 1, add these headers exactly:
   ```
   timestamp | session_id | question | answer | sources | thumbs_up
   ```
4. Note the **Spreadsheet ID** from the URL — it's the long string between `/d/` and `/edit`:
   ```
   https://docs.google.com/spreadsheets/d/THIS_IS_THE_ID/edit
   ```

### Part B: Create a Google Service Account

The app needs permission to write to the sheet without asking for your Google login every time. A service account is a bot account that has its own credentials.

1. Go to [console.cloud.google.com](https://console.cloud.google.com)
2. Create a new project (or use an existing one) — name it `upsourced-gpt`
3. In the left menu, go to **APIs & Services → Library**
4. Search for **"Google Sheets API"** and click **Enable**
5. Go to **APIs & Services → Credentials**
6. Click **"Create Credentials" → "Service Account"**
7. Name it `upsourced-gpt-logger`, click through the remaining steps
8. Once created, click on the service account, go to the **"Keys"** tab
9. Click **"Add Key" → "Create new key" → JSON** — this downloads a `.json` file to your machine
10. Open that JSON file — you'll need two values from it:
    - `"client_email"` — looks like `upsourced-gpt-logger@upsourced-gpt.iam.gserviceaccount.com`
    - `"private_key"` — the long string starting with `-----BEGIN RSA PRIVATE KEY-----`

### Part C: Share the Sheet with the Service Account

1. Open your Google Sheet
2. Click **Share** (top right)
3. Paste the `client_email` address from the JSON file
4. Give it **Editor** access
5. Click **Send** (ignore the "can't notify" warning — service accounts don't have inboxes)

### Part D: Add the Credentials to Streamlit Secrets

In the Streamlit Community Cloud dashboard, go to your app → **Settings → Secrets** and add:

```toml
ANTHROPIC_API_KEY = "sk-ant-your-actual-key-here"

[gsheets]
spreadsheet_id = "YOUR_SPREADSHEET_ID_HERE"
client_email = "upsourced-gpt-logger@your-project.iam.gserviceaccount.com"
private_key = "-----BEGIN RSA PRIVATE KEY-----\nMIIE...(full key)...\n-----END RSA PRIVATE KEY-----\n"
```

> **Important:** In the `private_key` value, the actual newlines in the key must be written as `\n` on a single line. When you open the JSON file, the key will already be formatted this way — copy it exactly as-is.

For local development, add the same `[gsheets]` block to `.streamlit/secrets.toml` (which is already gitignored).

### Part E: Add the Logging Code

Add `gspread` to `requirements.txt`:
```
gspread>=6.0.0
```

Create a new file `src/logging_sheet.py` with a single function:

```python
import datetime
import streamlit as st
import gspread
from google.oauth2.service_account import Credentials

SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]

@st.cache_resource
def _get_sheet():
    """Cached connection to the Google Sheet. Returns None if not configured."""
    try:
        secrets = st.secrets.get("gsheets", {})
        if not secrets:
            return None
        creds = Credentials.from_service_account_info(
            {
                "type": "service_account",
                "client_email": secrets["client_email"],
                "private_key": secrets["private_key"],
                "token_uri": "https://oauth2.googleapis.com/token",
            },
            scopes=SCOPES,
        )
        client = gspread.authorize(creds)
        return client.open_by_key(secrets["spreadsheet_id"]).sheet1
    except Exception:
        return None  # Logging is non-critical — never crash the app over it


def log_exchange(session_id: str, question: str, answer: str, sources: list[dict]) -> None:
    """Append one Q&A exchange as a new row. Silently skips if sheet is unavailable."""
    sheet = _get_sheet()
    if sheet is None:
        return
    try:
        source_str = ", ".join(
            f"{s['source_file']} p.{s['page_number']}" for s in sources
        )
        sheet.append_row([
            datetime.datetime.now().isoformat(),
            session_id,
            question,
            answer,
            source_str,
            "",  # thumbs_up — populated later when feedback button is added
        ])
    except Exception:
        pass  # Never let a logging failure crash the app
```

### Part F: Wire It Into `app.py`

In `app.py`, add two things:

**1. Generate a session ID once per browser session** (near the top of the session state initialization):
```python
import uuid

if "session_id" not in st.session_state:
    st.session_state.session_id = str(uuid.uuid4())[:8]
```

**2. Call `log_exchange()` after a successful answer** (right after the `st.session_state.messages.append(...)` line):
```python
from src.logging_sheet import log_exchange

log_exchange(
    session_id=st.session_state.session_id,
    question=prompt,
    answer=answer_content,
    sources=sources,
)
```

### Viewing the Log

Open the Google Sheet at any time to see all conversations in real time. You can:
- Filter by `session_id` to read a full conversation
- Sort by `thumbs_up = FALSE` once feedback is added to find weak answers
- Share the sheet with your boss as a read-only link so they can see usage without logging into the app

---

## What This Does NOT Include (Future Work)

- **Login / authentication** — Anyone with the URL can use the app. For initial boss testing this is fine. If you want to restrict access, look into Streamlit's built-in `[auth]` config block (supports Google OAuth) or adding a simple password gate.
- **Thumbs up/down feedback button** — The `thumbs_up` column is in the sheet and ready; wiring up the UI button in `app.py` is the natural next step after logging is confirmed working.
- **Google Drive sync** — Documents still need to be added manually via git push. The Drive sync feature is a separate project described in the roadmap.
- **Persistent conversation history** — Each browser session is independent. Refreshing loses the conversation. This is acceptable for a testing phase.

---

## Checklist Summary

- [x] Verify and fix `CLAUDE_MODEL` name in `src/config.py` — confirmed `claude-sonnet-4-20250514` is valid
- [x] Add `@st.cache_resource` ChromaDB client caching in `src/retrieval.py`
- [x] Add auto-ingestion block to `app.py`
- [x] Update `.gitignore` (allow `.streamlit/config.toml`, keep `secrets.toml` ignored)
- [x] Create `.streamlit/config.toml`
- [x] Create GitHub repo (`Yoder0/upsourced-accounting-gpt`, private) and push all files including `docs/`
- [x] Deploy on Streamlit Community Cloud with API key in Secrets
- [x] Test a question end-to-end on the live URL
- [x] Share URL — https://upsourced-accounting-gpt-zcbb7bwccar3xsosxsnnh5.streamlit.app/
- [ ] Create Google Sheet with headers and note the Spreadsheet ID
- [ ] Create Google Cloud service account and enable Sheets API
- [ ] Share the Google Sheet with the service account email
- [ ] Add `[gsheets]` credentials to Streamlit Secrets (and local `secrets.toml`)
- [ ] Add `gspread` to `requirements.txt`
- [ ] Create `src/logging_sheet.py`
- [ ] Add session ID and `log_exchange()` call to `app.py`
- [ ] Verify rows are appearing in the sheet after a test conversation
