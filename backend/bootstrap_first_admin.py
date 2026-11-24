"""One-off: list pending Studio accounts, or grant the sole one admin.

Run manually via a Railway pre-deploy override, never as part of the
regular deploy pipeline. Deliberately does nothing but print when the
situation is ambiguous (zero or more than one pending account), rather
than guessing which account to grant.
"""
import os

import psycopg

with psycopg.connect(os.environ["STUDIO_DATABASE_URL"]) as conn:
    with conn.cursor() as cur:
        cur.execute("SELECT id, email, name, created_at FROM accounts WHERE global_role IS NULL ORDER BY created_at")
        pending = cur.fetchall()
        print(f"Pending accounts ({len(pending)}):")
        for row in pending:
            print(f"  id={row[0]} email={row[1]} name={row[2]!r} created_at={row[3]}")
        if len(pending) == 1:
            account_id = pending[0][0]
            cur.execute("UPDATE accounts SET global_role = 'admin' WHERE id = %s", (account_id,))
            conn.commit()
            print(f"Granted admin to the one pending account: {pending[0][1]}")
        else:
            print("Not exactly one pending account -- granted nothing.")
