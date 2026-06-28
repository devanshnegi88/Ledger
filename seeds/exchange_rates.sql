-- seeds/exchange_rates.sql
-- Sample exchange rate snapshots for USD/INR, EUR/INR (Part A3.1).
-- valid_until = NULL means this is the currently active snapshot.

INSERT INTO exchange_rate_snapshots
  (snapshot_id, base_currency, quote_currency, rate, inverse_rate, source, captured_at, valid_from, valid_until)
VALUES
  (gen_random_uuid(), 'USD', 'INR', 83.42150000, 0.01198740, 'INTERNAL', now(), now(), NULL),
  (gen_random_uuid(), 'EUR', 'INR', 90.15300000, 0.01109250, 'INTERNAL', now(), now(), NULL),
  (gen_random_uuid(), 'INR', 'USD', 0.01198740, 83.42150000, 'INTERNAL', now(), now(), NULL),
  (gen_random_uuid(), 'INR', 'EUR', 0.01109250, 90.15300000, 'INTERNAL', now(), now(), NULL);
