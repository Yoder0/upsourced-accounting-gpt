# Health Benefits Regression Pack

Use `health_benefits_regression_cases.json` after changing any of the following:

- SOP PDFs in `docs/`
- Prompt behavior in `src/generation.py`
- Retrieval logic in `src/retrieval.py`
- Ingestion metadata in `src/ingest.py`

Each case defines:

- The scenario to test
- The conclusion the assistant should reach
- Required calculations or framing
- Failure patterns that should not reappear

Recommended workflow:

1. Re-run `python -m src.ingest` after changing any SOP PDFs.
2. Start the app and run each regression prompt or a fuller version of the scenario.
3. Check that the response includes the expected reasoning and avoids the prohibited failure patterns.
4. Update the regression pack whenever you discover a new failure mode worth preserving.
