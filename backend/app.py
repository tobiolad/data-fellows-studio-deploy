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
from typing import Literal
from uuid import UUID, uuid4

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from backend.auth import EntraSettings, EntraTokenValidator, HttpJwksProvider, TokenValidationError
from backend.persistence import PersistenceConfigurationError, PostgresRepository


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
    engagements: dict[str, dict] = field(default_factory=dict)
    projects: dict[str, dict] = field(default_factory=dict)
    work_packages: dict[str, dict] = field(default_factory=dict)
    assignments: dict[str, dict] = field(default_factory=dict)
    ai_runs: dict[str, dict] = field(default_factory=dict)
    artifacts: dict[str, dict] = field(default_factory=dict)
    deliverables: dict[str, dict] = field(default_factory=dict)
    reviews: dict[str, dict] = field(default_factory=dict)
    client_revision_requests: dict[str, dict] = field(default_factory=dict)
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
        self.engagements.clear()
        self.projects.clear()
        self.work_packages.clear()
        self.assignments.clear()
        self.ai_runs.clear()
        self.artifacts.clear()
        self.deliverables.clear()
        self.reviews.clear()
        self.client_revision_requests.clear()
        self.project_messages.clear()
        self.project_documents.clear()
        self.notifications.clear()
        self.opportunities.clear()
        self.opportunity_interests.clear()
        self.audit.clear()


store = Store()
app = FastAPI(title="Data Fellows Studio", docs_url=None, redoc_url=None)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://localhost:8100",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:8100",
    ],
    allow_methods=["GET", "POST", "DELETE"],
    allow_headers=["Authorization", "Content-Type"],
)


def identity(request: Request) -> Identity:
    """Use the synthetic adapter only in tests; otherwise validate Entra JWTs."""
    header = request.headers.get("authorization", "")
    if os.getenv("STUDIO_TEST_MODE", "false").lower() == "true":
        if not header.startswith("Bearer test:"):
            raise HTTPException(status_code=401, detail="A workforce access token is required")
        parts = header.removeprefix("Bearer test:").split(":", 1)
        if len(parts) != 2 or not parts[0] or not parts[1]:
            raise HTTPException(status_code=401, detail="Malformed synthetic identity")
        roles = frozenset(role for role in parts[1].split(",") if role)
        return Identity(parts[0], roles)
    if os.getenv("STUDIO_ENTRA_ENABLED", "false").lower() != "true":
        raise HTTPException(status_code=503, detail="Microsoft Entra authentication is not configured")
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


def memory_project_access(actor: Identity, project_id: str) -> tuple[dict, str, set[str]]:
    """Resolve project scope and caller membership without trusting client input."""
    project = store.projects.get(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    organization_id = organization_for_engagement(project["engagement_id"])
    roles = store.memberships.get((actor.actor_id, organization_id), set())
    assigned = any(
        item["professional_id"] == actor.actor_id
        and item["status"] == "accepted"
        and store.work_packages.get(item["work_package_id"], {}).get("project_id") == project_id
        for item in store.assignments.values()
    )
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
    storage_reference: str = Field(min_length=2, max_length=512)


class OpportunityCreate(BaseModel):
    title: str = Field(min_length=2, max_length=160)
    summary: str = Field(min_length=2, max_length=4000)
    specialization: str = Field(min_length=2, max_length=120)
    skills: list[str] = Field(default_factory=list, max_length=20)
    compensation: str | None = Field(default=None, max_length=240)
    deadline: datetime | None = None


class OpportunityInterestCreate(BaseModel):
    approach: str = Field(min_length=2, max_length=4000)


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
        ),
        "postgres_configured": (test_mode and deployment_env not in {"staging", "production"})
        or (persistence == "postgres" and bool(os.getenv("STUDIO_DATABASE_URL", "").strip())),
    }
    if not all(checks.values()):
        raise HTTPException(status_code=503, detail={"status": "not_ready", "checks": checks})
    return {"status": "ready", "environment": deployment_env, "persistence": persistence, "checks": checks}


@app.get("/api/me")
def me(request: Request) -> dict:
    actor = identity(request)
    return {"id": actor.actor_id, "roles": sorted(actor.roles), "authentication": "synthetic-test"}


