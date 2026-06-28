-- seeds/chart_of_accounts.sql
-- Minimum 19 accounts per Project Requirements Part A1.2 / Section A1.2 table.
-- normal_balance: ASSET/EXPENSE -> DEBIT ; LIABILITY/EQUITY/REVENUE -> CREDIT

INSERT INTO accounts (id, account_code, account_name, account_type, sub_type, currency, normal_balance, is_active, is_contra)
VALUES
  (gen_random_uuid(), '1001', 'Customer Wallet - Primary (INR)',     'ASSET',     'Current Asset',      'INR', 'DEBIT',  true, false),
  (gen_random_uuid(), '1002', 'Customer Wallet - USD Holdings',      'ASSET',     'Current Asset',      'USD', 'DEBIT',  true, false),
  (gen_random_uuid(), '1003', 'Customer Wallet - EUR Holdings',      'ASSET',     'Current Asset',      'EUR', 'DEBIT',  true, false),
  (gen_random_uuid(), '1010', 'Merchant Settlement - Pending',       'ASSET',     'Current Asset',      'INR', 'DEBIT',  true, false),
  (gen_random_uuid(), '1020', 'Loan Receivable - Personal',          'ASSET',     'Non-Current Asset',  'INR', 'DEBIT',  true, false),
  (gen_random_uuid(), '1030', 'Interest Receivable - Accrued',       'ASSET',     'Current Asset',      'INR', 'DEBIT',  true, false),
  (gen_random_uuid(), '2001', 'Customer Deposit Liability',          'LIABILITY', 'Current Liability',  'INR', 'CREDIT', true, false),
  (gen_random_uuid(), '2002', 'Merchant Payable - Pending',          'LIABILITY', 'Current Liability',  'INR', 'CREDIT', true, false),
  (gen_random_uuid(), '2010', 'Interest Payable - Savings',          'LIABILITY', 'Current Liability',  'INR', 'CREDIT', true, false),
  (gen_random_uuid(), '2020', 'Tax Collected at Source (TCS)',       'LIABILITY', 'Current Liability',  'INR', 'CREDIT', true, false),
  (gen_random_uuid(), '3001', 'Retained Earnings',                   'EQUITY',    'Retained Earnings',  'INR', 'CREDIT', true, false),
  (gen_random_uuid(), '4001', 'Transaction Fee Revenue',              'REVENUE',   'Operating Revenue',  'INR', 'CREDIT', true, false),
  (gen_random_uuid(), '4002', 'Interest Income - Loans',              'REVENUE',   'Operating Revenue',  'INR', 'CREDIT', true, false),
  (gen_random_uuid(), '4003', 'FX Conversion Revenue',                'REVENUE',   'Operating Revenue',  'INR', 'CREDIT', true, false),
  (gen_random_uuid(), '4010', 'Interchange Revenue',                  'REVENUE',   'Operating Revenue',  'INR', 'CREDIT', true, false),
  (gen_random_uuid(), '5001', 'Payment Gateway Fees',                 'EXPENSE',   'Operating Expense',  'INR', 'DEBIT',  true, false),
  (gen_random_uuid(), '5002', 'Cashback Expense',                     'EXPENSE',   'Marketing Expense',  'INR', 'DEBIT',  true, false),
  (gen_random_uuid(), '5003', 'Interest Expense - Savings',           'EXPENSE',   'Operating Expense',  'INR', 'DEBIT',  true, false),
  (gen_random_uuid(), '5010', 'FX Conversion Cost',                   'EXPENSE',   'Operating Expense',  'INR', 'DEBIT',  true, false),
  -- Phase 1 addition (documented in docs/submission-notes.md): Reward
  -- Points Liability is required by Transaction Type #19 (Reward Points
  -- Redemption) but was not enumerated in the original 19-account CoA.
  (gen_random_uuid(), '2030', 'Reward Points Liability',             'LIABILITY', 'Current Liability',  'INR', 'CREDIT', true, false)
ON CONFLICT (account_code) DO NOTHING;
