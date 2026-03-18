# Upsourced Accounting GPT — Work Plan

---

## Completed — Mar 17, 2026

Streamlit Community Cloud deployment is live.

**Live URL:** https://upsourced-accounting-gpt-zcbb7bwccar3xsosxsnnh5.streamlit.app/

| What | Notes |
|---|---|
| Model name verified | `claude-sonnet-4-20250514` confirmed valid |
| ChromaDB `@st.cache_resource` caching | `src/retrieval.py` — shared across all users/sessions |
| Auto-ingestion on startup | `app.py` — rebuilds DB from `docs/` on fresh server |
| `.streamlit/config.toml` | Headless server settings + brand colors |
| GitHub repo | `Yoder0/upsourced-accounting-gpt` (private) |
| Streamlit Cloud deploy | `ANTHROPIC_API_KEY` stored in Secrets |

---

## Next: Google Drive Document Sync

### Goal

Replace the manual git-push workflow with a shared Google Drive folder. Anyone with access drops a PDF in the folder. The app picks it up automatically — no GitHub, no terminal required.

### The Re-ingestion Problem

Two distinct issues need to be addressed:

**Issue 1 — Cold start after Streamlit sleep**
Streamlit Community Cloud wipes the server disk after ~7 days of inactivity. ChromaDB is gone and everything must be re-ingested from scratch. With the current doc set this takes ~60–90 seconds.

This is unavoidable as long as ChromaDB is the vector store. The long-term fix is migrating to a persistent cloud vector database (see Pinecone section below). For now, the spinner on cold start is acceptable.

**Issue 2 — Incremental updates (new doc added to Drive)**
When a new PDF is added to Drive, we want to ingest only that file — not rebuild the entire database. A file manifest stored in the Drive folder itself tracks what has already been ingested and its MD5 hash. On startup, the app compares Drive contents against the manifest and only downloads and ingests new or changed files.

This means adding a doc goes from "git push + reboot + 90 second full rebuild" to "drop in Drive + reboot + 10 second partial ingest."

---

### Implementation

#### Part A: Google Cloud Setup (~20 minutes, done once)

