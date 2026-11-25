"""Synthetic-first managed delivery API for Data Fellows Studio.

The in-memory repository makes the first vertical slice deterministic and easy
to test. Production must replace it with PostgreSQL repositories and Microsoft
Entra token validation before any real data is accepted.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from datetime import datetime, timezone
from functools import lru_cache
from threading import Lock
from typing import Literal
from uuid import UUID, uuid4

from fastapi import FastAPI, HTTPException, Query, Request, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from backend.admission import QUALIFICATION_POLICY_VERSION, check_approval, evidence_status
from backend.auth import EntraSettings, EntraTokenValidator, HttpJwksProvider, TokenValidationError
from backend import model_gateway
from backend.google_auth import (
    GOOGLE_ENABLED_ENV,
    GoogleAuthError,
    GoogleOAuthClient,
    GoogleOAuthSettings,
    issue_session_token,
    validate_session_token,
)
from backend.persistence import PersistenceConfigurationError, PostgresRepository, SYNTHETIC_AGENT_ID
from backend.stripe_billing import (
    BILLING_ENABLED_ENV,
    StripeBillingClient,
    StripeBillingError,
    StripeBillingSettings,
    verify_webhook_signature,
)


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass(frozen=True)
class Identity:
    actor_id: str
    roles: frozenset[str]


@dataclass
class Store:
    organizations: dict[str, dict] = field(default_factory=dict)
    memberships: dict[tuple[str, str], set[str]] = field(default_factory=dict)
    approved_professionals: set[str] = field(default_factory=set)
    professional_admissions: dict[str, dict] = field(default_factory=dict)
    professional_profiles: dict[str, dict] = field(default_factory=dict)
    engagements: dict[str, dict] = field(default_factory=dict)
    projects: dict[str, dict] = field(default_factory=dict)
    work_packages: dict[str, dict] = field(default_factory=dict)
    assignments: dict[str, dict] = field(default_factory=dict)
    ai_runs: dict[str, dict] = field(default_factory=dict)
    artifacts: dict[str, dict] = field(default_factory=dict)
    deliverables: dict[str, dict] = field(default_factory=dict)
    reviews: dict[str, dict] = field(default_factory=dict)
    client_revision_requests: dict[str, dict] = field(default_factory=dict)
    project_requests: dict[str, dict] = field(default_factory=dict)
    handovers: dict[str, dict] = field(default_factory=dict)
    project_messages: dict[str, dict] = field(default_factory=dict)
    project_documents: dict[str, dict] = field(default_factory=dict)
    notifications: dict[str, dict] = field(default_factory=dict)
    opportunities: dict[str, dict] = field(default_factory=dict)
    opportunity_interests: dict[str, dict] = field(default_factory=dict)
    audit: list[dict] = field(default_factory=list)

    def event(self, actor: Identity, action: str, resource_type: str, resource_id: str, metadata: dict | None = None, organization_id: str | None = None) -> None:
        self.audit.append({
            "id": str(uuid4()),
            "actor_id": actor.actor_id,
            "action": action,
            "resource_type": resource_type,
            "resource_id": resource_id,
            "metadata": metadata or {},
            "organization_id": organization_id,
            "created_at": now(),
        })

    def reset(self) -> None:
        self.organizations.clear()
        self.memberships.clear()
        self.approved_professionals.clear()
        self.professional_admissions.clear()
        self.professional_profiles.clear()
        self.engagements.clear()
        self.projects.clear()
        self.work_packages.clear()
        self.assignments.clear()
        self.ai_runs.clear()
        self.artifacts.clear()
        self.deliverables.clear()
        self.reviews.clear()
        self.client_revision_requests.clear()
        self.project_requests.clear()
        self.handovers.clear()
        self.project_messages.clear()
        self.project_documents.clear()
        self.notifications.clear()
        self.opportunities.clear()
        self.opportunity_interests.clear()
        self.audit.clear()


store = Store()
_deliverable_lock = Lock()
app = FastAPI(title="Data Fellows Studio", docs_url=None, redoc_url=None)
def _allowed_frontend_origins() -> list[str]:
    """The fixed local dev origins, plus whatever deployed frontend origins an
    operator lists in STUDIO_EXTRA_ALLOWED_ORIGINS (comma-separated, e.g.
    "https://studio.datafellowsai.com,https://data-fellows-studio-git-main-tobis-projects-2a038191.vercel.app")."""
    origins = [
        "http://localhost:5173",
        "http://localhost:8100",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:8100",
    ]
    extra = os.getenv("STUDIO_EXTRA_ALLOWED_ORIGINS", "")
    origins.extend(origin.strip() for origin in extra.split(",") if origin.strip())
    return origins


app.add_middleware(
    CORSMiddleware,
    allow_origins=_allowed_frontend_origins(),
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
    allow_headers=["Authorization", "Content-Type"],
)


def identity(request: Request) -> Identity:
    """Use the synthetic adapter only in tests; otherwise validate Entra or Studio-issued Google session JWTs."""
    header = request.headers.get("authorization", "")
    if header.startswith("Bearer studio:") and os.getenv(GOOGLE_ENABLED_ENV, "false").lower() == "true":
        try:
            principal = validate_session_token(header.removeprefix("Bearer studio:"))
        except GoogleAuthError as exc:
            raise HTTPException(status_code=401, detail="Bearer token validation failed") from exc
        return Identity(principal.actor_id, principal.roles)
    if os.getenv("STUDIO_TEST_MODE", "false").lower() == "true":
        if os.getenv("STUDIO_ENV", "development").strip().lower() in {"staging", "production"}:
            raise HTTPException(status_code=503, detail="Synthetic authentication is disabled in deployed environments")
        if not header.startswith("Bearer test:"):
            raise HTTPException(status_code=401, detail="A workforce access token is required")
        parts = header.removeprefix("Bearer test:").split(":", 1)
        if len(parts) != 2 or not parts[0] or not parts[1]:
            raise HTTPException(status_code=401, detail="Malformed synthetic identity")
        roles = frozenset(role for role in parts[1].split(",") if role)
        return Identity(parts[0], roles)
    if os.getenv("STUDIO_ENTRA_ENABLED", "false").lower() != "true":
        raise HTTPException(status_code=503, detail="Microsoft Entra authentication is not configured")
    if not header and os.getenv("STUDIO_PLATFORM_AUTH") == "easy-auth":
        access_token = request.headers.get("x-ms-token-aad-access-token")
        if access_token:
            origin = os.getenv("STUDIO_PUBLIC_ORIGIN", "")
            if request.method not in {"GET", "HEAD", "OPTIONS"} and (
                not origin.startswith("https://") or request.headers.get("origin") != origin
            ):
                raise HTTPException(status_code=403, detail="A same-origin Studio session is required")
            header = "Bearer " + access_token
    if not header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="A workforce access token is required")
    try:
        principal = entra_validator().validate(header.removeprefix("Bearer ").strip())
    except (TokenValidationError, ValueError) as exc:
        raise HTTPException(status_code=401, detail="Bearer token validation failed") from exc
    return Identity(principal.actor_id, principal.roles)


@lru_cache(maxsize=1)
def entra_validator() -> EntraTokenValidator:
    settings = EntraSettings.from_environment()
    return EntraTokenValidator(settings, HttpJwksProvider(settings.jwks_url))


def postgres_mode() -> bool:
    return os.getenv("STUDIO_PERSISTENCE", "memory").lower() == "postgres"


@lru_cache(maxsize=1)
def postgres_repository() -> PostgresRepository:
    try:
        return PostgresRepository()
    except PersistenceConfigurationError as exc:
        raise HTTPException(status_code=503, detail="PostgreSQL persistence is not configured") from exc


def unsupported_memory_domain(operation: str) -> None:
    if postgres_mode():
        raise HTTPException(status_code=501, detail=f"PostgreSQL persistence for {operation} is not enabled yet")


@lru_cache(maxsize=1)
def stripe_billing_client() -> StripeBillingClient:
    try:
        return StripeBillingClient(StripeBillingSettings.from_environment())
    except StripeBillingError as exc:
        raise HTTPException(status_code=503, detail="Stripe billing is not configured") from exc


def require_billing_enabled() -> None:
    if os.getenv(BILLING_ENABLED_ENV, "false").lower() != "true":
        raise HTTPException(status_code=503, detail="Client billing is not switched on")


STRIPE_INVOICE_EVENT_STATUS = {
    "invoice.paid": "paid",
    "invoice.voided": "void",
    "invoice.marked_uncollectible": "uncollectible",
    "invoice.finalized": "open",
}


def organization_uuid(value: str) -> UUID:
    try:
        return UUID(value)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail="organization_id must be a UUID") from exc


def validate_synthetic_output(output: dict) -> None:
    if output.get("synthetic") is not True or output.get("type") != "work_breakdown":
        raise HTTPException(status_code=502, detail="AI executor returned an invalid artifact")
    if not isinstance(output.get("steps"), list) or not output["steps"]:
        raise HTTPException(status_code=502, detail="AI executor returned no validated steps")
    if not isinstance(output.get("source_specification"), str):
        raise HTTPException(status_code=502, detail="AI executor omitted source provenance")


def require_global(actor: Identity, *roles: str) -> None:
    if not actor.roles.intersection(roles):
        raise HTTPException(status_code=403, detail="The required internal role is missing")


def member(actor: Identity, organization_id: str, *roles: str) -> None:
    if "admin" in actor.roles:
        return
    assigned = store.memberships.get((actor.actor_id, organization_id), set())
    if not assigned.intersection(roles):
        raise HTTPException(status_code=403, detail="Organization access is not authorized")


def organization_for_engagement(engagement_id: str) -> str:
    engagement = store.engagements.get(engagement_id)
    if not engagement:
        raise HTTPException(status_code=404, detail="Engagement not found")
    return engagement["organization_id"]


def organization_for_project(project_id: str) -> str:
    project = store.projects.get(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return organization_for_engagement(project["engagement_id"])


def project_for_package(package_id: str) -> dict:
    package = store.work_packages.get(package_id)
    if not package:
        raise HTTPException(status_code=404, detail="Work package not found")
    project = store.projects.get(package["project_id"])
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


def revoke_assignments(professional_id: str, organization_id: str | None = None) -> None:
    for assignment in store.assignments.values():
        if assignment["professional_id"] != professional_id or assignment["status"] not in {"invited", "accepted"}:
            continue
        project = project_for_package(assignment["work_package_id"])
        if organization_id is None or organization_id == organization_for_engagement(project["engagement_id"]):
            assignment["status"] = "revoked"


def active_package_ids(actor: Identity) -> set[str]:
    if actor.actor_id not in store.approved_professionals:
        return set()
    result = set()
    for item in store.assignments.values():
        if item["professional_id"] != actor.actor_id or item["status"] != "accepted":
            continue
        if item["expires_at"] and datetime.fromisoformat(item["expires_at"]).timestamp() <= datetime.now(timezone.utc).timestamp():
            continue
        org = organization_for_engagement(project_for_package(item["work_package_id"])["engagement_id"])
        if "professional" in store.memberships.get((actor.actor_id, org), set()):
            result.add(item["work_package_id"])
    return result


def memory_project_access(actor: Identity, project_id: str) -> tuple[dict, str, set[str]]:
    """Resolve project scope and caller membership without trusting client input."""
    project = store.projects.get(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    organization_id = organization_for_engagement(project["engagement_id"])
    roles = store.memberships.get((actor.actor_id, organization_id), set())
    assigned = any(store.work_packages[key]["project_id"] == project_id for key in active_package_ids(actor))
    roles = roles - {"professional"}
    if "admin" not in actor.roles and not roles.intersection({"owner", "reviewer", "client"}) and not assigned:
        raise HTTPException(status_code=403, detail="Project access is not authorized")
    return project, organization_id, roles | ({"professional"} if assigned else set())


def memory_notification(project_id: str, recipient_group: str, kind: str, title: str, body: str) -> dict:
    record = {
        "id": str(uuid4()),
        "project_id": project_id,
        "recipient_group": recipient_group,
        "kind": kind,
        "title": title,
        "body": body,
        "read_at": None,
        "created_at": now(),
    }
    store.notifications[record["id"]] = record
    return record


class OrganizationCreate(BaseModel):
    name: str = Field(min_length=2, max_length=160)
    referral_code: str | None = Field(default=None, min_length=6, max_length=40)


class MemberGrant(BaseModel):
    actor_id: str = Field(min_length=2, max_length=120)
    role: Literal["client", "professional", "reviewer", "owner"]


class EngagementCreate(BaseModel):
    organization_id: str
    name: str = Field(min_length=2, max_length=160)
    objective: str = Field(min_length=2, max_length=4000)


class ProjectCreate(BaseModel):
    engagement_id: str
    name: str = Field(min_length=2, max_length=160)


class WorkPackageCreate(BaseModel):
    project_id: str
    title: str = Field(min_length=2, max_length=160)
    acceptance_criteria: list[str] = Field(min_length=1, max_length=20)
    depends_on: list[str] = Field(default_factory=list, max_length=20)


class AssignmentCreate(BaseModel):
    professional_id: str = Field(min_length=2, max_length=120)
    expires_at: datetime | None = None


class AIRunCreate(BaseModel):
    work_package_id: str
    specification: str = Field(min_length=10, max_length=4000)
    tools: list[Literal["planning"]] = Field(default_factory=lambda: ["planning"], max_length=1)
    budget_cents: int = Field(default=100, ge=1, le=1000)
    agent_id: str | None = None


class AgentCreate(BaseModel):
    name: str = Field(min_length=2, max_length=160)
    purpose: str = Field(min_length=2, max_length=2000)
    capability_category: Literal["planning", "research", "code_generation", "qa", "vetting", "analytics"]
    provider: str = Field(min_length=2, max_length=80)
    model: str = Field(min_length=1, max_length=120)
    model_version: str = Field(min_length=1, max_length=120)
    allowed_tools: list[Literal["planning"]] = Field(min_length=1, max_length=5)
    data_access_scope: Literal["none", "work_package", "organization"]
    autonomy_level: Literal["supervised", "bounded_autonomous"]
    requires_human_approval: bool = True
    budget_cap_cents: int = Field(ge=1, le=100000)
    owner_actor_id: str = Field(min_length=2, max_length=120)


class ReferralLinkCreate(BaseModel):
    partner_name: str = Field(min_length=2, max_length=160)


class GoogleSignIn(BaseModel):
    code: str = Field(min_length=1, max_length=4096)
    redirect_uri: str = Field(min_length=1, max_length=2048)


class AccountRoleAssignment(BaseModel):
    role: Literal["admin", "reviewer", "professional", "client"]


class SupportRequestCreate(BaseModel):
    subject: str = Field(min_length=2, max_length=200)
    body: str = Field(min_length=2, max_length=4000)


class InvoiceCreate(BaseModel):
    description: str = Field(min_length=2, max_length=500)
    amount_cents: int = Field(ge=100, le=100_000_000)
    currency: str = Field(min_length=3, max_length=3)
    # Only read the first time an organization is billed; later invoices reuse the Stripe
    # customer already on file and ignore these.
    billing_email: str | None = Field(default=None, min_length=3, max_length=320)
    billing_name: str | None = Field(default=None, min_length=2, max_length=160)


class DiagnosticLinkCreate(BaseModel):
    organization_id: str
    source_engagement_id: str = Field(min_length=2, max_length=160)


class DiagnosticHandoffWorkPackage(BaseModel):
    id: str = Field(min_length=1, max_length=160)
    intervention: str = Field(min_length=2, max_length=4000)
    outcome: str = Field(min_length=2, max_length=4000)
    acceptance: str = Field(min_length=2, max_length=4000)
    research_claim: dict | None = None


class DiagnosticHandoffCreate(BaseModel):
    idempotency_key: str = Field(min_length=8, max_length=160)
    schema_version: int
    engagement_id: str = Field(min_length=1, max_length=160)
    report_id: str = Field(min_length=1, max_length=160)
    report_version: int = Field(ge=1)
    problem: str = Field(min_length=2, max_length=4000)
    desired_outcome: str = Field(min_length=2, max_length=4000)
    work_packages: list[DiagnosticHandoffWorkPackage] = Field(min_length=1, max_length=50)


class Decision(BaseModel):
    decision: Literal["approved", "rejected"]
    comment: str = Field(default="", max_length=2000)


class DeliverableCreate(BaseModel):
    work_package_id: str
    title: str = Field(min_length=2, max_length=160)
    content: str = Field(min_length=2, max_length=12000)


class ReviewCreate(BaseModel):
    decision: Literal["approved", "revision_requested"]
    comment: str = Field(default="", max_length=2000)


class ClientRevisionCreate(BaseModel):
    comment: str = Field(min_length=2, max_length=2000)


class ProjectMessageCreate(BaseModel):
    body: str = Field(min_length=2, max_length=4000)
    recipient_group: Literal["client", "professional", "internal"]


class ProjectDocumentCreate(BaseModel):
    name: str = Field(min_length=2, max_length=200)
    description: str = Field(default="", max_length=2000)
    classification: Literal["project", "deliverable", "support"] = "project"
    storage_reference: str = Field(max_length=512, pattern=r"^(blob://private/|private://)[A-Za-z0-9_./-]+$")


class OpportunityCreate(BaseModel):
    title: str = Field(min_length=2, max_length=160)
    summary: str = Field(min_length=2, max_length=4000)
    specialization: str = Field(min_length=2, max_length=120)
    skills: list[str] = Field(default_factory=list, max_length=20)
    compensation: str | None = Field(default=None, max_length=240)
    deadline: datetime | None = None


class OpportunityInterestCreate(BaseModel):
    approach: str = Field(min_length=2, max_length=4000)


class ProfessionalProfileUpdate(BaseModel):
    display_name: str = Field(min_length=2, max_length=160)
    headline: str = Field(default="", max_length=240)
    bio: str = Field(default="", max_length=4000)
    skills: list[str] = Field(default_factory=list, max_length=30)
    specializations: list[str] = Field(default_factory=list, max_length=20)
    education: list[dict[str, str]] = Field(default_factory=list, max_length=10)
    experience: list[dict[str, str]] = Field(default_factory=list, max_length=15)
    portfolio: list[dict[str, str]] = Field(default_factory=list, max_length=20)
    evidence_references: list[dict[str, str]] = Field(default_factory=list, max_length=20)
    availability: str = Field(default="", max_length=120)
    expected_version: int | None = Field(default=None, ge=1)


class AdmissionReviewUpdate(BaseModel):
    verified_evidence_indices: list[int] = Field(default_factory=list, max_length=20)
    reviewed_profile_version: int | None = Field(default=None, ge=1)
    status: Literal["under_review", "assessment", "approved", "declined", "revoked"]
    reason: str = Field(default="", max_length=4000)
    missing_information: list[str] = Field(default_factory=list, max_length=20)
    assessment_requests: list[dict[str, str]] = Field(default_factory=list, max_length=10)
    next_action: str = Field(default="", max_length=1000)


def audit_response(actor: Identity, resource_type: str, resource_id: str, action: str, organization_id: str | None = None) -> None:
    store.event(actor, action, resource_type, resource_id, organization_id=organization_id)


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "mode": "synthetic" if os.getenv("STUDIO_TEST_MODE", "false").lower() == "true" else "entra-required"}


@app.get("/ready")
def ready() -> dict:
    """Fail closed when deployment configuration cannot safely accept traffic."""
    deployment_env = os.getenv("STUDIO_ENV", "development").strip().lower()
    test_mode = os.getenv("STUDIO_TEST_MODE", "false").lower() == "true"
    persistence = os.getenv("STUDIO_PERSISTENCE", "memory").strip().lower()
    checks = {
        "test_identity_disabled_for_staging": not (deployment_env in {"staging", "production"} and test_mode),
        "entra_configured": test_mode or (
            os.getenv("STUDIO_ENTRA_ENABLED", "false").lower() == "true"
            and bool(os.getenv("STUDIO_ENTRA_TENANT_ID", "").strip())
            and bool(os.getenv("STUDIO_ENTRA_AUDIENCE", "").strip())
            and bool(os.getenv("STUDIO_ENTRA_WEB_CLIENT_ID", "").strip())
        ),
        "postgres_configured": (test_mode and deployment_env not in {"staging", "production"})
        or (persistence == "postgres" and bool(os.getenv("STUDIO_DATABASE_URL", "").strip())),
    }
    if deployment_env in {"staging", "production"}:
        checks["schema_current"] = False
        if all(value for key, value in checks.items() if key != "schema_current"):
            try:
                checks["schema_current"] = postgres_repository().schema_current()
            except Exception:
                # Never include database host, connection details or driver errors in health output.
                pass
    if not all(checks.values()):
        raise HTTPException(status_code=503, detail={"status": "not_ready", "checks": checks})
    return {"status": "ready", "environment": deployment_env, "persistence": persistence, "checks": checks}


def _authentication_method(request: Request) -> str:
    if request.headers.get("authorization", "").startswith("Bearer studio:"):
        return "google"
    if os.getenv("STUDIO_TEST_MODE", "").lower() == "true":
        return "synthetic-test"
    return "entra"


@app.get("/api/me")
def me(request: Request) -> dict:
    actor = identity(request)
    result = {"id": actor.actor_id, "roles": sorted(actor.roles), "authentication": _authentication_method(request)}
    if "professional" in actor.roles:
        application = (postgres_repository().get_professional_application(actor.actor_id) if postgres_mode()
                       else store.professional_admissions.get(actor.actor_id))
        result["admission_status"] = application["status"] if application else None
    return result


@app.post("/api/auth/google")
def google_sign_in(body: GoogleSignIn) -> dict:
    """Verify a Google authorization code and return a Studio session.

    A new account is created with no global_role (pending): the response's
    `pending` flag tells the client to show the "waiting for an admin"
    screen instead of a workspace, since every route still 403s an empty
    role set regardless of what this endpoint returns.
    """
    if os.getenv(GOOGLE_ENABLED_ENV, "false").lower() != "true":
        raise HTTPException(status_code=503, detail="Google sign-in is not configured")
    if not postgres_mode():
        raise HTTPException(status_code=501, detail="Google sign-in requires PostgreSQL persistence")
    try:
        settings = GoogleOAuthSettings.from_environment()
        identity_claim = GoogleOAuthClient(settings).exchange(body.code, body.redirect_uri)
    except GoogleAuthError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc
    account = postgres_repository().upsert_google_account(identity_claim.email, identity_claim.name, identity_claim.picture)
    try:
        token = issue_session_token(account["id"], account["email"], account["global_role"])
    except GoogleAuthError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    return {
        "access_token": token,
        "actor_id": account["id"],
        "email": account["email"],
        "name": account["name"],
        "role": account["global_role"],
        "pending": account["global_role"] is None,
    }


@app.get("/api/accounts")
def list_accounts(request: Request, role: str | None = Query(default=None)) -> list[dict]:
    """List Studio accounts created through Google sign-in. Admin only."""
    actor = identity(request)
    require_global(actor, "admin")
    if not postgres_mode():
        raise HTTPException(status_code=501, detail="Accounts require PostgreSQL persistence")
    if role is not None and role not in {"pending", "admin", "reviewer", "professional", "client"}:
        raise HTTPException(status_code=422, detail="Unknown role filter")
    return postgres_repository().list_accounts(role)


@app.post("/api/accounts/{account_id}/role")
def assign_account_role(account_id: str, body: AccountRoleAssignment, request: Request) -> dict:
    """Grant a Studio-owned account its first (or a new) global role. Admin only."""
    actor = identity(request)
    require_global(actor, "admin")
    if not postgres_mode():
        raise HTTPException(status_code=501, detail="Accounts require PostgreSQL persistence")
    try:
        account_uuid = UUID(account_id)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail="account_id must be a UUID") from exc
    try:
        return postgres_repository().set_account_role(actor.actor_id, account_uuid, body.role)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail="Account not found") from exc


@app.post("/api/organizations", status_code=status.HTTP_201_CREATED)
def create_organization(body: OrganizationCreate, request: Request) -> dict:
    actor = identity(request)
    require_global(actor, "admin")
    if postgres_mode():
        repo = postgres_repository()
        organization_id = repo.create_organization(body.name, actor.actor_id)
        if body.referral_code:
            repo.record_referral_signup(body.referral_code, organization_id)
        return {"id": str(organization_id), "name": body.name, "created_at": now()}
    organization_id = str(uuid4())
    store.organizations[organization_id] = {"id": organization_id, "name": body.name, "created_at": now()}
    store.memberships[(actor.actor_id, organization_id)] = {"owner"}
    audit_response(actor, "organization", organization_id, "organization.created", organization_id)
    return store.organizations[organization_id]


@app.get("/api/organizations")
def list_organizations(request: Request) -> list[dict]:
    actor = identity(request)
    if postgres_mode():
        return postgres_repository().list_organizations(actor.actor_id, admin="admin" in actor.roles)
    if "admin" in actor.roles:
        return list(store.organizations.values())
    visible = []
    for organization_id, organization in store.organizations.items():
        if store.memberships.get((actor.actor_id, organization_id), set()):
            visible.append(organization)
    return visible


@app.post("/api/organizations/{organization_id}/members", status_code=status.HTTP_201_CREATED)
def grant_member(organization_id: str, body: MemberGrant, request: Request) -> dict:
    actor = identity(request)
    if postgres_mode():
        try:
            postgres_repository().grant_membership(organization_uuid(organization_id), body.actor_id, body.role, actor.actor_id)
        except PermissionError as exc:
            raise HTTPException(403, str(exc)) from exc
        return {"actor_id": body.actor_id, "organization_id": organization_id, "role": body.role}
    if organization_id not in store.organizations:
        raise HTTPException(status_code=404, detail="Organization not found")
    member(actor, organization_id, "owner")
    roles = store.memberships.setdefault((body.actor_id, organization_id), set())
    if body.role == "professional" and "professional" not in roles:
        revoke_assignments(body.actor_id, organization_id)
    roles.add(body.role)
    audit_response(actor, "organization_membership", f"{body.actor_id}:{organization_id}", "membership.granted", organization_id)
    return {"actor_id": body.actor_id, "organization_id": organization_id, "role": body.role}


@app.get("/api/organizations/{organization_id}/members")
def list_members(organization_id: str, request: Request) -> list[dict]:
    actor = identity(request)
    if postgres_mode():
        try:
            return postgres_repository().list_memberships(organization_uuid(organization_id), actor.actor_id, admin="admin" in actor.roles)
        except PermissionError as exc:
            raise HTTPException(status_code=403, detail=str(exc)) from exc
    if organization_id not in store.organizations:
        raise HTTPException(status_code=404, detail="Organization not found")
    if "admin" not in actor.roles and "owner" not in store.memberships.get((actor.actor_id, organization_id), set()):
        raise HTTPException(status_code=403, detail="Only an organization owner may view the membership roster")
    return [
        {"actor_id": member_id, "role": role}
        for (member_id, org_id), roles in store.memberships.items()
        if org_id == organization_id
        for role in sorted(roles)
    ]


@app.delete("/api/organizations/{organization_id}/members/{member_id}/{role}")
def revoke_member(organization_id: str, member_id: str, role: Literal["client", "professional", "reviewer", "owner"], request: Request) -> dict:
    actor = identity(request)
    if postgres_mode():
        try:
            postgres_repository().revoke_membership(organization_uuid(organization_id), member_id, role, actor.actor_id)
        except ValueError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
        except LookupError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        return {"actor_id": member_id, "organization_id": organization_id, "role": role, "status": "revoked"}
    if organization_id not in store.organizations:
        raise HTTPException(status_code=404, detail="Organization not found")
    member(actor, organization_id, "owner")
    assigned = store.memberships.get((member_id, organization_id), set())
    if role not in assigned:
        raise HTTPException(status_code=404, detail="Membership role not found")
    if role == "owner" and sum("owner" in roles for (candidate, org), roles in store.memberships.items() if org == organization_id and candidate != member_id) == 0:
        raise HTTPException(status_code=409, detail="The final organization owner cannot be revoked")
    if role == "professional":
        revoke_assignments(member_id, organization_id)
    assigned.remove(role)
    if not assigned:
        store.memberships.pop((member_id, organization_id), None)
    audit_response(actor, "organization_membership", f"{member_id}:{organization_id}", "membership.revoked", organization_id)
    return {"actor_id": member_id, "organization_id": organization_id, "role": role, "status": "revoked"}


@app.post("/api/organizations/{organization_id}/invoices", status_code=status.HTTP_201_CREATED)
def create_invoice(organization_id: str, body: InvoiceCreate, request: Request) -> dict:
    """Prepare a draft invoice. Nothing is emailed or visible to the client yet --
    that only happens on the separate, explicit "send" action below."""
    actor = identity(request)
    require_global(actor, "admin")
    require_billing_enabled()
    if not postgres_mode():
        raise HTTPException(status_code=501, detail="Billing requires PostgreSQL persistence")
    if body.currency != body.currency.lower() or not body.currency.isalpha():
        raise HTTPException(status_code=422, detail="currency must be a lower-case 3-letter code, e.g. 'usd'")
    org_id = organization_uuid(organization_id)
    repo = postgres_repository()
    client = stripe_billing_client()
    existing = repo.get_billing_customer(org_id)
    if existing is None:
        if not body.billing_email or not body.billing_name:
            raise HTTPException(status_code=422, detail="billing_email and billing_name are required to bill this organization for the first time")
        try:
            created = client.create_customer(body.billing_email, body.billing_name)
        except StripeBillingError as exc:
            raise HTTPException(status_code=502, detail=str(exc)) from exc
        repo.create_billing_customer(org_id, created["id"], body.billing_email)
        stripe_customer_id = created["id"]
    else:
        stripe_customer_id = existing["stripe_customer_id"]
    try:
        draft = client.create_invoice(stripe_customer_id, body.currency)
        client.add_invoice_item(stripe_customer_id, draft["id"], body.amount_cents, body.currency, body.description)
    except StripeBillingError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    return repo.create_invoice(org_id, draft["id"], stripe_customer_id, body.description, body.amount_cents, body.currency, actor.actor_id)


@app.get("/api/organizations/{organization_id}/invoices")
def list_invoices(organization_id: str, request: Request) -> list[dict]:
    actor = identity(request)
    if not postgres_mode():
        raise HTTPException(status_code=501, detail="Billing requires PostgreSQL persistence")
    try:
        return postgres_repository().list_invoices(organization_uuid(organization_id), actor.actor_id, admin="admin" in actor.roles)
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc


@app.get("/api/invoices/{invoice_id}")
def get_invoice(invoice_id: UUID, request: Request) -> dict:
    actor = identity(request)
    if not postgres_mode():
        raise HTTPException(status_code=501, detail="Billing requires PostgreSQL persistence")
    try:
        return postgres_repository().get_invoice_for_actor(invoice_id, actor.actor_id, admin="admin" in actor.roles)
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.post("/api/invoices/{invoice_id}/send")
def send_invoice(invoice_id: UUID, request: Request) -> dict:
    """The one action that actually emails the client: finalize then send, in one press."""
    actor = identity(request)
    require_global(actor, "admin")
    require_billing_enabled()
    if not postgres_mode():
        raise HTTPException(status_code=501, detail="Billing requires PostgreSQL persistence")
    repo = postgres_repository()
    try:
        record = repo.get_invoice_for_actor(invoice_id, actor.actor_id, admin=True)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    if record["status"] != "draft":
        raise HTTPException(status_code=409, detail="Only a draft invoice can be sent")
    client = stripe_billing_client()
    try:
        client.finalize_invoice(record["stripe_invoice_id"])
        sent = client.send_invoice(record["stripe_invoice_id"])
    except StripeBillingError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    return repo.mark_invoice_sent(invoice_id, sent.get("hosted_invoice_url") or "", sent.get("status") or "open", actor.actor_id)


@app.post("/api/invoices/{invoice_id}/void")
def void_invoice(invoice_id: UUID, request: Request) -> dict:
    actor = identity(request)
    require_global(actor, "admin")
    if not postgres_mode():
        raise HTTPException(status_code=501, detail="Billing requires PostgreSQL persistence")
    repo = postgres_repository()
    try:
        record = repo.get_invoice_for_actor(invoice_id, actor.actor_id, admin=True)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    if record["status"] == "draft":
        try:
            stripe_billing_client().delete_draft_invoice(record["stripe_invoice_id"])
        except StripeBillingError as exc:
            raise HTTPException(status_code=502, detail=str(exc)) from exc
        repo.delete_draft_invoice(invoice_id, actor.actor_id)
        return {"id": str(invoice_id), "status": "discarded"}
    try:
        stripe_billing_client().void_invoice(record["stripe_invoice_id"])
    except StripeBillingError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    try:
        return repo.void_invoice(invoice_id, actor.actor_id)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@app.post("/api/stripe/webhook")
async def stripe_webhook(request: Request) -> dict:
    """Verified by Stripe's own signature, never by anything the caller claims.
    Idempotent: a redelivered event id is acknowledged without being re-applied."""
    if not postgres_mode():
        raise HTTPException(status_code=501, detail="Billing requires PostgreSQL persistence")
    webhook_secret = os.getenv("STRIPE_WEBHOOK_SECRET", "").strip()
    if not webhook_secret:
        raise HTTPException(status_code=503, detail="Stripe webhook secret is not configured")
    payload = await request.body()
    try:
        event = verify_webhook_signature(payload, request.headers.get("stripe-signature", ""), webhook_secret)
    except StripeBillingError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    event_id = event.get("id")
    event_type = event.get("type")
    if not isinstance(event_id, str) or not event_id:
        raise HTTPException(status_code=400, detail="Stripe event is missing an id")
    repo = postgres_repository()
    if not repo.record_webhook_event(event_id, event_type if isinstance(event_type, str) else "unknown"):
        return {"received": True, "deduplicated": True}
    target_status = STRIPE_INVOICE_EVENT_STATUS.get(event_type) if isinstance(event_type, str) else None
    if target_status:
        stripe_invoice_id = (event.get("data") or {}).get("object", {}).get("id")
        if isinstance(stripe_invoice_id, str) and stripe_invoice_id:
            repo.update_invoice_status_by_stripe_id(stripe_invoice_id, target_status)
    return {"received": True}


@app.post("/api/organizations/{organization_id}/support-requests", status_code=status.HTTP_201_CREATED)
def create_support_request(organization_id: str, body: SupportRequestCreate, request: Request) -> dict:
    actor = identity(request)
    if not postgres_mode():
        raise HTTPException(status_code=501, detail="Support requests require PostgreSQL persistence")
    try:
        return postgres_repository().create_support_request(organization_uuid(organization_id), actor.actor_id, body.subject, body.body)
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc


@app.get("/api/organizations/{organization_id}/support-requests")
def list_organization_support_requests(organization_id: str, request: Request) -> list[dict]:
    actor = identity(request)
    if not postgres_mode():
        raise HTTPException(status_code=501, detail="Support requests require PostgreSQL persistence")
    try:
        return postgres_repository().list_support_requests(actor.actor_id, "admin" in actor.roles, organization_uuid(organization_id))
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc


@app.get("/api/support-requests")
def list_all_support_requests(request: Request, status_filter: Literal["open", "resolved"] | None = None) -> list[dict]:
    actor = identity(request)
    require_global(actor, "admin")
    if not postgres_mode():
        raise HTTPException(status_code=501, detail="Support requests require PostgreSQL persistence")
    return postgres_repository().list_support_requests(actor.actor_id, True, status_filter=status_filter)


@app.post("/api/support-requests/{request_id}/resolve")
def resolve_support_request(request_id: UUID, request: Request) -> dict:
    actor = identity(request)
    require_global(actor, "admin")
    if not postgres_mode():
        raise HTTPException(status_code=501, detail="Support requests require PostgreSQL persistence")
    try:
        return postgres_repository().resolve_support_request(request_id, actor.actor_id)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@app.post("/api/professionals/{professional_id}/application", status_code=status.HTTP_201_CREATED)
def submit_professional_application(professional_id: str, request: Request) -> dict:
    actor = identity(request)
    require_global(actor, "professional", "admin")
    if actor.actor_id != professional_id and "admin" not in actor.roles:
        raise HTTPException(status_code=403, detail="A professional may submit only their own application")
    if postgres_mode():
        try:
            postgres_repository().submit_professional_application(professional_id, actor.actor_id)
        except ValueError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
        return {"professional_id": professional_id, "status": "submitted"}
    existing = store.professional_admissions.get(professional_id)
    if existing:
        if existing["status"] == "submitted":
            return {"professional_id": professional_id, "status": "submitted"}
        raise HTTPException(status_code=409, detail="An application already exists. Update the current profile or contact admission staff.")
    store.professional_admissions[professional_id] = {
        "professional_id": professional_id,
        "status": "submitted",
        "decided_by": None,
        "decided_at": None,
        "submitted_at": now(),
        "reviewed_at": None,
        "decision_reason": "",
        "missing_information": [],
        "assessment_requests": [],
        "evidence_references": [],
        "next_action": "Awaiting admission review",
        "created_at": now(),
    }
    store.event(actor, "professional.application_submitted", "professional", professional_id)
    return {"professional_id": professional_id, "status": "submitted"}


@app.get("/api/professionals/{professional_id}/application")
def get_professional_application(professional_id: str, request: Request) -> dict:
    actor = identity(request)
    if actor.actor_id != professional_id and not actor.roles.intersection({"admin", "reviewer"}):
        raise HTTPException(status_code=403, detail="Application access is not authorized")
    if postgres_mode():
        record = postgres_repository().get_professional_application(professional_id)
    else:
        record = store.professional_admissions.get(professional_id)
    if not record:
        raise HTTPException(status_code=404, detail="Professional application not found")
    return record


def _profile_access(actor: Identity, professional_id: str) -> None:
    """Profiles are private to the professional and authorized admission staff."""
    if actor.actor_id == professional_id and "professional" in actor.roles:
        return
    if actor.roles.intersection({"admin", "reviewer"}):
        return
    raise HTTPException(status_code=403, detail="Professional profile access is not authorized")


@app.get("/api/professionals/{professional_id}/profile")
def get_professional_profile(professional_id: str, request: Request) -> dict:
    actor = identity(request)
    _profile_access(actor, professional_id)
    if postgres_mode():
        try:
            record = postgres_repository().get_professional_profile(professional_id)
        except LookupError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
    else:
        if professional_id not in store.professional_admissions:
            raise HTTPException(status_code=404, detail="Professional application not found")
        record = store.professional_profiles.get(professional_id)
    if not record:
        raise HTTPException(status_code=404, detail="Professional profile has not been started")
    if not postgres_mode():
        record = {**record, "application_status": store.professional_admissions[professional_id]["status"]}
    history = (postgres_repository().admission_history(professional_id) if postgres_mode() else
               [event["metadata"] for event in store.audit if event["resource_type"] == "professional_admission"
                and event["resource_id"] == professional_id])
    return {**record, "evidence_references": evidence_status(record, history)}


@app.put("/api/professionals/{professional_id}/profile")
def update_professional_profile(professional_id: str, body: ProfessionalProfileUpdate, request: Request) -> dict:
    actor = identity(request)
    if actor.actor_id != professional_id or "professional" not in actor.roles:
        raise HTTPException(403, "Only the applicant can edit their profile")
    payload = body.model_dump(exclude_none=True)
    for evidence in payload.get("evidence_references", []):
        evidence["status"] = "unverified"
        reference = evidence.get("reference", "").strip()
        if reference and not reference.startswith(("private://", "quarantine://", "pending://")):
            raise HTTPException(status_code=422, detail="Evidence references must use private, quarantine, or pending storage schemes")
        if any(key not in {"label", "reference", "classification", "status"} for key in evidence):
            raise HTTPException(status_code=422, detail="Evidence references contain unsupported metadata")
    expected_version = payload.pop("expected_version", None)
    if postgres_mode():
        try:
            return postgres_repository().upsert_professional_profile(professional_id, payload, actor.actor_id, expected_version)
        except LookupError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except ValueError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
    if professional_id not in store.professional_admissions:
        raise HTTPException(status_code=409, detail="Submit a professional application before editing a profile")
    existing = store.professional_profiles.get(professional_id)
    current_version = existing.get("version", 0) if existing else 0
    if expected_version is not None and expected_version != current_version:
        raise HTTPException(status_code=409, detail="Profile changed since it was loaded; refresh before saving")
    profile = {
        **payload,
        "professional_id": professional_id,
        "version": current_version + 1,
        "updated_at": now(),
        "application_status": store.professional_admissions[professional_id]["status"],
    }
    store.professional_profiles[professional_id] = profile
    audit_response(actor, "professional_profile", professional_id, "professional_profile.updated")
    return profile


@app.get("/api/professionals/{professional_id}/admission-history")
def admission_history(professional_id: str, request: Request) -> list[dict]:
    actor = identity(request)
    require_global(actor, "admin", "reviewer")
    if postgres_mode():
        return postgres_repository().admission_history(professional_id)
    return [{"action": item["action"], "reviewer": item["actor_id"], "created_at": item["created_at"], **item["metadata"]}
            for item in reversed(store.audit) if item["resource_id"] == professional_id
            and item["resource_type"] in {"professional", "professional_admission"}]


@app.get("/api/professionals/admissions")
def list_professional_admissions(
    request: Request,
    status_filter: Literal["draft", "submitted", "under_review", "assessment", "pending", "approved", "declined", "rejected", "revoked"] | None = None,
) -> list[dict]:
    actor = identity(request)
    require_global(actor, "admin", "reviewer")
    if postgres_mode():
        return postgres_repository().list_professional_admissions(status_filter)
    records = [{**record, "display_name": store.professional_profiles.get(record["professional_id"], {}).get("display_name")}
               for record in store.professional_admissions.values()]
    if status_filter:
        records = [record for record in records if record["status"] == status_filter]
    return sorted(records, key=lambda record: (record["created_at"], record["professional_id"]))


@app.post("/api/professionals/{professional_id}/review")
def review_professional_admission(professional_id: str, body: AdmissionReviewUpdate, request: Request) -> dict:
    actor = identity(request)
    require_global(actor, "admin", "reviewer")
    if professional_id == actor.actor_id:
        raise HTTPException(status_code=409, detail="An independent reviewer must make the admission decision")
    for reference in body.assessment_requests:
        if not reference.get("title", "").strip():
            raise HTTPException(status_code=422, detail="Assessment requests require a title")
    if body.status in {"approved", "declined", "revoked"} and not body.reason.strip():
        raise HTTPException(status_code=422, detail="A decision reason is required for terminal admission decisions")
    if postgres_mode():
        try:
            return postgres_repository().review_professional_admission(
                professional_id, body.model_dump(exclude_none=True), actor.actor_id
            )
        except ValueError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
        except LookupError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
    record = store.professional_admissions.get(professional_id)
    if not record:
        raise HTTPException(status_code=404, detail="Professional application not found")
    verified_evidence = []
    previous_status = record["status"]
    if body.status == "approved":
        try:
            verified_evidence = check_approval(record, store.professional_profiles.get(professional_id),
                           body.model_dump(), professional_id, actor.actor_id)
        except ValueError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
    record = {
        **record,
        "status": body.status,
        "decided_by": actor.actor_id if body.status in {"approved", "declined", "revoked"} else record.get("decided_by"),
        "decided_at": now() if body.status in {"approved", "declined", "revoked"} else record.get("decided_at"),
        "reviewed_at": now(),
        "decision_reason": body.reason,
        "missing_information": body.missing_information,
        "assessment_requests": body.assessment_requests,
        "next_action": body.next_action,
    }
    store.professional_admissions[professional_id] = record
    if body.status == "approved":
        revoke_assignments(professional_id)
        store.approved_professionals.add(professional_id)
    else:
        store.approved_professionals.discard(professional_id)
        revoke_assignments(professional_id)
    store.event(actor, f"professional.admission_{body.status}", "professional_admission", professional_id,
                {"verified_evidence": verified_evidence, "policy_version": QUALIFICATION_POLICY_VERSION, "previous_status": previous_status, "reason": body.reason, "reviewed_profile_version": body.reviewed_profile_version})
    return record


@app.post("/api/professionals/{professional_id}/decision")
@app.post("/api/professionals/{professional_id}/approve")
def retired_admission_decision(professional_id: str, request: Request) -> None:
    require_global(identity(request), "admin")
    raise HTTPException(status_code=410, detail="Record a reasoned decision in the application review workspace")


@app.post("/api/engagements", status_code=status.HTTP_201_CREATED)
def create_engagement(body: EngagementCreate, request: Request) -> dict:
    actor = identity(request)
    require_global(actor, "admin")
    if postgres_mode():
        engagement_id = postgres_repository().create_engagement(organization_uuid(body.organization_id), body.name, body.objective, actor.actor_id)
        return {"id": str(engagement_id), "organization_id": body.organization_id, "name": body.name, "objective": body.objective, "status": "authorized", "created_at": now()}
    if body.organization_id not in store.organizations:
        raise HTTPException(status_code=404, detail="Organization not found")
    engagement_id = str(uuid4())
    store.engagements[engagement_id] = {
        "id": engagement_id,
        "organization_id": body.organization_id,
        "name": body.name,
        "objective": body.objective,
        "status": "authorized",
        "created_at": now(),
    }
    audit_response(actor, "engagement", engagement_id, "engagement.created", body.organization_id)
    return store.engagements[engagement_id]


@app.get("/api/engagements")
def list_engagements(request: Request) -> list[dict]:
    actor = identity(request)
    if postgres_mode():
        return postgres_repository().list_engagements(actor.actor_id, admin="admin" in actor.roles)
    if "admin" in actor.roles:
        return list(store.engagements.values())
    visible = []
    scoped = {project_for_package(key)["engagement_id"] for key in active_package_ids(actor)}
    for engagement in store.engagements.values():
        if engagement["id"] in scoped or store.memberships.get((actor.actor_id, engagement["organization_id"]), set()).intersection({"client", "reviewer", "owner"}):
            visible.append(engagement)
    return visible


@app.get("/api/admin/overview")
def admin_overview(request: Request) -> dict:
    """Return admin-only operational summaries from authorized records."""
    actor = identity(request)
    require_global(actor, "admin")
    if postgres_mode():
        return postgres_repository().admin_overview(actor.actor_id)

    projects = []
    for project in store.projects.values():
        engagement = store.engagements.get(project["engagement_id"], {})
        organization = store.organizations.get(engagement.get("organization_id"), {})
        packages = [item for item in store.work_packages.values() if item["project_id"] == project["id"]]
        package_ids = {item["id"] for item in packages}
        deliverables = [item for item in store.deliverables.values() if item["work_package_id"] in package_ids]
        projects.append({
            **project,
            "engagement_name": engagement.get("name"),
            "organization_name": organization.get("name"),
            "work_package_count": len(packages),
            "deliverable_count": len(deliverables),
            "awaiting_review": sum(item["status"] == "under_review" for item in deliverables),
        })
    applications = [{**item, "display_name": store.professional_profiles.get(item["professional_id"], {}).get("display_name")}
                    for item in store.professional_admissions.values()]
    open_opportunities = [item for item in store.opportunities.values() if item["status"] == "published"]
    active_assignments = [item for item in store.assignments.values() if item["status"] == "accepted"]
    pending_reviews = [item for item in store.deliverables.values() if item["status"] == "under_review"]
    pending_ai = [item for item in store.artifacts.values() if item["status"] == "pending_review"]
    failed_ai = [item for item in store.ai_runs.values() if item["status"] == "failed"]
    return {
        "organizations": list(store.organizations.values()),
        "engagements": list(store.engagements.values()),
        "projects": projects,
        "applications": applications,
        "professionals": applications,
        "opportunities": open_opportunities,
        "opportunity_interests": list(store.opportunity_interests.values()),
        "deliverables": list(store.deliverables.values()),
        "ai_runs": [{**item, "artifact_status": store.artifacts.get(item.get("artifact_id"), {}).get("status")} for item in store.ai_runs.values()],
        "audit": list(reversed(store.audit[-25:])),
        "metrics": {
            "active_engagements": sum(item["status"] in {"authorized", "active"} for item in store.engagements.values()),
            "projects_awaiting_kickoff": sum(item["status"] == "active" and not any(package["project_id"] == item["id"] for package in store.work_packages.values()) for item in store.projects.values()),
            "active_projects": sum(item["status"] == "active" for item in store.projects.values()),
            "awaiting_review": len(pending_reviews),
            "client_approvals_pending": sum(item["status"] == "approved" for item in store.deliverables.values()),
            "pending_applications": sum(item["status"] in {"pending", "submitted", "under_review", "assessment"} for item in applications),
            "open_opportunities": len(open_opportunities),
            "active_assignments": len(active_assignments),
            "ai_pending_approval": len(pending_ai),
            "ai_failed": len(failed_ai),
        },
    }


def _memory_client_overview(actor: Identity) -> dict:
    """Return only records belonging to organizations where the actor is a client."""
    organization_ids = {
        organization_id
        for (member_id, organization_id), roles in store.memberships.items()
        if member_id == actor.actor_id and "client" in roles
    }
    if not organization_ids:
        raise HTTPException(status_code=403, detail="An active client membership is required")
    organizations = [item for item in store.organizations.values() if item["id"] in organization_ids]
    engagements = [item for item in store.engagements.values() if item["organization_id"] in organization_ids]
    engagement_ids = {item["id"] for item in engagements}
    projects = []
    deliverables = []
    for project in store.projects.values():
        engagement = store.engagements.get(project["engagement_id"])
        if not engagement or engagement["id"] not in engagement_ids:
            continue
        packages = []
        for package in store.work_packages.values():
            if package["project_id"] != project["id"]:
                continue
            versions = [item for item in store.deliverables.values() if item["work_package_id"] == package["id"] and item["status"] in {"approved", "accepted"}]
            safe_versions = [{key: value for key, value in item.items() if key != "submitted_by"} for item in sorted(versions, key=lambda item: item["version"])]
            deliverables.extend(safe_versions)
            packages.append({**package, "deliverables": safe_versions})
        projects.append({**project, "engagement_name": engagement["name"], "organization_name": store.organizations.get(engagement["organization_id"], {}).get("name"), "work_packages": packages})
    return {
        "organizations": organizations,
        "engagements": engagements,
        "projects": projects,
        "deliverables": deliverables,
        "metrics": {
            "active_projects": sum(item["status"] == "active" for item in projects),
            "completed_projects": sum(item["status"] == "completed" for item in projects),
            "deliverables_for_review": sum(item["status"] == "approved" for item in deliverables),
            "accepted_deliverables": sum(item["status"] == "accepted" for item in deliverables),
        },
    }


@app.get("/api/client/overview")
def client_overview(request: Request) -> dict:
    actor = identity(request)
    if postgres_mode():
        try:
            return postgres_repository().client_overview(actor.actor_id)
        except PermissionError as exc:
            raise HTTPException(status_code=403, detail=str(exc)) from exc
    return _memory_client_overview(actor)


class ProjectRequestInput(BaseModel):
    subject: str = Field(min_length=2, max_length=500, pattern=r"\S.*\S")


class RequestDecision(BaseModel):
    decision: Literal["approved", "declined"]
    rationale: str = Field(min_length=2, max_length=1000, pattern=r"\S.*\S")


@app.get("/api/projects/{project_id}/coordination")
def project_coordination(project_id: UUID, request: Request) -> dict:
    actor = identity(request)
    if postgres_mode():
        try:
            return postgres_repository().project_coordination(project_id, actor.actor_id, "admin" in actor.roles)
        except PermissionError as exc:
            raise HTTPException(403, str(exc)) from exc
        except LookupError as exc:
            raise HTTPException(404, str(exc)) from exc
    key = str(project_id)
    _, _, roles = memory_project_access(actor, key)
    if "admin" not in actor.roles and not roles.intersection({"owner", "client"}):
        raise HTTPException(403, "Client project coordination access is required")
    return {"requests": [row for row in reversed(store.project_requests.values()) if row["project_id"] == key],
            "handover": store.handovers.get(key)}


@app.post("/api/projects/{project_id}/requests", status_code=201)
def open_project_request(project_id: UUID, body: ProjectRequestInput, request: Request) -> dict:
    actor = identity(request)
    require_global(actor, "client")
    if postgres_mode():
        try:
            return postgres_repository().open_project_request(project_id, actor.actor_id, body.subject.strip())
        except PermissionError as exc:
            raise HTTPException(403, str(exc)) from exc
        except LookupError as exc:
            raise HTTPException(404, str(exc)) from exc
    key = str(project_id)
    _, org, roles = memory_project_access(actor, key)
    if "client" not in roles:
        raise HTTPException(403, "Client membership is required")
    row = {"id": str(uuid4()), "project_id": key, "subject": body.subject.strip(), "created_at": now(),
           "decision": None, "rationale": None, "decided_at": None}
    store.project_requests[row["id"]] = row
    memory_notification(key, "internal", "project.request.opened", "Client request", "A client request needs a decision.")
    audit_response(actor, "project_request", row["id"], "project.request.opened", org)
    return {"id": row["id"]}


@app.post("/api/projects/{project_id}/requests/{request_id}/decision")
def decide_project_request(project_id: UUID, request_id: UUID, body: RequestDecision, request: Request) -> dict:
    actor = identity(request)
    require_global(actor, "admin")
    if postgres_mode():
        try:
            return postgres_repository().decide_project_request(project_id, request_id, actor.actor_id, body.decision, body.rationale.strip())
        except LookupError as exc:
            raise HTTPException(404, str(exc)) from exc
        except ValueError as exc:
            raise HTTPException(409, str(exc)) from exc
    _, org, _ = memory_project_access(actor, str(project_id))
    with _deliverable_lock:
        row = store.project_requests.get(str(request_id))
        if not row or row["project_id"] != str(project_id):
            raise HTTPException(404, "Project request not found")
        if row["decision"]:
            raise HTTPException(409, "A decision has already been recorded")
        row.update(decision=body.decision, rationale=body.rationale.strip(), decided_at=now())
        memory_notification(str(project_id), "client", "project.request.decided", "Request decision", "Data Fellows responded to a request.")
        audit_response(actor, "project_request", row["id"], "project.request.decided", org)
        return {"id": row["id"], "decision": body.decision}


@app.get("/api/projects/{project_id}/messages")
def list_project_messages(project_id: str, request: Request) -> list[dict]:
    actor = identity(request)
    if postgres_mode():
        try:
            project_uuid = UUID(project_id)
            return postgres_repository().list_project_messages(project_uuid, actor.actor_id, admin="admin" in actor.roles)
        except ValueError as exc:
            raise HTTPException(status_code=422, detail="project_id must be a UUID") from exc
        except PermissionError as exc:
            raise HTTPException(status_code=403, detail=str(exc)) from exc
        except LookupError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
    _project, _organization_id, roles = memory_project_access(actor, project_id)
    internal = "admin" in actor.roles or roles.intersection({"owner", "reviewer"})
    allowed_groups = set()
    if "client" in roles:
        allowed_groups.add("client")
    if "professional" in roles:
        allowed_groups.add("professional")
    if not roles.intersection({"client", "professional"}):
        allowed_groups = {"client", "professional", "internal"}
    return [
        item for item in sorted(store.project_messages.values(), key=lambda value: value["created_at"])
        if item["project_id"] == project_id
        and (internal or item["sender_id"] == actor.actor_id or item["recipient_group"] in allowed_groups)
    ]


@app.post("/api/projects/{project_id}/messages", status_code=status.HTTP_201_CREATED)
def send_project_message(project_id: str, body: ProjectMessageCreate, request: Request) -> dict:
    actor = identity(request)
    if postgres_mode():
        try:
            project_uuid = UUID(project_id)
            return postgres_repository().send_project_message(project_uuid, actor.actor_id, body.body, body.recipient_group, admin="admin" in actor.roles)
        except ValueError as exc:
            raise HTTPException(status_code=422, detail="project_id must be a UUID") from exc
        except PermissionError as exc:
            raise HTTPException(status_code=403, detail=str(exc)) from exc
        except LookupError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
    _project, organization_id, roles = memory_project_access(actor, project_id)
    if "admin" not in actor.roles and roles.intersection({"client", "professional"}) and body.recipient_group != "internal":
        raise HTTPException(status_code=403, detail="Clients and professionals may only message Data Fellows internally")
    message = {
        "id": str(uuid4()),
        "project_id": project_id,
        "sender_id": actor.actor_id,
        "recipient_group": body.recipient_group,
        "body": body.body,
        "created_at": now(),
    }
    store.project_messages[message["id"]] = message
    memory_notification(project_id, body.recipient_group, "project.message", "New project message", "A new message is available in the project workspace.")
    audit_response(actor, "project_message", message["id"], "project.message.sent", organization_id,)
    return message


@app.get("/api/projects/{project_id}/documents")
def list_project_documents(project_id: str, request: Request) -> list[dict]:
    actor = identity(request)
    if postgres_mode():
        try:
            project_uuid = UUID(project_id)
            return postgres_repository().list_project_documents(project_uuid, actor.actor_id, admin="admin" in actor.roles)
        except ValueError as exc:
            raise HTTPException(status_code=422, detail="project_id must be a UUID") from exc
        except PermissionError as exc:
            raise HTTPException(status_code=403, detail=str(exc)) from exc
        except LookupError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
    _project, _organization_id, roles = memory_project_access(actor, project_id)
    return [
        {key: value for key, value in item.items() if key != "storage_reference"}
        for item in sorted(store.project_documents.values(), key=lambda value: value["created_at"])
        if item["project_id"] == project_id and ("admin" in actor.roles or not roles.intersection({"client", "professional"}) or item["classification"] != "support")
    ]


@app.post("/api/projects/{project_id}/documents", status_code=status.HTTP_201_CREATED)
def create_project_document(project_id: str, body: ProjectDocumentCreate, request: Request) -> dict:
    actor = identity(request)
    if postgres_mode():
        try:
            project_uuid = UUID(project_id)
            return postgres_repository().create_project_document(project_uuid, actor.actor_id, body.model_dump(), admin="admin" in actor.roles)
        except ValueError as exc:
            raise HTTPException(status_code=422, detail="project_id must be a UUID") from exc
        except PermissionError as exc:
            raise HTTPException(status_code=403, detail=str(exc)) from exc
        except LookupError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
    _project, organization_id, roles = memory_project_access(actor, project_id)
    if "admin" not in actor.roles and not roles.intersection({"owner"}):
        raise HTTPException(status_code=403, detail="Only a Data Fellows owner may add project documents")
    document = {"id": str(uuid4()), "project_id": project_id, **body.model_dump(), "created_by": actor.actor_id, "created_at": now()}
    store.project_documents[document["id"]] = document
    audit_response(actor, "project_document", document["id"], "project.document.added", organization_id)
    return {key: value for key, value in document.items() if key != "storage_reference"}


@app.get("/api/projects/{project_id}/activity")
def project_activity(project_id: str, request: Request) -> list[dict]:
    actor = identity(request)
    if postgres_mode():
        try:
            project_uuid = UUID(project_id)
            return postgres_repository().project_activity(project_uuid, actor.actor_id, admin="admin" in actor.roles)
        except ValueError as exc:
            raise HTTPException(status_code=422, detail="project_id must be a UUID") from exc
        except PermissionError as exc:
            raise HTTPException(status_code=403, detail=str(exc)) from exc
        except LookupError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
    _project, _organization_id, roles = memory_project_access(actor, project_id)
    if "admin" not in actor.roles and not roles.intersection({"owner", "reviewer"}):
        return [{"action": event["action"], "created_at": event["created_at"]} for event in reversed(store.audit)
                if event["resource_type"] == "project" and event["resource_id"] == project_id
                and event["action"] in {"project.created", "project.completed"}]
    related_ids = {project_id}
    package_ids = {item["id"] for item in store.work_packages.values() if item["project_id"] == project_id}
    related_ids.update(package_ids)
    related_ids.update(item["id"] for item in store.assignments.values() if item["work_package_id"] in package_ids)
    related_ids.update(item["id"] for item in store.deliverables.values() if item["work_package_id"] in package_ids)
    related_ids.update(item["id"] for item in store.ai_runs.values() if item["work_package_id"] in package_ids)
    related_ids.update(item["id"] for item in store.project_messages.values() if item["project_id"] == project_id)
    related_ids.update(item["id"] for item in store.project_documents.values() if item["project_id"] == project_id)
    events = [item for item in store.audit if item["resource_id"] in related_ids]
    if "client" in roles or "professional" in roles:
        events = [item for item in events if item["resource_type"] not in {"ai_run", "ai_artifact"}]
    return list(reversed(events))


@app.get("/api/notifications")
def notifications(request: Request) -> list[dict]:
    actor = identity(request)
    if postgres_mode():
        return postgres_repository().list_notifications(actor.actor_id, admin="admin" in actor.roles)
    results = []
    for item in store.notifications.values():
        if not item["project_id"]:
            continue
        try:
            _project, _organization_id, roles = memory_project_access(actor, item["project_id"])
        except HTTPException:
            continue
        internal = "admin" in actor.roles or roles.intersection({"owner", "reviewer"})
        if internal or item["recipient_group"] in roles:
            results.append(item)
    return sorted(results, key=lambda value: value["created_at"], reverse=True)


@app.get("/api/engagements/{engagement_id}/projects")
def list_projects(engagement_id: str, request: Request) -> list[dict]:
    actor = identity(request)
    if postgres_mode():
        try:
            return postgres_repository().list_projects(UUID(engagement_id), actor.actor_id, admin="admin" in actor.roles)
        except PermissionError as exc:
            raise HTTPException(status_code=403, detail=str(exc)) from exc
        except LookupError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except ValueError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
    engagement = store.engagements.get(engagement_id)
    if not engagement:
        raise HTTPException(status_code=404, detail="Engagement not found")
    if "admin" not in actor.roles:
        organization_id = engagement["organization_id"]
        roles = store.memberships.get((actor.actor_id, organization_id), set())
        if not roles.intersection({"owner", "reviewer", "client"}):
            project_ids = {store.work_packages[key]["project_id"] for key in active_package_ids(actor)}
            visible = [p for p in store.projects.values() if p["engagement_id"] == engagement_id and p["id"] in project_ids]
            if not visible:
                raise HTTPException(status_code=403, detail="Project access is not authorized")
            return visible
    return [project for project in store.projects.values() if project["engagement_id"] == engagement_id]


@app.post("/api/projects", status_code=status.HTTP_201_CREATED)
def create_project(body: ProjectCreate, request: Request) -> dict:
    actor = identity(request)
    if postgres_mode():
        try:
            project_id = postgres_repository().create_project(UUID(body.engagement_id), body.name, actor.actor_id)
        except LookupError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        return {"id": str(project_id), "engagement_id": body.engagement_id, "name": body.name, "status": "active", "created_at": now()}
    unsupported_memory_domain("projects")
    org_id = organization_for_engagement(body.engagement_id)
    member(actor, org_id, "owner")
    project_id = str(uuid4())
    store.projects[project_id] = {
        "id": project_id,
        "engagement_id": body.engagement_id,
        "name": body.name,
        "status": "active",
        "created_at": now(),
    }
    audit_response(actor, "project", project_id, "project.created", org_id)
    return store.projects[project_id]


@app.post("/api/work-packages", status_code=status.HTTP_201_CREATED)
def create_work_package(body: WorkPackageCreate, request: Request) -> dict:
    actor = identity(request)
    if postgres_mode():
        try:
            package_id = postgres_repository().create_work_package(
                UUID(body.project_id),
                body.title,
                body.acceptance_criteria,
                [UUID(value) for value in body.depends_on],
                actor.actor_id,
            )
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        except LookupError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        return {"id": str(package_id), "project_id": body.project_id, "title": body.title, "acceptance_criteria": body.acceptance_criteria, "dependencies": body.depends_on, "status": "unassigned"}
    unsupported_memory_domain("work packages")
    project = store.projects.get(body.project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    org_id = organization_for_engagement(project["engagement_id"])
    member(actor, org_id, "owner")
    if len(set(body.depends_on)) != len(body.depends_on) or body.project_id in body.depends_on:
        raise HTTPException(status_code=422, detail="Dependencies must be unique and cannot reference the package itself")
    for dependency_id in body.depends_on:
        dependency = store.work_packages.get(dependency_id)
        if not dependency or dependency["project_id"] != body.project_id:
            raise HTTPException(status_code=422, detail="Dependencies must be existing work packages in the same project")
    package_id = str(uuid4())
    store.work_packages[package_id] = {
        "id": package_id,
        "project_id": body.project_id,
        "title": body.title,
        "acceptance_criteria": body.acceptance_criteria,
        "status": "unassigned",
        "depends_on": list(body.depends_on),
    }
    audit_response(actor, "work_package", package_id, "work_package.created", org_id)
    return store.work_packages[package_id]


@app.get("/api/projects/{project_id}/work-packages")
def list_work_packages(project_id: str, request: Request) -> list[dict]:
    actor = identity(request)
    if postgres_mode():
        try:
            return postgres_repository().list_work_packages(UUID(project_id), actor.actor_id, admin="admin" in actor.roles)
        except PermissionError as exc:
            raise HTTPException(status_code=403, detail=str(exc)) from exc
        except LookupError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
    project = store.projects.get(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    organization_id = organization_for_engagement(project["engagement_id"])
    roles = store.memberships.get((actor.actor_id, organization_id), set())
    if "admin" not in actor.roles and not roles.intersection({"owner", "reviewer", "client"}):
        visible = [store.work_packages[k] for k in active_package_ids(actor) if store.work_packages[k]["project_id"] == project_id]
        if not visible:
            raise HTTPException(status_code=403, detail="Work package access is not authorized")
        return visible
    return [item for item in store.work_packages.values() if item["project_id"] == project_id]


@app.post("/api/work-packages/{package_id}/assignments", status_code=status.HTTP_201_CREATED)
def assign_work(package_id: str, body: AssignmentCreate, request: Request) -> dict:
    actor = identity(request)
    if postgres_mode():
        try:
            assignment_id = postgres_repository().assign_work(UUID(package_id), body.professional_id, body.expires_at, actor.actor_id)
        except ValueError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
        except PermissionError as exc:
            raise HTTPException(status_code=403, detail=str(exc)) from exc
        except LookupError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        return {"id": str(assignment_id), "work_package_id": package_id, "professional_id": body.professional_id, "status": "invited", "expires_at": body.expires_at.isoformat() if body.expires_at else None}
    unsupported_memory_domain("assignments")
    project = project_for_package(package_id)
    org_id = organization_for_engagement(project["engagement_id"])
    member(actor, org_id, "owner")
    if body.professional_id not in store.approved_professionals:
        raise HTTPException(status_code=409, detail="Professional approval is required before assignment")
    if "professional" not in store.memberships.get((body.professional_id, org_id), set()):
        raise HTTPException(status_code=403, detail="Professional is not admitted to this organization")
    assignment_id = str(uuid4())
    store.assignments[assignment_id] = {"id": assignment_id, "work_package_id": package_id, "professional_id": body.professional_id, "status": "invited", "expires_at": body.expires_at.isoformat() if body.expires_at else None}
    store.work_packages[package_id]["status"] = "assigned"
    audit_response(actor, "assignment", assignment_id, "assignment.invited", org_id)
    return store.assignments[assignment_id]


@app.post("/api/assignments/{assignment_id}/accept")
def accept_assignment(assignment_id: str, request: Request) -> dict:
    actor = identity(request)
    if postgres_mode():
        try:
            postgres_repository().accept_assignment(UUID(assignment_id), actor.actor_id)
        except ValueError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
        except LookupError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        return {"id": assignment_id, "professional_id": actor.actor_id, "status": "accepted"}
    assignment = store.assignments.get(assignment_id)
    if not assignment:
        raise HTTPException(status_code=404, detail="Assignment not found")
    if assignment["professional_id"] != actor.actor_id:
        raise HTTPException(status_code=403, detail="Only the invited professional may accept")
    if assignment["status"] != "invited":
        raise HTTPException(status_code=409, detail="Assignment invitation is no longer active")
    if assignment["expires_at"] and datetime.fromisoformat(assignment["expires_at"]) <= datetime.now(timezone.utc):
        assignment["status"] = "expired"
        raise HTTPException(status_code=409, detail="Assignment invitation has expired")
    project = project_for_package(assignment["work_package_id"])
    org = organization_for_engagement(project["engagement_id"])
    if actor.actor_id not in store.approved_professionals or "professional" not in store.memberships.get((actor.actor_id, org), set()):
        raise HTTPException(status_code=409, detail="Assignment access is no longer active")
    assignment["status"] = "accepted"
    audit_response(actor, "assignment", assignment_id, "assignment.accepted", organization_for_engagement(project["engagement_id"]))
    return assignment


@app.post("/api/assignments/{assignment_id}/decline")
def decline_assignment(assignment_id: str, request: Request) -> dict:
    actor = identity(request)
    if postgres_mode():
        try:
            postgres_repository().decline_assignment(UUID(assignment_id), actor.actor_id)
        except PermissionError as exc:
            raise HTTPException(status_code=403, detail=str(exc)) from exc
        except LookupError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except ValueError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
        return {"id": assignment_id, "status": "declined"}
    assignment = store.assignments.get(assignment_id)
    if not assignment:
        raise HTTPException(status_code=404, detail="Assignment not found")
    if assignment["professional_id"] != actor.actor_id:
        raise HTTPException(status_code=403, detail="Only the invited professional may decline")
    if assignment["status"] != "invited":
        raise HTTPException(status_code=409, detail="Only an active invitation can be declined")
    assignment["status"] = "declined"
    project = project_for_package(assignment["work_package_id"])
    audit_response(actor, "assignment", assignment_id, "assignment.declined", organization_for_engagement(project["engagement_id"]))
    return assignment


@app.get("/api/professionals/{professional_id}/assignments")
def list_assignments(professional_id: str, request: Request) -> list[dict]:
    actor = identity(request)
    if postgres_mode():
        try:
            return postgres_repository().list_assignments(professional_id, actor.actor_id, admin="admin" in actor.roles)
        except PermissionError as exc:
            raise HTTPException(status_code=403, detail=str(exc)) from exc
    if actor.actor_id != professional_id and "admin" not in actor.roles:
        raise HTTPException(status_code=403, detail="Assignment access is not authorized")
    result = []
    for item in store.assignments.values():
        if item["professional_id"] != professional_id:
            continue
        package = store.work_packages.get(item["work_package_id"], {})
        if "admin" not in actor.roles:
            org = organization_for_engagement(store.projects[package["project_id"]]["engagement_id"])
            if (professional_id not in store.approved_professionals or item["status"] not in {"accepted", "invited"}
                    or "professional" not in store.memberships.get((professional_id, org), set())
                    or (item["expires_at"] and datetime.fromisoformat(item["expires_at"]).timestamp() <= datetime.now(timezone.utc).timestamp())):
                continue
        project = store.projects.get(package.get("project_id"), {})
        engagement = store.engagements.get(project.get("engagement_id"), {})
        result.append({**item, "title": package.get("title"), "project_id": project.get("id"), "project_name": project.get("name"), "engagement_name": engagement.get("name"), "objective": engagement.get("objective")})
    return result


@app.post("/api/opportunities", status_code=status.HTTP_201_CREATED)
def create_opportunity(body: OpportunityCreate, request: Request) -> dict:
    actor = identity(request)
    require_global(actor, "admin")
    if postgres_mode():
        opportunity_id = postgres_repository().create_opportunity(body.title, body.summary, body.specialization, body.skills, body.compensation, body.deadline, actor.actor_id)
        return {"id": str(opportunity_id), **body.model_dump(), "status": "published", "created_by": actor.actor_id}
    opportunity_id = str(uuid4())
    store.opportunities[opportunity_id] = {"id": opportunity_id, **body.model_dump(), "status": "published", "created_by": actor.actor_id, "created_at": now()}
    audit_response(actor, "opportunity", opportunity_id, "opportunity.published")
    return store.opportunities[opportunity_id]


@app.get("/api/opportunities")
def list_opportunities(request: Request) -> list[dict]:
    actor = identity(request)
    if "admin" not in actor.roles and "professional" not in actor.roles:
        raise HTTPException(status_code=403, detail="Only approved professionals may view opportunities")
    if postgres_mode():
        try:
            return postgres_repository().list_opportunities(actor.actor_id, admin="admin" in actor.roles)
        except PermissionError as exc:
            raise HTTPException(status_code=403, detail=str(exc)) from exc
    if "admin" not in actor.roles and actor.actor_id not in store.approved_professionals:
        raise HTTPException(status_code=403, detail="Professional approval is required to view opportunities")
    results = []
    for opportunity in store.opportunities.values():
        if opportunity["status"] != "published":
            continue
        interest = next((item for item in store.opportunity_interests.values() if item["opportunity_id"] == opportunity["id"] and item["professional_id"] == actor.actor_id), None)
        results.append({**opportunity, "interest_id": interest and interest["id"], "interest_status": interest and interest["status"]})
    return sorted(results, key=lambda item: item["created_at"], reverse=True)


@app.post("/api/opportunities/{opportunity_id}/interests", status_code=status.HTTP_201_CREATED)
def express_opportunity_interest(opportunity_id: str, body: OpportunityInterestCreate, request: Request) -> dict:
    actor = identity(request)
    require_global(actor, "professional")
    if postgres_mode():
        try:
            interest_id = postgres_repository().express_interest(UUID(opportunity_id), actor.actor_id, body.approach)
            return {"id": str(interest_id), "opportunity_id": opportunity_id, "professional_id": actor.actor_id, "approach": body.approach, "status": "interested"}
        except PermissionError as exc:
            raise HTTPException(status_code=403, detail=str(exc)) from exc
        except LookupError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
    if actor.actor_id not in store.approved_professionals:
        raise HTTPException(status_code=403, detail="Professional approval is required to express interest")
    if opportunity_id not in store.opportunities or store.opportunities[opportunity_id]["status"] != "published":
        raise HTTPException(status_code=404, detail="Opportunity not found")
    interest_id = str(uuid4())
    record = {"id": interest_id, "opportunity_id": opportunity_id, "professional_id": actor.actor_id, "approach": body.approach, "status": "interested", "created_at": now()}
    store.opportunity_interests[interest_id] = record
    return record


@app.get("/api/opportunities/interests")
def list_opportunity_interests(request: Request) -> list[dict]:
    actor = identity(request)
    require_global(actor, "admin")
    if postgres_mode():
        return postgres_repository().list_opportunity_interests(actor.actor_id)
    return list(store.opportunity_interests.values())


@app.post("/api/opportunity-interests/{interest_id}/{decision}")
def decide_opportunity_interest(interest_id: str, decision: Literal["selected", "withdrawn"], request: Request) -> dict:
    actor = identity(request)
    require_global(actor, "admin")
    if postgres_mode():
        try:
            return postgres_repository().decide_opportunity_interest(UUID(interest_id), decision)
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        except LookupError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
    record = store.opportunity_interests.get(interest_id)
    if not record:
        raise HTTPException(status_code=404, detail="Opportunity interest not found")
    record["status"] = decision
    audit_response(actor, "opportunity_interest", interest_id, f"opportunity_interest.{decision}")
    return record


@app.post("/api/ai-agents", status_code=status.HTTP_201_CREATED)
def register_agent(body: AgentCreate, request: Request) -> dict:
    actor = identity(request)
    require_global(actor, "admin")
    if not postgres_mode():
        raise HTTPException(status_code=501, detail="The AI agent registry requires PostgreSQL persistence")
    return postgres_repository().create_agent(actor.actor_id, body.model_dump())


@app.get("/api/ai-agents")
def list_agents(request: Request) -> list[dict]:
    actor = identity(request)
    require_global(actor, "admin", "reviewer")
    if not postgres_mode():
        raise HTTPException(status_code=501, detail="The AI agent registry requires PostgreSQL persistence")
    return postgres_repository().list_agents()


def _resolve_run_agent(repo: PostgresRepository, agent_id: str | None) -> dict:
    lookup_id = UUID(agent_id) if agent_id else SYNTHETIC_AGENT_ID
    agent = repo.get_agent(lookup_id)
    if agent is None:
        raise HTTPException(status_code=404, detail="AI agent not found")
    if agent["status"] != "active":
        raise HTTPException(status_code=409, detail="AI agent is not active")
    return agent


@app.post("/api/ai-runs", status_code=status.HTTP_201_CREATED)
def create_ai_run(body: AIRunCreate, request: Request) -> dict:
    actor = identity(request)
    if postgres_mode():
        repo = postgres_repository()
        agent = _resolve_run_agent(repo, body.agent_id)
        if not set(body.tools).issubset(set(agent["allowed_tools"])):
            raise HTTPException(status_code=422, detail="Requested tool is not permitted for this agent")
        if body.budget_cents > agent["budget_cap_cents"]:
            raise HTTPException(status_code=422, detail="Requested budget exceeds the agent's approved budget cap")
        try:
            adapter = model_gateway.resolve_adapter(agent["provider"])
            result = adapter.run(body.specification, body.tools)
        except model_gateway.ModelGatewayError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
        validate_synthetic_output(result.output)
        try:
            run_id, artifact_id, _ = repo.create_ai_run(
                UUID(body.work_package_id), actor.actor_id, body.specification, body.budget_cents, result.output,
                agent_id=UUID(agent["id"]), agent_version=agent["name"],
                provider=result.provider, model=result.model, model_version=result.model_version,
            )
        except PermissionError as exc:
            raise HTTPException(status_code=403, detail=str(exc)) from exc
        except LookupError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        return {
            "id": str(run_id), "work_package_id": body.work_package_id, "requested_by": actor.actor_id,
            "status": "succeeded", "budget_cents": body.budget_cents, "spent_cents": 0,
            "agent": agent["name"], "agent_id": agent["id"], "provider": result.provider,
            "model": result.model, "model_version": result.model_version,
            "artifact_id": str(artifact_id),
            "artifact": {"id": str(artifact_id), "run_id": str(run_id), "status": "pending_review", "content": result.output},
        }
    unsupported_memory_domain("AI runs")
    project = project_for_package(body.work_package_id)
    org_id = organization_for_engagement(project["engagement_id"])
    member(actor, org_id, "owner")
    if body.tools != ["planning"]:
        raise HTTPException(status_code=422, detail="Only the bounded planning tool is enabled")
    run_id = str(uuid4())
    artifact_id = str(uuid4())
    output = {
        "type": "work_breakdown",
        "synthetic": True,
        "steps": [
            {"order": 1, "title": "Clarify approved requirements", "requires_approval": True},
            {"order": 2, "title": "Prepare implementation checklist", "requires_approval": True},
            {"order": 3, "title": "Review acceptance criteria", "requires_approval": True},
        ],
        "source_specification": body.specification,
    }
    store.ai_runs[run_id] = {
        "id": run_id,
        "work_package_id": body.work_package_id,
        "requested_by": actor.actor_id,
        "status": "succeeded",
        "budget_cents": body.budget_cents,
        "spent_cents": 0,
        "agent": "synthetic-planner-v1",
        "artifact_id": artifact_id,
        "created_at": now(),
    }
    store.artifacts[artifact_id] = {"id": artifact_id, "run_id": run_id, "status": "pending_review", "content": output}
    audit_response(actor, "ai_run", run_id, "ai_run.completed", org_id)
    return {**store.ai_runs[run_id], "artifact": store.artifacts[artifact_id]}


@app.post("/api/ai-runs/{run_id}/cancel")
def cancel_ai_run(run_id: str, request: Request) -> dict:
    actor = identity(request)
    if postgres_mode():
        try:
            postgres_repository().cancel_ai_run(UUID(run_id), actor.actor_id)
        except PermissionError as exc:
            raise HTTPException(status_code=403, detail=str(exc)) from exc
        except LookupError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except ValueError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
        return {"id": run_id, "status": "cancelled"}
    unsupported_memory_domain("AI run cancellation")


@app.get("/api/ai-runs/{run_id}")
def get_ai_run(run_id: str, request: Request) -> dict:
    actor = identity(request)
    if postgres_mode():
        try:
            return postgres_repository().get_ai_run(UUID(run_id), actor.actor_id, admin="admin" in actor.roles)
        except PermissionError as exc:
            raise HTTPException(status_code=403, detail=str(exc)) from exc
        except LookupError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
    run = store.ai_runs.get(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="AI run not found")
    project = project_for_package(run["work_package_id"])
    organization_id = organization_for_engagement(project["engagement_id"])
    if "admin" not in actor.roles and not store.memberships.get((actor.actor_id, organization_id), set()).intersection({"owner", "reviewer"}):
        raise HTTPException(status_code=403, detail="AI run access is not authorized")
    return {**run, "artifact": store.artifacts.get(run["artifact_id"])}


@app.post("/api/ai-runs/{run_id}/decision")
def decide_ai_run(run_id: str, body: Decision, request: Request) -> dict:
    actor = identity(request)
    if postgres_mode():
        require_global(actor, "admin", "reviewer")
        try:
            return postgres_repository().decide_ai_artifact(UUID(run_id), actor.actor_id, body.decision, body.comment, admin="admin" in actor.roles)
        except PermissionError as exc:
            raise HTTPException(status_code=403, detail=str(exc)) from exc
        except LookupError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except ValueError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
    unsupported_memory_domain("AI artifacts")
    run = store.ai_runs.get(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="AI run not found")
    if actor.actor_id == run["requested_by"]:
        raise HTTPException(status_code=409, detail="Independent approval is required")
    require_global(actor, "admin", "reviewer")
    project = project_for_package(run["work_package_id"])
    member(actor, organization_for_engagement(project["engagement_id"]), "reviewer", "owner")
    artifact = store.artifacts[run["artifact_id"]]
    artifact["status"] = body.decision
    artifact["decision_by"] = actor.actor_id
    artifact["decision_comment"] = body.comment
    audit_response(actor, "ai_artifact", artifact["id"], f"ai_artifact.{body.decision}", organization_for_engagement(project["engagement_id"]))
    return artifact


@app.post("/api/referral-links", status_code=status.HTTP_201_CREATED)
def create_referral_link(body: ReferralLinkCreate, request: Request) -> dict:
    """Create a trackable referral link for an onboarded partner (e.g. an accelerator)."""
    actor = identity(request)
    require_global(actor, "admin")
    if not postgres_mode():
        raise HTTPException(status_code=501, detail="Referral links require PostgreSQL persistence")
    return postgres_repository().create_referral_link(body.partner_name, actor.actor_id)


@app.get("/api/referral-links")
def list_referral_links(request: Request) -> list[dict]:
    actor = identity(request)
    require_global(actor, "admin")
    if not postgres_mode():
        raise HTTPException(status_code=501, detail="Referral links require PostgreSQL persistence")
    return postgres_repository().list_referral_links()


@app.post("/api/referral-links/{code}/visit", status_code=status.HTTP_204_NO_CONTENT)
def record_referral_visit(code: str) -> None:
    """Record a visit through a shared referral link. Unauthenticated: this is hit from a public landing page."""
    if not postgres_mode():
        raise HTTPException(status_code=501, detail="Referral links require PostgreSQL persistence")
    try:
        postgres_repository().record_referral_visit(code)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.get("/api/referral/{view_token}/stats")
def referral_stats(view_token: str) -> dict:
    """Let a partner see their own link's performance using the token they were given, without a Studio account."""
    if not postgres_mode():
        raise HTTPException(status_code=501, detail="Referral links require PostgreSQL persistence")
    stats = postgres_repository().get_referral_stats_by_token(view_token)
    if stats is None:
        raise HTTPException(status_code=404, detail="Referral link not found")
    return stats


