# Data Fellows Studio

This is the local bootstrap for the new managed-delivery platform. The GitHub organization currently rejects creation of `Data-Fellows/data-fellows-studio` for the available token (`403 Resource not accessible by integration`), so this isolated repository is not yet a remote PR.

The first vertical slice is synthetic-only and uses an explicit test identity adapter. It demonstrates:

`client organization → admin project → approved professional assignment → bounded deterministic AI planning → internal review → client acceptance → completion`

The test identity adapter is disabled unless `STUDIO_TEST_MODE=true`. It is not an authentication mechanism for deployment. The production boundary is Microsoft Entra workforce/external identity with server-side authorization.

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
