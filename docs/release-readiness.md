# Studio release-readiness handoff

## Current evidence

- The latest local candidate is PR #33 (`codex/studio-container-hardening`).
- Synthetic and PostgreSQL-backed tests pass locally and in GitHub Actions.
- `/health` is liveness only. `/ready` is the configuration readiness gate.
- No live Entra token, Azure database, blob store or production data has been used.

## Recommended merge order

Merge the stack in dependency order, keeping every pull request under review:

`#1 → #2 → #3 → #4 → #5 → #6 → #7 → #8 → #9 → #10 → #11 → #12 → #13 → #14 → #15 → #16 → #17 → #18`

PR #19 is currently parallel to PR #20: both are based on the migration-checksum branch. Merge or rebase PR #19's AI review portal changes before merging the #20–#33 descendant chain. Then continue:

`#19 → #20 → #21 → #22 → #23 → #24 → #25 → #26 → #27 → #28 → #29 → #30 → #31 → #32 → #33`

Do not merge a later branch until its declared base is present. After each merge, rerun backend tests, migration checks and frontend validation.

## Migration and rollback

1. Take an approved PostgreSQL backup and record the backup identifier.
2. Run the migration runner against the staging database using a least-privilege migration identity.
3. Confirm `studio_schema_migrations` contains every version and checksum.
4. Run the PostgreSQL integration suite and `/ready` configuration check.
5. Deploy the application image only after the migration succeeds.
6. If the application image must be rolled back, restore the prior image only when it is schema-compatible. Do not delete or reverse applied migrations; use an immutable successor migration for corrections.
7. If a migration fails, keep the transaction rollback, preserve the failure logs, restore from the approved backup only under the recovery procedure and stop traffic until reviewed.

## Owner approvals before staging

- Approve the PR merge order and enable protected environments.
- Configure the Entra tenant, API audience, SPA redirect URI and separate analyst/reviewer test identities.
- Configure GitHub OIDC federated credentials and least-privilege deployment roles.
- Approve PostgreSQL, private storage, Key Vault, managed identity and monitoring resources/costs.
- Confirm backup retention, restore test timing and data-retention policy.
- Approve synthetic-only staging data and keep Tavily, Exa and Azure OpenAI disabled initially.

## Release blockers

Local checks do not verify live Entra authentication, private network connectivity, database restore, blob authorization, monitoring delivery or authenticated browser behavior. Those remain explicit staging gates.