@app.post("/api/diagnostic-links", status_code=status.HTTP_201_CREATED)
def create_diagnostic_link(body: DiagnosticLinkCreate, request: Request) -> dict:
    """Authorize one external BizPilot engagement to deliver handoffs into one Studio organization.

    This is a deliberate, owner-initiated step (an owning admin links the
    engagement) that must happen before any handoff for it is accepted. It
    never happens automatically from a handoff payload.
    """
    actor = identity(request)
    require_global(actor, "admin")
    if not postgres_mode():
        raise HTTPException(status_code=501, detail="Diagnostic links require PostgreSQL persistence")
    try:
        return postgres_repository().create_diagnostic_link(UUID(body.organization_id), "bizpilot", body.source_engagement_id, actor.actor_id)
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@app.post("/api/diagnostic-handoffs", status_code=status.HTTP_201_CREATED)
def receive_diagnostic_handoff(body: DiagnosticHandoffCreate, request: Request) -> dict:
    """Receive one BizPilot diagnostic handoff and create its authorized Studio shell.

    Creates an engagement, a project, and one work package per approved
    recommendation -- status 'authorized'/'unassigned', for Studio staff to
    plan and staff through the existing assignment and AI-run workflows.
    Never auto-assigns a professional or starts an AI run. Idempotent on
    (link, idempotency_key): a repeated delivery returns the same records.
    """
    actor = identity(request)
    require_global(actor, "admin", "diagnostics_service")
    if not postgres_mode():
        raise HTTPException(status_code=501, detail="Diagnostic handoffs require PostgreSQL persistence")
    if body.schema_version != 1:
        raise HTTPException(status_code=422, detail="Unsupported diagnostic handoff schema version")
    repo = postgres_repository()
    link = repo.get_diagnostic_link("bizpilot", body.engagement_id)
    if link is None:
        raise HTTPException(status_code=404, detail="No authorized Studio link exists for this diagnostic engagement")
    existing = repo.get_diagnostic_handoff(UUID(link["id"]), body.idempotency_key)
    if existing is not None:
        return {**existing, "idempotent": True}
    try:
        engagement_id = repo.create_engagement(UUID(link["organization_id"]), f"BizPilot diagnostic {body.report_id[:40]}", body.desired_outcome, link["linked_by"])
        project_id = repo.create_project(engagement_id, body.problem[:160], link["linked_by"])
        work_packages = []
        for item in body.work_packages:
            evidence_references = (item.research_claim or {}).get("sources", [])
            work_package_id = repo.create_work_package(project_id, item.intervention[:160], [item.acceptance], [], link["linked_by"])
            work_packages.append({"id": str(work_package_id), "source_recommendation_id": item.id, "evidence_references": evidence_references})
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    record = repo.record_diagnostic_handoff(UUID(link["id"]), body.idempotency_key, body.report_id, body.report_version, engagement_id, project_id, work_packages, actor.actor_id)
    return {**record, "idempotent": False}