@app.post("/api/organizations", status_code=status.HTTP_201_CREATED)
def create_organization(body: OrganizationCreate, request: Request) -> dict:
    actor = identity(request)
    require_global(actor, "admin")
    if postgres_mode():
        organization_id = postgres_repository().create_organization(body.name, actor.actor_id)
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
        postgres_repository().grant_membership(organization_uuid(organization_id), body.actor_id, body.role, actor.actor_id)
        return {"actor_id": body.actor_id, "organization_id": organization_id, "role": body.role}
    if organization_id not in store.organizations:
        raise HTTPException(status_code=404, detail="Organization not found")
    member(actor, organization_id, "owner")
    store.memberships.setdefault((body.actor_id, organization_id), set()).add(body.role)
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
    assigned.remove(role)
    if not assigned:
        store.memberships.pop((member_id, organization_id), None)
    audit_response(actor, "organization_membership", f"{member_id}:{organization_id}", "membership.revoked", organization_id)
    return {"actor_id": member_id, "organization_id": organization_id, "role": role, "status": "revoked"}


@app.post("/api/professionals/{professional_id}/application", status_code=status.HTTP_201_CREATED)
def submit_professional_application(professional_id: str, request: Request) -> dict:
    actor = identity(request)
    if actor.actor_id != professional_id and "admin" not in actor.roles:
        raise HTTPException(status_code=403, detail="A professional may submit only their own application")
    if postgres_mode():
        postgres_repository().submit_professional_application(professional_id, actor.actor_id)
        return {"professional_id": professional_id, "status": "pending"}
    store.approved_professionals.discard(professional_id)
    store.professional_admissions[professional_id] = {
        "professional_id": professional_id,
        "status": "pending",
        "decided_by": None,
        "decided_at": None,
        "created_at": now(),
    }
    store.event(actor, "professional.application_submitted", "professional", professional_id)
    return {"professional_id": professional_id, "status": "pending"}


@app.get("/api/professionals/{professional_id}/application")
def get_professional_application(professional_id: str, request: Request) -> dict:
    actor = identity(request)
    if actor.actor_id != professional_id and "admin" not in actor.roles:
        raise HTTPException(status_code=403, detail="Application access is not authorized")
    if postgres_mode():
        record = postgres_repository().get_professional_application(professional_id)
    else:
        record = store.professional_admissions.get(professional_id)
    if not record:
        raise HTTPException(status_code=404, detail="Professional application not found")
    return record


@app.get("/api/professionals/admissions")
def list_professional_admissions(
    request: Request,
    status_filter: Literal["pending", "approved", "rejected", "revoked"] | None = None,
) -> list[dict]:
    actor = identity(request)
    require_global(actor, "admin")
    if postgres_mode():
        return postgres_repository().list_professional_admissions(status_filter)
    records = list(store.professional_admissions.values())
    if status_filter:
        records = [record for record in records if record["status"] == status_filter]
    return sorted(records, key=lambda record: (record["created_at"], record["professional_id"]))


@app.post("/api/professionals/{professional_id}/decision")
def decide_professional(professional_id: str, body: Decision, request: Request) -> dict:
    actor = identity(request)
    require_global(actor, "admin")
    if body.decision not in {"approved", "rejected"}:
        raise HTTPException(status_code=422, detail="Professional decisions must be approved or rejected")
    if postgres_mode():
        postgres_repository().decide_professional(professional_id, body.decision, actor.actor_id)
        return {"professional_id": professional_id, "status": body.decision}
    if body.decision == "approved":
        store.approved_professionals.add(professional_id)
    else:
        store.approved_professionals.discard(professional_id)
    created_at = store.professional_admissions.get(professional_id, {}).get("created_at", now())
    store.professional_admissions[professional_id] = {
        "professional_id": professional_id,
        "status": body.decision,
        "decided_by": actor.actor_id,
        "decided_at": now(),
        "created_at": created_at,
    }
    audit_response(actor, "professional", professional_id, f"professional.{body.decision}")
    return {"professional_id": professional_id, "status": body.decision}


