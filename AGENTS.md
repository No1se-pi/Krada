# Instructions for contributors

- Keep business rules in `backend/src/krada/modules/*/domain.py`; domain code must not import FastAPI, SQLAlchemy, Redis, or MAX SDK.
- Every tenant-owned query must receive trusted `TenantContext`; never accept `school_id` from a player request body.
- State-changing endpoints require an `Idempotency-Key` where retries can duplicate value.
- Persist state, ledger entry, and outbox event in one database transaction.
- Add migrations for schema changes and update relevant docs/ADR in the same change.
- Never expose correct answers before an attempt is evaluated.
- Run backend tests and frontend type/build checks before claiming completion.
- Production must reject mock authentication and placeholder secrets.