@app.post("/api/deliverables", status_code=status.HTTP_201_CREATED)
def submit_deliverable(body: DeliverableCreate, request: Request) -> dict:
    actor = identity(request)
    if postgres_mode():
        try:
            return postgres_repository().submit_deliverable(UUID(body.work_package_id), body.title, body.content, actor.actor_id)
        except PermissionError as exc:
            raise HTTPException(status_code=403, detail=str(exc)) from exc
        except LookupError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except ValueError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
    unsupported_memory_domain("deliverables")
    project = project_for_package(body.work_package_id)
    org_id = organization_for_engagement(project["engagement_id"])
    allowed = store.memberships.get((actor.actor_id, org_id), set())
    current_time = datetime.now(timezone.utc).timestamp()
    assigned = "professional" in allowed and actor.actor_id in store.approved_professionals and any(
        a["work_package_id"] == body.work_package_id and a["professional_id"] == actor.actor_id
        and a["status"] == "accepted" and (not a["expires_at"] or datetime.fromisoformat(a["expires_at"]).timestamp() > current_time)
        for a in store.assignments.values()
    )
    if "owner" not in allowed and not assigned:
        raise HTTPException(status_code=403, detail="Only an assigned delivery resource may submit")
    with _deliverable_lock:
        existing = [d for d in store.deliverables.values() if d["work_package_id"] == body.work_package_id]
        if existing and existing[-1]["status"] in {"under_review", "approved", "accepted"}:
            raise HTTPException(status_code=409, detail="A new version requires a revision request on the latest deliverable")
        deliverable_id = str(uuid4())
        record = {
            "id": deliverable_id,
            "work_package_id": body.work_package_id,
            "title": body.title,
            "content": body.content,
            "version": len(existing) + 1,
            "submitted_by": actor.actor_id,
            "status": "under_review",
        }
        store.deliverables[deliverable_id] = record
        audit_response(actor, "deliverable", deliverable_id, "deliverable.submitted", org_id)
        return record


