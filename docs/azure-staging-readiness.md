# Studio staging readiness

This document describes the smallest approval-controlled deployment boundary for
the synthetic Studio pilot. It does not provision resources or prove live
connectivity.

## Reuse boundary

The BizPilot staging subscription/resource group and VNet are existing approved
infrastructure candidates. Studio should reuse the Container Apps environment
and registry only when the owner confirms workload isolation, managed-identity
permissions and image repository separation. Studio must not reuse an Inscend
database, storage account, image or credential.

The following dependencies should be separate data resources in the approved
resource group: PostgreSQL Flexible Server/database, private Blob Storage,
Key Vault and Storage Queue. Private endpoints and DNS links must be scoped to
the Studio data resources. A dedicated Container Apps revision and runtime
managed identity are required for the API and worker.

## Read-only validation

Run .github/workflows/azure-staging-preflight.yml from the protected
azure-inventory environment. It checks subscription/resource-group identity,
VNet/subnets/delegations, supported private-endpoint policy values, Container
Apps environment state and ACR admin-authentication settings. defaultOutboundAccess=false
is reported for review; configuration inspection cannot prove ACR image pulls,
DNS resolution or private PostgreSQL/Blob/Key Vault connectivity.

The workflow intentionally does not inspect secrets, billing values or customer
data. Sponsorship balance, expiry, eligible services and provider-side quotas
require billing/sponsorship access and remain unverified with resource-group
Reader access.

## Deployment gates

1. Owner approves the exact resources, names, region and incremental cost.
2. A protected deployment identity is configured with resource-scoped
   permissions; the inventory identity remains Reader-only.
3. Entra API/SPA registrations and separate synthetic analyst/reviewer accounts
   are created. STUDIO_TEST_MODE remains disabled in staging.
4. PostgreSQL and private storage resources are created, private DNS is linked,
   and Key Vault references are configured without copying secret values into
   GitHub.
5. Apply migrations in a one-shot protected job, then deploy immutable image
   digests and run /health and /ready.
6. Run synthetic role-separated browser verification, inspect audit events and
   retain the evidence before accepting the staging release.

## Migration and rollback

Apply migrations in lexical order (001 through the latest) through the
protected migration job. The repository records checksums and fails closed if
an applied migration changes. Schema changes are additive and should be
validated with a PostgreSQL backup before deployment. Roll back application
images only when the schema remains compatible; restore the database only under
an incident decision with an explicit recovery point and owner.

## Cost guardrails

Prices are estimates until the Sponsorship subscription quote and current
Canada Central meter prices are verified. The likely fixed staging costs are
PostgreSQL Flexible Server, private endpoints and Log Analytics; Blob, Queue,
Key Vault and ACR Basic are generally usage-based or low fixed-cost services.
Keep one small Container Apps revision, bounded log retention, no NAT Gateway
unless a connectivity probe proves it necessary, and stop or scale down
nonessential workloads between test sessions. A budget alert is a notification,
not a hard spending cap.

## Required owner actions

- Configure the azure-inventory GitHub environment and approve the OIDC
  federated credential subject used by this repository.
- Verify the owner can see Sponsorship balance/expiry and current spend.
- Approve the separate Studio data resources and deployment identity.
- Create Entra registrations, redirect URIs, API audience and two synthetic
  staff accounts.
- Approve the first deployment and live connectivity probe; no paid provider
  (Azure OpenAI, Tavily or Exa) is enabled by this workflow.
