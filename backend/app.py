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
    engagements: dict[str, dict] = field(default_factory=dict)
    projects: dict[str, dict] = field(default_factory=dict)
    work_packages: dict[str, dict] = field(default_factory=dict)
    assignments: dict[str, dict] = field(default_factory=dict)
    ai_runs: dict[str, dict] = field(default_factory=dict)
    artifacts: dict[str, dict] = field(default_factory=dict)
    deliverables: dict[str, dict] = field(default_factory=dict)
    reviews: dict[str, dict] = field(default_factory=dict)
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
        self.engagements.clear()
        self.projects.clear()
        self.work_packages.clear()
        self.assignments.clear()
        self.ai_runs.clear()
        self.artifacts.clear()
        self.deliverables.clear()
        self.reviews.clear()
        self.audit.clear()


store = Store()
app = FastAPI(title="Data Fellows Studio", docs_url=None, redoc_url=None)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:8100"],
    allow_methods=["GET", "POST", "DELETE"],
    allow_headers=["Authorization", "Content-Type"],
)


def identity(request: Request) -> Identity:
    """Resolve only the explicit synthetic adapter in local test mode."""
    if os.getenv("STUDIO_TEST_MODE", "false").lower() != "true":
        raise HTTPException(status_code=503, detail="Microsoft Entra authentication is not configured")
    header = request.headers.get("authorization", "")
    if not header.startswith("Bearer test:"):
        raise HTTPException(status_code=401, detail="A workforce access token is required")
    parts = header.removeprefix("Bearer test:").split(":", 1)
    if len(parts) != 2 or not parts[0] or not parts[1]:
        raise HTTPException(status_code=401, detail="Malformed synthetic identity")
    roles = frozenset(role for role in parts[1].split(",") if role)
    return Identity(parts[0], roles)


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


def audit_response(actor: Identity, resource_type: str, resource_id: str, action: str, organization_id: str | None = None) -> None:
    store.event(actor, action, resource_type, resource_id, organization_id=organization_id)


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "mode": "synthetic" if os.getenv("STUDIO_TEST_MODE", "false").lower() == "true" else "entra-required"}


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


@app.post("/api/professionals/{professional_id}/approve")
def approve_professional(professional_id: str, request: Request) -> dict:
    actor = identity(request)
    if postgres_mode():
        postgres_repository().approve_professional(professional_id, actor.actor_id)
        return {"professional_id": professional_id, "status": "approved"}
    unsupported_memory_domain("professional admissions")
    require_global(actor, "admin")
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
    package_id = str(uuid4())
    store.work_packages[package_id] = {
        "id": package_id,
        "project_id": body.project_id,
        "title": body.title,
        "acceptance_criteria": body.acceptance_criteria,
        "status": "unassigned",
    }
    audit_response(actor, "work_package", package_id, "work_package.created", org_id)
    return store.work_packages[package_id]


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
    store.assignments[assignment_id] = {"id": assignment_id, "work_package_id": package_id, "professional_id": body.professional_id, "status": "accepted"}
    store.work_packages[package_id]["status"] = "assigned"
    audit_response(actor, "assignment", assignment_id, "assignment.accepted", org_id)
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
    unsupported_memory_domain("assignments")


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


@app.post("/api/ai-runs/{run_id}/decision")
def decide_ai_run(run_id: str, body: Decision, request: Request) -> dict:
    actor = identity(request)
    if postgres_mode():
        require_global(actor, "admin", "reviewer")
        try:
            return postgres_repository().decide_ai_artifact(UUID(run_id), actor.actor_id, body.decision, body.comment)
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
    unsupported_memory_domain("deliverables")
    project = project_for_package(body.work_package_id)
    org_id = organization_for_engagement(project["engagement_id"])
    allowed = store.memberships.get((actor.actor_id, org_id), set())
    assigned = any(a["work_package_id"] == body.work_package_id and a["professional_id"] == actor.actor_id for a in store.assignments.values())
    if "admin" not in actor.roles and "owner" not in allowed and not assigned:
        raise HTTPException(status_code=403, detail="Only an assigned delivery resource may submit")
    existing = [d for d in store.deliverables.values() if d["work_package_id"] == body.work_package_id]
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
    member(actor, org_id, "client")
    if deliverable["status"] != "approved":
        raise HTTPException(status_code=409, detail="Only an internally approved deliverable can be accepted")
    deliverable["status"] = "accepted"
    deliverable["accepted_by"] = actor.actor_id
    deliverable["accepted_at"] = now()
    audit_response(actor, "deliverable", deliverable_id, "deliverable.client_accepted", org_id)
    return deliverable


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