@app.get("/api/work-packages/{package_id}/deliverables")
def list_deliverables(package_id: str, request: Request) -> list[dict]:
    actor = identity(request)
    if postgres_mode():
        try:
            return postgres_repository().list_deliverables(UUID(package_id), actor.actor_id, admin="admin" in actor.roles)
        except PermissionError as exc:
            raise HTTPException(status_code=403, detail=str(exc)) from exc
        except LookupError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
    project = project_for_package(package_id)
    organization_id = organization_for_engagement(project["engagement_id"])
    roles = store.memberships.get((actor.actor_id, organization_id), set())
    if "admin" not in actor.roles and not roles.intersection({"owner", "reviewer", "client"}) and package_id not in active_package_ids(actor):
        raise HTTPException(status_code=403, detail="Deliverable access is not authorized")
    deliverables = [item for item in store.deliverables.values() if item["work_package_id"] == package_id]
    if "client" in roles and "owner" not in roles and "reviewer" not in roles:
        deliverables = [item for item in deliverables if item["status"] in {"approved", "accepted"}]
    return sorted(deliverables, key=lambda item: item["version"])


@app.get("/api/reviewer/queue")
def reviewer_queue(request: Request, offset: int = Query(default=0, ge=0)) -> dict:
    actor = identity(request)
    require_global(actor, "reviewer", "admin")
    page_size = 20
    if postgres_mode():
        rows = postgres_repository().reviewer_queue(actor.actor_id, offset, page_size + 1)
    else:
        rows = []
        for item in store.deliverables.values():
            if item["status"] != "under_review" or item["submitted_by"] == actor.actor_id:
                continue
            package = store.work_packages[item["work_package_id"]]
            project = store.projects[package["project_id"]]
            org = organization_for_engagement(project["engagement_id"])
            if not store.memberships.get((actor.actor_id, org), set()).intersection({"owner", "reviewer"}):
                continue
            rows.append({**item, "project_name": project["name"], "package_title": package["title"],
                         "acceptance_criteria": package["acceptance_criteria"]})
        rows.sort(key=lambda row: (row.get("created_at", ""), row["id"]))
        rows = rows[offset:offset + page_size + 1]
        for row in rows[:page_size]:
            prior = {v["id"]: v["version"] for v in store.deliverables.values()
                     if v["work_package_id"] == row["work_package_id"] and v["version"] < row["version"]}
            row["previous_reviews"] = sorted(
                ({"version": prior[r["deliverable_id"]], "decision": r["decision"], "comment": r["comment"]}
                 for r in store.reviews.values() if r["deliverable_id"] in prior),
                key=lambda review: review["version"], reverse=True)[:5]
    fields = ("id", "title", "version", "content", "project_name", "package_title", "acceptance_criteria", "previous_reviews")
    return {"items": [{key: row[key] for key in fields} for row in rows[:page_size]], "has_more": len(rows) > page_size}




