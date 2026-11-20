# Studio database migrations

Migrations live in `migrations/` and are applied lexically inside one transaction. The repository records applied versions in `studio_schema_migrations`; rerunning a completed migration is a no-op.

Production rules:

- Run migrations from a reviewed, approval-controlled job before application rollout.
- Use a dedicated Studio database; never point these migrations at BizPilot or another product database.
- Set `STUDIO_PERSISTENCE=postgres` only after migrations succeed; unsupported domain endpoints fail closed with `501` until their repository methods are implemented.
- Use a least-privilege migration identity for schema changes and a separate runtime identity for ordinary reads/writes.
- Never run migrations against a live client database from a pull request.
- Take and verify a backup before destructive or irreversible changes.
- Add immutable successor columns/rows for domain history rather than overwriting approved artifacts.
- Set `STUDIO_TEST_DATABASE_URL` only in a protected synthetic test environment.
