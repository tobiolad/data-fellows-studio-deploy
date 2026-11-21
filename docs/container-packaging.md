# Container packaging

Studio has separate images for the FastAPI API and the static portal.

- `backend/Dockerfile` runs as UID `10001`, keeps test identity mode disabled by default and exposes `/health` as a liveness probe.
- `frontend/Dockerfile` serves only the reviewed static assets through Nginx and exposes `/health.html` for a container health probe.
- Neither image contains credentials, database data or provider API keys.

Builds should use immutable image tags tied to a reviewed commit. Runtime secrets belong in the deployment secret store. The backend `/ready` endpoint must be used as the deployment readiness check; `/health` only proves that the process is responding.

The frontend currently reads `window.STUDIO_API_URL` when supplied by the hosting page and otherwise defaults to the local API URL. A staging deployment must provide the API origin through an approved configuration mechanism before exposing the portal.