@app.post("/api/deliverables/{deliverable_id}/review")
def review_deliverable(deliverable_id: str, body: ReviewCreate, request: Request) -> dict:
    actor = identity(request)
    require_global(actor, "admin", "reviewer")
    if not body.comment.strip():
        raise HTTPException(status_code=422, detail="Enter a review comment")
    if postgres_mode():
        try:
            return postgres_repository().review_deliverable(UUID(deliverable_id), actor.actor_id, body.decision, body.comment)
        except PermissionError as exc:
            raise HTTPException(status_code=403, detail=str(exc)) from exc
        except LookupError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except ValueError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
    unsupported_memory_domain("deliverable reviews")
    deliverable = store.deliverables.get(deliverable_id)
    if not deliverable:
        raise HTTPException(status_code=404, detail="Deliverable not found")
    if actor.actor_id == deliverable["submitted_by"]:
        raise HTTPException(status_code=409, detail="Independent review is required")
    project = project_for_package(deliverable["work_package_id"])
    org = organization_for_engagement(project["engagement_id"])
    if not store.memberships.get((actor.actor_id, org), set()).intersection({"reviewer", "owner"}):
        raise HTTPException(status_code=403, detail="Reviewer is not authorized for this organization")
    with _deliverable_lock:
        if deliverable["status"] != "under_review":
            raise HTTPException(status_code=409, detail="This version has already received a decision")
        deliverable["status"] = body.decision
        review_id = str(uuid4())
        store.reviews[review_id] = {"id": review_id, "deliverable_id": deliverable_id, "reviewer": actor.actor_id, **body.model_dump(), "created_at": now()}
        audit_response(actor, "deliverable", deliverable_id, f"deliverable.{body.decision}", organization_for_engagement(project["engagement_id"]))
        return {"deliverable": deliverable, "review": store.reviews[review_id]}


