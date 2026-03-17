# Run Upsourced Accounting GPT

Use this quick guide any time you close the app and want to start it again.

## 1) Open Terminal and go to the project

```bash
cd /Users/jakeyoder/Desktop/upsourced-accounting-gpt
```

## 2) Activate the virtual environment

```bash
source .venv/bin/activate
```

## 3) (Optional) Re-ingest docs if you changed files in `docs/`

```bash
python -m src.ingest
```

## 4) Start Streamlit

```bash
streamlit run app.py
```

If `streamlit` is not found, run:

```bash
.venv/bin/streamlit run app.py
```

## 5) Open in browser

Use the URL shown in Terminal (for example `http://localhost:8501` or `http://localhost:8505`).

## Before your first health-benefits tieout

Give the app the Phase 1 context up front so it can choose the right procedure:

- Period under review
- Client methodology: AP bill, auto-withdrawal, or manual accrual
- Systems touched: QBO, payroll platform, carrier portal, broker
- Payroll frequency and any 3-pay-period months
- Medical carrier and whether non-medical products are in the same clearing account
- Whether you want a monthly tieout, annual rate validation, or mixed-activity cleanup

Example prompt:

```text
Tie out the Feb 2026 health benefits clearing account for Client X.
Methodology: manual accrual in QBO.
Systems touched: QBO, Gusto, Guardian portal.
Payroll: biweekly, 2 pay periods in February.
Medical carrier: Anthem. Non-medical items from Guardian DBL/PFL also hit the same clearing account.
Task: separate non-medical activity first, then complete the monthly tieout and flag anything that needs escalation.
```

## Stop the app

In the same terminal window, press:

```bash
Ctrl + C
```

## Troubleshooting: Browse files lag or "Open" won't work

If clicking "Browse files" causes heavy loading and you can't select "Open", you likely have multiple Streamlit instances running. Kill them and restart cleanly:

```bash
pkill -f "streamlit run app.py"
cd /Users/jakeyoder/Desktop/upsourced-accounting-gpt
source .venv/bin/activate
streamlit run app.py
```

Then open only the single URL shown. If it still hangs, close old app tabs, hard refresh (`Cmd+Shift+R`), or try a different browser.
