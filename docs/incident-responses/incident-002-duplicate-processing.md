# Incident Post-Mortem: Duplicate Transaction Processing

**Incident Card (Day 2):** FinCore posted a P2P transfer twice due to a
network timeout retry. Customer was charged double (INR 15,000 overcharged).

## Root Cause
The legacy system treated each inbound API call as a new intent. A client
timeout triggered an automatic retry; the server had already committed the
first request but the client never saw the response, so it retried — and
the server processed it again as a brand-new transaction.

## Design Solution Implemented
1. **`idempotency_keys` table** (`migrations/004`) — every state-changing
   request must carry a client-generated key. Looked up *before* any
   business logic runs.
2. **Conflict detection** — if the key exists with a matching request hash,
   the stored response is replayed (HTTP 200) with zero new processing. If
   the hash differs, HTTP 409 is returned.
3. **`ledger_entries.idempotency_key`** is also `UNIQUE` at the database
   level — a second layer of protection even if the service-layer check is
   bypassed.
4. **Atomicity** — all journal lines for one transaction are wrapped in a
   single DB transaction (`db_transaction()` context manager); a crash
   mid-write rolls back everything, so retries never see a half-committed
   state.
5. **Stale-PROCESSING cleanup job** — a background job marks idempotency
   keys older than 5 minutes in `PROCESSING` state as `FAILED`, allowing a
   legitimate retry without leaking unbounded rows.

## Verification
`tests/integration/idempotency.test.py` (planned Day 3) submits the same
P2P transfer twice concurrently and asserts exactly one journal entry pair
is created and the second response is a byte-for-byte replay of the first.