@app.post("/api/deliverables/{deliverable_id}/accept")
def accept_deliverable(deliverable_id: str, request: Request) -> dict:
    actor = identity(request)
    if postgres_mode():
        try:
            return postgres_repository().accept_deliverable(UUID(deliverable_id), actor.actor_id)
        except PermissionError as exc:
            raise HTTPException(status_code=403, detail=str(exc)) from exc
        except LookupError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except ValueError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
    unsupported_memory_domain("client acceptance")
    deliverable = store.deliverables.get(deliverable_id)
    if not deliverable:
        raise HTTPException(status_code=404, detail="Deliverable not found")
    project = project_for_package(deliverable["work_package_id"])
    org_id = organization_for_engagement(project["engagement_id"])
    if "client" not in store.memberships.get((actor.actor_id, org_id), set()):
        raise HTTPException(status_code=403, detail="Only an active client membership may record acceptance")
    if deliverable["status"] != "approved":
        raise HTTPException(status_code=409, detail="Only an internally approved deliverable can be accepted")
    deliverable["status"] = "accepted"
    deliverable["accepted_by"] = actor.actor_id
    deliverable["accepted_at"] = now()
    memory_notification(project["id"], "internal", "deliverable.client_accepted", "Client acceptance recorded", "A client accepted an internally approved deliverable.")
    audit_response(actor, "deliverable", deliverable_id, "deliverable.client_accepted", org_id)
    return deliverable


