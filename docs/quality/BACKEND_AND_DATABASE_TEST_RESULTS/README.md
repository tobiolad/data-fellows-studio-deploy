# Backend and database verification

| Command | Passed | Failed | Skipped |
|---|---:|---:|---:|
| `python -m pytest backend -q` with no test DSN | 28 | 0 | 7 |
| Same command with `STUDIO_TEST_DATABASE_URL` pointing to a fresh local PostgreSQL 16 database | 35 | 0 | 0 |

The second row includes the 28 tests from the first row. Seven are database-specific. All migrations through 008 ran. The database suite includes migration checksum and idempotency checks, profile version conflicts, admission denials, reviewed delivery, client acceptance and audit checks. It uses a separate test database from the browser walkthroughs. Raw pytest summaries are in this directory.

An intermediate run reused a previously populated disposable database. It returned 31 passes and one failure because an existing fixture profile had version 2 where the test expected its first save. A fresh database passed. Test isolation on repeated runs against an already used DSN remains a fixture limitation. Never point this suite at a shared or persistent staging database.

No live Entra tenant, Stripe events, real documents or production traffic were involved.
