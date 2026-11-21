# Synthetic staging runbook

This runbook is approval-controlled. It does not authorize provisioning or deployment.

## Preflight

1. Confirm the target subscription, resource group and environment are approved.
2. Confirm the GitHub environment is protected and the workflow uses OIDC, not client secrets.
3. Confirm the database backup and rollback owner are assigned.
4. Confirm Entra analyst and reviewer accounts are separate and active.
5. Confirm all live research and model providers are disabled.

## Deployment sequence

1. Run read-only infrastructure inventory.
2. Run the Bicep dependency what-if; stop on unexpected resources or network changes.
3. Provision only the approved dependencies.
4. Build and publish immutable backend/frontend images.
5. Run database migrations through the protected migration job.
6. Deploy the approved image references.
7. Verify `/health` and `/ready`.
8. Sign in as analyst and reviewer; verify role separation and revocation behavior.
9. Execute the synthetic managed-delivery lifecycle.
10. Verify audit events, private storage authorization, report/export behavior and failure handling.

## Shutdown and recovery

- Stop or scale down staging workloads when testing ends where the service supports it.
- Retain logs and audit records according to the approved policy.
- If verification fails, stop traffic, preserve evidence, roll back the application image when schema-compatible and escalate any migration or data issue before retrying.
- Never use a production database, real client dataset or copied Inscend credential for staging.