@app.post("/api/deliverables/{deliverable_id}/client-revision")
def request_client_revision(deliverable_id: str, body: ClientRevisionCreate, request: Request) -> dict:
    """Allow an authorized client to request a revision without changing the immutable version."""
    actor = identity(request)
    if postgres_mode():
        try:
            return postgres_repository().request_client_revision(UUID(deliverable_id), actor.actor_id, body.comment)
        except PermissionError as exc:
            raise HTTPException(status_code=403, detail=str(exc)) from exc
        except LookupError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except ValueError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
    deliverable = store.deliverables.get(deliverable_id)
    if not deliverable:
        raise HTTPException(status_code=404, detail="Deliverable not found")
    project = project_for_package(deliverable["work_package_id"])
    org_id = organization_for_engagement(project["engagement_id"])
    if "client" not in store.memberships.get((actor.actor_id, org_id), set()):
        raise HTTPException(status_code=403, detail="Only an active client membership may request a revision")
    if deliverable["status"] != "approved":
        raise HTTPException(status_code=409, detail="Only an internally approved deliverable can be sent back for revision")
    deliverable["status"] = "revision_requested"
    request_id = str(uuid4())
    store.client_revision_requests[request_id] = {"id": request_id, "deliverable_id": deliverable_id, "client_id": actor.actor_id, "comment": body.comment, "created_at": now()}
    memory_notification(project["id"], "internal", "deliverable.client_revision_requested", "Client revision requested", "A client requested changes to an approved deliverable.")
    audit_response(actor, "deliverable", deliverable_id, "deliverable.client_revision_requested", org_id)
    return {"deliverable": deliverable, "revision_request": store.client_revision_requests[request_id]}


