# Incident Post-Mortem: Stale Exchange Rate Used in Conversion

**Incident Card (Day 6):** USD deposit converted at a stale rate (48 hours
old). Customer received INR 4,200 less than market rate.

## Root Cause
The legacy system cached FX rates without a freshness check. A rate fetched
once was reused indefinitely until the next scheduled refresh, so a
conversion could silently execute against a two-day-old rate during a
period of currency volatility.

## Design Solution Implemented
1. **`exchange_rate_snapshots`** table (Part A3.1) stores `captured_at`,
   `valid_from`, and `valid_until` for every rate — immutable, append-only.
2. **`exchange_rate_service.get_latest_rate()`** explicitly checks
   `captured_at` against `settings.fx_rate_stale_threshold_hours`
   (configurable, default 12h) and raises `StaleRateError` (HTTP 422) if
   exceeded — the conversion is rejected outright rather than silently
   using stale data.
3. **`StaleRateError`** is a `LedgerError` subclass, so it surfaces through
   the structured error response format (Part A10.2) with a clear,
   actionable message.
4. Graceful degradation (Part A10.5) for a *future* phase: when the FX
   provider itself is down, the documented fallback is to use the most
   recent cached rate **with an explicit warning to the user and a wider
   spread** — not to silently proceed as if nothing changed. This is
   distinct from the bug here, which was using a stale rate *without* any
   warning or spread adjustment.

## Verification
`tests/integration/test_fx_conversion.py::test_stale_rate_is_rejected`
inserts a rate snapshot captured 48 hours ago and asserts the conversion
attempt raises `StaleRateError` rather than completing silently.
