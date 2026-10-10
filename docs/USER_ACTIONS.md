# User Action Items

## Active Setup Status
- `INGESTION_STATE=user_preingested` is active.
- Data is already ingested in Synapt; the probe will inspect and work with existing content.
- Automated pipeline execution will proceed through all phases autonomously.

## Next Steps for the User (Reference Only)
1. Verify `.env` contains valid credentials if running live modes (`GEMINI_API_KEY` / `OPENROUTER_API_KEY`, `SYNAPT_USERNAME`, `SYNAPT_PASSWORD`, `SYNAPT_PROVIDER_ID`).
2. Run `python -m scripts.dev api` to start the backend microservice.
3. Run `python -m scripts.dev ui` to launch the Streamlit frontend.