@app.post("/api/projects/{project_id}/complete")
def complete_project(project_id: str, request: Request) -> dict:
    actor = identity(request)
    if postgres_mode():
        try:
            return postgres_repository().complete_project(UUID(project_id), actor.actor_id)
        except PermissionError as exc:
            raise HTTPException(status_code=403, detail=str(exc)) from exc
        except LookupError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except ValueError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
    unsupported_memory_domain("project completion")
    project = store.projects.get(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    org_id = organization_for_engagement(project["engagement_id"])
    member(actor, org_id, "owner")
    if project["status"] == "completed":
        return project
    versions = [{key: item[key] for key in ("id", "title", "version")} for item in store.deliverables.values()
                if item["status"] == "accepted" and store.work_packages[item["work_package_id"]]["project_id"] == project_id]
    if not versions:
        raise HTTPException(status_code=409, detail="At least one client-accepted deliverable is required")
    store.handovers[project_id] = {"versions": versions, "created_at": now()}
    project["status"] = "completed"
    audit_response(actor, "project", project_id, "project.completed", org_id)
    return project


@app.get("/api/audit")
def audit(request: Request) -> list[dict]:
    actor = identity(request)
    require_global(actor, "admin", "reviewer")
    if postgres_mode():
        return postgres_repository().list_audit(actor.actor_id, admin="admin" in actor.roles)
    if "admin" in actor.roles:
        return list(store.audit)
    visible_organizations = {
        organization_id
        for (member_id, organization_id), roles in store.memberships.items()
        if member_id == actor.actor_id and roles.intersection({"owner", "reviewer"})
    }
    return [event for event in store.audit if event["organization_id"] in visible_organizations]