@app.post("/api/professionals/{professional_id}/approve")
def approve_professional(professional_id: str, request: Request) -> dict:
    """Compatibility endpoint retained for existing synthetic clients."""
    actor = identity(request)
    require_global(actor, "admin")
    if postgres_mode():
        postgres_repository().approve_professional(professional_id, actor.actor_id)
        return {"professional_id": professional_id, "status": "approved"}
    store.approved_professionals.add(professional_id)
    audit_response(actor, "professional", professional_id, "professional.approved")
    return {"professional_id": professional_id, "status": "approved"}


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
    for engagement in store.engagements.values():
        if (actor.actor_id, engagement["organization_id"]) in store.memberships:
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
    applications = list(store.professional_admissions.values())
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
            "pending_applications": sum(item["status"] == "pending" for item in applications),
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
    allowed_groups = {"internal"}
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
        assigned = any(
            assignment["professional_id"] == actor.actor_id
            and assignment["status"] == "accepted"
            and store.work_packages.get(assignment["work_package_id"], {}).get("project_id") in {
                project["id"] for project in store.projects.values() if project["engagement_id"] == engagement_id
            }
            for assignment in store.assignments.values()
        )
        if not roles.intersection({"owner", "reviewer", "client"}) and not assigned:
            raise HTTPException(status_code=403, detail="Project access is not authorized")
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
    assigned = any(item["professional_id"] == actor.actor_id and item["status"] == "accepted" and store.work_packages.get(item["work_package_id"], {}).get("project_id") == project_id for item in store.assignments.values())
    if "admin" not in actor.roles and not roles.intersection({"owner", "reviewer", "client"}) and not assigned:
        raise HTTPException(status_code=403, detail="Work package access is not authorized")
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
    assignment["status"] = "accepted"
    project = project_for_package(assignment["work_package_id"])
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
        project = store.projects.get(package.get("project_id"), {})
        engagement = store.engagements.get(project.get("engagement_id"), {})
        result.append({**item, "title": package.get("title"), "project_name": project.get("name"), "engagement_name": engagement.get("name"), "objective": engagement.get("objective")})
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


@app.post("/api/ai-runs", status_code=status.HTTP_201_CREATED)
def create_ai_run(body: AIRunCreate, request: Request) -> dict:
    actor = identity(request)
    if postgres_mode():
        if body.tools != ["planning"]:
            raise HTTPException(status_code=422, detail="Only the bounded planning tool is enabled")
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
        validate_synthetic_output(output)
        try:
            run_id, artifact_id, _ = postgres_repository().create_ai_run(UUID(body.work_package_id), actor.actor_id, body.specification, body.budget_cents, output)
        except PermissionError as exc:
            raise HTTPException(status_code=403, detail=str(exc)) from exc
        except LookupError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        return {"id": str(run_id), "work_package_id": body.work_package_id, "requested_by": actor.actor_id, "status": "succeeded", "budget_cents": body.budget_cents, "spent_cents": 0, "agent": "synthetic-planner-v1", "artifact_id": str(artifact_id), "artifact": {"id": str(artifact_id), "run_id": str(run_id), "status": "pending_review", "content": output}}
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
    assigned = any(a["work_package_id"] == body.work_package_id and a["professional_id"] == actor.actor_id for a in store.assignments.values())
    if "admin" not in actor.roles and "owner" not in allowed and not assigned:
        raise HTTPException(status_code=403, detail="Only an assigned delivery resource may submit")
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
    assigned = any(item["work_package_id"] == package_id and item["professional_id"] == actor.actor_id and item["status"] == "accepted" for item in store.assignments.values())
    if "admin" not in actor.roles and not roles and not assigned:
        raise HTTPException(status_code=403, detail="Deliverable access is not authorized")
    deliverables = [item for item in store.deliverables.values() if item["work_package_id"] == package_id]
    if "client" in roles and "owner" not in roles and "reviewer" not in roles:
        deliverables = [item for item in deliverables if item["status"] in {"approved", "accepted"}]
    return sorted(deliverables, key=lambda item: item["version"])


@app.post("/api/deliverables/{deliverable_id}/review")
def review_deliverable(deliverable_id: str, body: ReviewCreate, request: Request) -> dict:
    actor = identity(request)
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
    require_global(actor, "admin", "reviewer")
    project = project_for_package(deliverable["work_package_id"])
    member(actor, organization_for_engagement(project["engagement_id"]), "reviewer", "owner")
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
    if not any(d["status"] == "accepted" and store.work_packages[d["work_package_id"]]["project_id"] == project_id for d in store.deliverables.values()):
        raise HTTPException(status_code=409, detail="At least one client-accepted deliverable is required")
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
        if member_id == actor.actor_id and roles
    }
    return [event for event in store.audit if event["organization_id"] in visible_organizations]
