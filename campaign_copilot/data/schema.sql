-- Synthetic data for Northwind Community Bank (fictional). Nothing here is real.

CREATE TABLE IF NOT EXISTS branches (
    branch_id      INTEGER PRIMARY KEY,
    name           TEXT NOT NULL,
    city           TEXT NOT NULL,
    metro          TEXT NOT NULL,          -- "Dallas-Fort Worth" or "North Texas"
    opened_year    INTEGER NOT NULL,
    staff_count    INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS customers (
    customer_id        INTEGER PRIMARY KEY,
    branch_id          INTEGER NOT NULL REFERENCES branches(branch_id),
    segment            TEXT NOT NULL,      -- young_professional | family | retiree | small_business | student
    tenure_years       REAL NOT NULL,
    has_checking       INTEGER NOT NULL,   -- 0/1
    has_savings        INTEGER NOT NULL,
    has_credit_card    INTEGER NOT NULL,
    has_mortgage       INTEGER NOT NULL,
    has_auto_loan      INTEGER NOT NULL,
    checking_balance   REAL NOT NULL,
    savings_balance    REAL NOT NULL,
    digital_engagement REAL NOT NULL,      -- 0.0 (never logs in) to 1.0 (daily)
    direct_mail_opt_in INTEGER NOT NULL,
    email_opt_in       INTEGER NOT NULL,
    last_contact_days  INTEGER NOT NULL    -- days since any marketing contact
);

CREATE TABLE IF NOT EXISTS campaigns (
    campaign_id      INTEGER PRIMARY KEY,
    name             TEXT NOT NULL,
    quarter          TEXT NOT NULL,        -- e.g. 2025-Q3
    product          TEXT NOT NULL,        -- checking | savings | credit_card | mortgage | auto_loan
    channel          TEXT NOT NULL,        -- direct_mail | email | digital_ad
    branch_id        INTEGER REFERENCES branches(branch_id),  -- NULL means all branches
    target_segment   TEXT,                 -- NULL means no segment filter
    offer            TEXT NOT NULL,        -- plain-English offer
    offer_apy        REAL,                 -- NULL when the offer has no rate
    sent_count       INTEGER NOT NULL,
    response_count   INTEGER NOT NULL,
    accounts_opened  INTEGER NOT NULL,
    cost_usd         REAL NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_customers_branch ON customers(branch_id);
CREATE INDEX IF NOT EXISTS idx_customers_segment ON customers(segment);
CREATE INDEX IF NOT EXISTS idx_campaigns_product ON campaigns(product, channel);