1. Go to [console.cloud.google.com](https://console.cloud.google.com)
2. Create (or reuse) a project — `upsourced-gpt`
3. **APIs & Services → Library** → enable **Google Drive API** and **Google Sheets API**
4. **APIs & Services → Credentials → Create Credentials → Service Account**
   - Name: `upsourced-gpt-drive`
   - Skip optional role/user steps
5. Click the service account → **Keys → Add Key → Create new key → JSON**
   - Save the downloaded file — you need `client_email` and `private_key` from it
6. Create a Google Drive folder named **"Upsourced GPT — Documents"**
7. Share the folder with the service account's `client_email` — give it **Viewer** access
8. Copy the folder ID from the URL (the long string after `/folders/`)

#### Part B: Add Credentials to Streamlit Secrets

In the Streamlit Cloud dashboard → your app → **Settings → Secrets**, add to the existing secrets block:

```toml
ANTHROPIC_API_KEY = "sk-ant-..."

[gdrive]
folder_id = "YOUR_FOLDER_ID_HERE"
client_email = "upsourced-gpt-drive@upsourced-gpt.iam.gserviceaccount.com"
private_key = "-----BEGIN RSA PRIVATE KEY-----\n...\n-----END RSA PRIVATE KEY-----\n"
```

For local development, add the same `[gdrive]` block to `.streamlit/secrets.toml` (already gitignored).

#### Part C: Add dependencies to `requirements.txt`

```
google-api-python-client>=2.100.0
google-auth>=2.23.0
```

#### Part D: Create `src/drive_sync.py`

This module handles all Drive interaction: listing files, downloading PDFs, and maintaining the manifest.

```python
"""
Google Drive sync for Upsourced Accounting GPT.
Downloads PDFs from the configured Drive folder and maintains a manifest
so only new or changed files are re-ingested.
"""

import hashlib
import json
import tempfile
from pathlib import Path

import streamlit as st
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
from google.oauth2.service_account import Credentials

MANIFEST_FILENAME = ".ingest_manifest.json"
SCOPES = ["https://www.googleapis.com/auth/drive.readonly"]


@st.cache_resource
def _get_drive_service():
    """Cached Drive API client shared across all sessions."""
    secrets = st.secrets.get("gdrive", {})
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
    return build("drive", "v3", credentials=creds, cache_discovery=False)


def list_drive_pdfs() -> list[dict]:
    """Return list of {id, name, md5Checksum} for all PDFs in the folder."""
    service = _get_drive_service()
    if not service:
        return []
    folder_id = st.secrets["gdrive"]["folder_id"]
    results = service.files().list(
        q=f"'{folder_id}' in parents and mimeType='application/pdf' and trashed=false",
        fields="files(id, name, md5Checksum)",
    ).execute()
    return results.get("files", [])


def download_pdf(file_id: str, dest_path: Path) -> None:
    """Download a single Drive file to dest_path."""
    service = _get_drive_service()
    request = service.files().get_media(fileId=file_id)
    with open(dest_path, "wb") as f:
        downloader = MediaIoBaseDownload(f, request)
        done = False
        while not done:
            _, done = downloader.next_chunk()


def sync_drive_to_docs(docs_dir: Path) -> list[Path]:
    """
    Download new or changed PDFs from Drive to docs_dir.
    Returns list of paths that need to be (re-)ingested.
    Returns None if Drive is not configured (fall back to local docs/).
    """
    service = _get_drive_service()
    if not service:
        return None  # Drive not configured — caller uses local docs/

    docs_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = docs_dir / MANIFEST_FILENAME
    manifest = {}
    if manifest_path.exists():
        manifest = json.loads(manifest_path.read_text())

    drive_files = list_drive_pdfs()
    to_ingest = []

    for f in drive_files:
        name = f["name"]
        md5 = f.get("md5Checksum", "")
        if manifest.get(name, {}).get("md5") == md5:
            continue  # unchanged — skip
        dest = docs_dir / name
        download_pdf(f["id"], dest)
        manifest[name] = {"md5": md5, "file_id": f["id"]}
        to_ingest.append(dest)

    # Remove local files that were deleted from Drive
    drive_names = {f["name"] for f in drive_files}
    for local_pdf in docs_dir.glob("*.pdf"):
        if local_pdf.name not in drive_names:
            local_pdf.unlink()
            manifest.pop(local_pdf.name, None)

    manifest_path.write_text(json.dumps(manifest, indent=2))
    return to_ingest
```

#### Part E: Update `src/ingest.py`

Add a function that ingests only a specific list of files (for incremental updates), alongside the existing `ingest_documents()` which rebuilds everything.

```python
def ingest_files(paths: list[Path]) -> None:
    """Ingest only the specified PDF files (incremental update)."""
    # Same logic as ingest_documents() but scoped to the provided paths
    # rather than globbing all of docs/
```

#### Part F: Update the auto-ingest block in `app.py`

Replace the current startup block with one that:
1. Tries to sync from Drive
2. If Drive is configured and ChromaDB exists: only re-ingests changed files
3. If Drive is configured and ChromaDB is missing (cold start): full rebuild
4. If Drive is not configured: falls back to local `docs/` as before

```python
from src.drive_sync import sync_drive_to_docs
from src.ingest import ingest_documents, ingest_files
from config import CHROMA_PERSIST_DIR, DOCS_DIR

drive_files_to_ingest = sync_drive_to_docs(DOCS_DIR)

if drive_files_to_ingest is None:
    # Drive not configured — use local docs/ as before
    if not CHROMA_PERSIST_DIR.exists() or not any(CHROMA_PERSIST_DIR.iterdir()):
        with st.spinner("Building knowledge base from documents... (~1 minute)"):
            ingest_documents()
elif not CHROMA_PERSIST_DIR.exists() or not any(CHROMA_PERSIST_DIR.iterdir()):
    # Cold start — full rebuild from whatever is now in docs/
    with st.spinner("Building knowledge base from documents... (~1 minute)"):
        ingest_documents()
elif drive_files_to_ingest:
    # Incremental — only re-ingest new or changed files
    with st.spinner(f"Syncing {len(drive_files_to_ingest)} updated document(s)..."):
        ingest_files(drive_files_to_ingest)
```

---

### Checklist

- [ ] Enable Drive API in Google Cloud console
- [ ] Create service account `upsourced-gpt-drive` and download JSON key
- [ ] Create Drive folder and share with service account (Viewer)
- [ ] Add `[gdrive]` block to Streamlit Secrets
- [ ] Add `[gdrive]` block to local `.streamlit/secrets.toml`
- [ ] Add `google-api-python-client` and `google-auth` to `requirements.txt`
- [ ] Create `src/drive_sync.py`
- [ ] Add `ingest_files()` to `src/ingest.py`
- [ ] Update startup block in `app.py`
- [ ] Upload existing docs to Drive folder
- [ ] Test incremental update: add one PDF to Drive, reboot app, confirm only that file ingests
- [ ] Test cold start: confirm full rebuild works from Drive

---

## Future: Persistent Vector Store (Pinecone)

### When this becomes urgent

Two scale thresholds to watch:

| Doc count | Problem |
|---|---|
| ~30+ PDFs | Cold-start rebuild after Streamlit sleep climbs past 3–4 minutes — unacceptable wait for a team member hitting a woken app |
| ~50+ PDFs | The keyword scoring in `src/retrieval.py` scans every chunk on every query. At ~1,500+ chunks this adds 3–5 seconds of latency per question |

Both problems disappear with Pinecone. At the current doc count (~10 PDFs) neither is an issue yet, but the Drive sync plan will accelerate how fast docs accumulate. Revisit this when the folder crosses ~25–30 PDFs.

### How it changes things

- ChromaDB (local, wiped on sleep) → Pinecone (cloud-hosted, always available)
- Cold start goes from minutes to ~2 seconds — embeddings are stored permanently, nothing to rebuild
- Incremental ingestion is the default — new docs add to the index, nothing is rebuilt
- Keyword scan replaced by Pinecone's native metadata filtering, which is fast regardless of index size

### What it requires

- Free Pinecone account (free tier: 1 index, 100k vectors — enough for ~3,000 PDFs)
- `pinecone-client` added to `requirements.txt`
- `PINECONE_API_KEY` added to Streamlit Secrets
- Rewrite `src/ingest.py` and `src/retrieval.py` to use Pinecone instead of ChromaDB
- Embeddings must come from an external model since ChromaDB's built-in embedder can't be used with Pinecone — `text-embedding-3-small` from OpenAI (~$0.02 per 1M tokens, negligible cost) or Anthropic's embedding API

This is a meaningful rewrite of the retrieval layer (~4–6 hours) but unlocks production-quality performance. Worth doing after the Drive sync is stable and the doc count starts climbing.

---

## Backlog

- **Google Sheets conversation logging** — Detailed in the original `PLAN.md` Steps 10A–F. Service account setup overlaps with Drive sync above; can be added in the same pass.
- **Thumbs up/down feedback button** — `thumbs_up` column already reserved in the Sheets schema.
- **Authentication** — Currently anyone with the URL can use the app. Streamlit's built-in `[auth]` config block supports Google OAuth; a simple password gate is also possible with `st.secrets`.
- **Google Drive sync for Slack** — Slack bot integration for team-wide access without opening a browser.
- **Client-specific knowledge bases** — Separate ChromaDB collections (or Pinecone namespaces) per client.
