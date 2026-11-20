# Data Fellows Studio

This is the first synthetic-only managed-delivery foundation for Data Fellows Studio. Implementation is developed through reviewed feature branches.

The first vertical slice is synthetic-only and uses an explicit test identity adapter. It demonstrates:

`client organization → admin project → approved professional assignment → bounded deterministic AI planning → internal review → client acceptance → completion`

The test identity adapter is disabled unless `STUDIO_TEST_MODE=true`. It is not an authentication mechanism for deployment. The production boundary is Microsoft Entra workforce/external identity with server-side authorization.

## Microsoft Entra configuration

Production startup must set `STUDIO_ENTRA_ENABLED=true`, `STUDIO_ENTRA_TENANT_ID` and `STUDIO_ENTRA_AUDIENCE`. The issuer and JWKS URL default to the Microsoft Entra v2 endpoints for that tenant and can be overridden with `STUDIO_ENTRA_ISSUER` and `STUDIO_ENTRA_JWKS_URL` for a verified tenant configuration. The validator accepts only signed RSA tokens with required `exp`, `iat`, `iss`, `aud` and `sub` claims, checks `tid`, and bounds JWKS responses and network timeouts. Token roles are identity metadata only; organization memberships and project assignments remain the authorization source of truth.

## Local run

```text
STUDIO_TEST_MODE=true uvicorn backend.app:app --reload --port 8100
```

The lightweight demo UI is `frontend/index.html`. It is intentionally labelled as a synthetic harness until Entra registrations and a real frontend build are approved.

## Security boundary

- Public registration does not exist.
- Roles are assigned by an administrator through a server-side membership endpoint.
- Every project, assignment, deliverable, AI run and acceptance checks organization/project membership.
- Professionals must be approved before assignment.
- Reviewers cannot approve their own submissions.
- AI planning is deterministic and bounded; it cannot deploy, pay, message a client or change scope.
- Every consequential mutation creates an audit event.
