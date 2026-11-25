-- Client billing: one Stripe customer per organization, invoices sent through
-- Stripe's hosted pages, and an idempotency ledger for webhook events.

CREATE TABLE IF NOT EXISTS billing_customers (
    organization_id uuid PRIMARY KEY REFERENCES organizations(id) ON DELETE CASCADE,
    stripe_customer_id text NOT NULL UNIQUE CHECK (length(trim(stripe_customer_id)) >= 2),
    email text NOT NULL CHECK (position('@' in email) > 1),
    created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS invoices (
    id uuid PRIMARY KEY,
    organization_id uuid NOT NULL REFERENCES organizations(id) ON DELETE RESTRICT,
    stripe_invoice_id text NOT NULL UNIQUE CHECK (length(trim(stripe_invoice_id)) >= 2),
    stripe_customer_id text NOT NULL,
    description text NOT NULL CHECK (length(trim(description)) >= 2),
    amount_cents bigint NOT NULL CHECK (amount_cents > 0),
    currency text NOT NULL CHECK (currency = lower(currency) AND length(currency) = 3),
    status text NOT NULL CHECK (status IN ('draft', 'open', 'paid', 'void', 'uncollectible')),
    hosted_invoice_url text,
    created_by text NOT NULL CHECK (length(trim(created_by)) >= 2),
    created_at timestamptz NOT NULL DEFAULT now(),
    sent_at timestamptz,
    paid_at timestamptz,
    updated_at timestamptz NOT NULL DEFAULT now(),
    CHECK (sent_at IS NULL OR sent_at >= created_at),
    CHECK (paid_at IS NULL OR paid_at >= created_at)
);

CREATE INDEX IF NOT EXISTS invoices_organization_idx ON invoices(organization_id, created_at DESC);

CREATE TABLE IF NOT EXISTS stripe_webhook_events (
    id text PRIMARY KEY,
    type text NOT NULL,
    received_at timestamptz NOT NULL DEFAULT now()
);
