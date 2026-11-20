"""PostgreSQL persistence primitives for Studio.

The synthetic API intentionally keeps its in-memory store for deterministic
tests. Production startup must select this repository with
``STUDIO_DATABASE_URL`` and run the versioned migrations before accepting
real data. No caller-supplied role or organization is trusted here.
"""

from __future__ import annotations

import json
import os
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator
from uuid import UUID, uuid4


MIGRATIONS_DIR = Path(__file__).resolve().parent.parent / "migrations"


class PersistenceConfigurationError(RuntimeError):
    """Raised when production persistence is not configured safely."""


class PostgresRepository:
    """Small transaction-safe repository for the initial delivery slice."""

    def __init__(self, dsn: str | None = None, connect_factory: Any | None = None) -> None:
        self.dsn = dsn or os.getenv("STUDIO_DATABASE_URL")
        if not self.dsn and connect_factory is None:
            raise PersistenceConfigurationError("STUDIO_DATABASE_URL is required for PostgreSQL persistence")
        self._connect_factory = connect_factory

    def _connect(self):
        if self._connect_factory is not None:
            return self._connect_factory(self.dsn)
        try:
            import psycopg
        except ImportError as exc:  # pragma: no cover - dependency is installed by deployment
            raise PersistenceConfigurationError("psycopg is required for PostgreSQL persistence") from exc
        return psycopg.connect(self.dsn)

    @contextmanager
    def transaction(self) -> Iterator[Any]:
        """Commit a transaction only after the caller exits successfully."""
        connection = self._connect()
        try:
            with connection.transaction():
                yield connection
        finally:
            connection.close()

    def migrate(self) -> None:
        """Apply migrations in lexical order inside one transaction."""
        scripts = sorted(MIGRATIONS_DIR.glob("*.sql"))
        if not scripts:
            raise PersistenceConfigurationError("No Studio migrations were found")
        with self.transaction() as connection:
            cursor = connection.cursor()
            cursor.execute("CREATE TABLE IF NOT EXISTS studio_schema_migrations (version text PRIMARY KEY, applied_at timestamptz NOT NULL DEFAULT now())")
            for script in scripts:
                version = script.name.split("_", 1)[0]
                cursor.execute("SELECT 1 FROM studio_schema_migrations WHERE version = %s", (version,))
                if cursor.fetchone():
                    continue
                cursor.execute(script.read_text(encoding="utf-8"))
                cursor.execute("INSERT INTO studio_schema_migrations(version) VALUES (%s)", (version,))

    def create_organization(self, name: str, owner_id: str) -> UUID:
        organization_id = uuid4()
        with self.transaction() as connection:
            cursor = connection.cursor()
            cursor.execute("INSERT INTO organizations(id, name) VALUES (%s, %s)", (organization_id, name))
            cursor.execute(
                "INSERT INTO memberships(organization_id, actor_id, role) VALUES (%s, %s, 'owner')",
                (organization_id, owner_id),
            )
            self._audit(cursor, organization_id, owner_id, "organization.created", "organization", str(organization_id))
        return organization_id

    def grant_membership(self, organization_id: UUID, actor_id: str, role: str, actor: str) -> None:
        with self.transaction() as connection:
            cursor = connection.cursor()
            self._require_owner(cursor, organization_id, actor)
            cursor.execute(
                """INSERT INTO memberships(organization_id, actor_id, role)
                   VALUES (%s, %s, %s)
                   ON CONFLICT (organization_id, actor_id, role)
                   DO UPDATE SET revoked_at = NULL""",
                (organization_id, actor_id, role),
            )
            self._audit(cursor, organization_id, actor, "membership.granted", "organization_membership", f"{actor_id}:{organization_id}")

    def create_engagement(self, organization_id: UUID, name: str, objective: str, actor: str) -> UUID:
        engagement_id = uuid4()
        with self.transaction() as connection:
            cursor = connection.cursor()
            self._require_owner(cursor, organization_id, actor)
            cursor.execute(
                "INSERT INTO engagements(id, organization_id, name, objective, status) VALUES (%s, %s, %s, %s, 'authorized')",
                (engagement_id, organization_id, name, objective),
            )
            self._audit(cursor, organization_id, actor, "engagement.created", "engagement", str(engagement_id))
        return engagement_id

    def list_engagements(self, actor_id: str, admin: bool = False) -> list[dict[str, Any]]:
        with self.transaction() as connection:
            cursor = connection.cursor()
            if admin:
                cursor.execute("SELECT id, organization_id, name, objective, status, created_at FROM engagements ORDER BY created_at")
            else:
                cursor.execute(
                    """SELECT e.id, e.organization_id, e.name, e.objective, e.status, e.created_at
                       FROM engagements e
                       JOIN memberships m ON m.organization_id = e.organization_id
                       WHERE m.actor_id = %s AND m.revoked_at IS NULL
                       ORDER BY e.created_at""",
                    (actor_id,),
                )
            return [
                {
                    "id": row[0],
                    "organization_id": row[1],
                    "name": row[2],
                    "objective": row[3],
                    "status": row[4],
                    "created_at": row[5],
                }
                for row in cursor.fetchall()
            ]

    def create_project(self, engagement_id: UUID, name: str, actor: str) -> UUID:
        project_id = uuid4()
        with self.transaction() as connection:
            cursor = connection.cursor()
            cursor.execute("SELECT organization_id FROM engagements WHERE id = %s", (engagement_id,))
            row = cursor.fetchone()
            if row is None:
                raise LookupError("Engagement not found")
            self._require_owner(cursor, row[0], actor)
            cursor.execute(
                "INSERT INTO projects(id, engagement_id, name, status) VALUES (%s, %s, %s, 'active')",
                (project_id, engagement_id, name),
            )
            self._audit(cursor, row[0], actor, "project.created", "project", str(project_id))
        return project_id

    def list_projects(self, engagement_id: UUID, actor: str, admin: bool = False) -> list[dict[str, Any]]:
        with self.transaction() as connection:
            cursor = connection.cursor()
            cursor.execute("SELECT organization_id FROM engagements WHERE id = %s", (engagement_id,))
            engagement = cursor.fetchone()
            if engagement is None:
                raise LookupError("Engagement not found")
            organization_id = engagement[0]
            if not admin:
                cursor.execute(
                    """SELECT 1 FROM memberships
                       WHERE organization_id = %s AND actor_id = %s AND revoked_at IS NULL
                         AND role IN ('owner', 'reviewer', 'client')
                       UNION SELECT 1 FROM assignments a
                       JOIN work_packages w ON w.id = a.work_package_id
                       JOIN projects p ON p.id = w.project_id
                       WHERE p.engagement_id = %s AND a.professional_id = %s
                         AND a.status = 'accepted'
                         AND (a.expires_at IS NULL OR a.expires_at > now())""",
                    (organization_id, actor, engagement_id, actor),
                )
                if cursor.fetchone() is None:
                    raise PermissionError("Project access is not authorized")
            cursor.execute(
                "SELECT id, engagement_id, name, status, created_at FROM projects WHERE engagement_id = %s ORDER BY created_at",
                (engagement_id,),
            )
            return [
                {"id": str(row[0]), "engagement_id": str(row[1]), "name": row[2], "status": row[3], "created_at": row[4]}
                for row in cursor.fetchall()
            ]

    def create_work_package(self, project_id: UUID, title: str, acceptance_criteria: list[str], depends_on: list[UUID], actor: str) -> UUID:
        package_id = uuid4()
        with self.transaction() as connection:
            cursor = connection.cursor()
            cursor.execute(
                "SELECT e.organization_id FROM projects p JOIN engagements e ON e.id = p.engagement_id WHERE p.id = %s",
                (project_id,),
            )
            row = cursor.fetchone()
            if row is None:
                raise LookupError("Project not found")
            self._require_owner(cursor, row[0], actor)
            if depends_on:
                cursor.execute(
                    "SELECT COUNT(*) FROM work_packages WHERE project_id = %s AND id = ANY(%s::uuid[])",
                    (project_id, depends_on),
                )
                if cursor.fetchone()[0] != len(set(depends_on)):
                    raise ValueError("Dependencies must be existing work packages in the same project")
            cursor.execute(
                "INSERT INTO work_packages(id, project_id, title, acceptance_criteria, status) VALUES (%s, %s, %s, %s, 'unassigned')",
                (package_id, project_id, title, json.dumps(acceptance_criteria)),
            )
            for dependency_id in set(depends_on):
                cursor.execute(
                    "INSERT INTO work_package_dependencies(work_package_id, depends_on_id) VALUES (%s, %s)",
                    (package_id, dependency_id),
                )
            self._audit(cursor, row[0], actor, "work_package.created", "work_package", str(package_id), {"depends_on": [str(item) for item in depends_on]})
        return package_id

    def list_work_packages(self, project_id: UUID, actor: str, admin: bool = False) -> list[dict[str, Any]]:
        with self.transaction() as connection:
            cursor = connection.cursor()
            cursor.execute("SELECT e.organization_id FROM projects p JOIN engagements e ON e.id = p.engagement_id WHERE p.id = %s", (project_id,))
            project = cursor.fetchone()
            if project is None:
                raise LookupError("Project not found")
            organization_id = project[0]
            if not admin:
                cursor.execute(
                    """SELECT 1 FROM memberships WHERE organization_id = %s AND actor_id = %s AND revoked_at IS NULL AND role IN ('owner', 'reviewer', 'client')
                       UNION SELECT 1 FROM assignments a JOIN work_packages w ON w.id = a.work_package_id
                       WHERE w.project_id = %s AND a.professional_id = %s AND a.status = 'accepted'
                         AND (a.expires_at IS NULL OR a.expires_at > now())""",
                    (organization_id, actor, project_id, actor),
                )
                if cursor.fetchone() is None:
                    raise PermissionError("Work package access is not authorized")
            cursor.execute("SELECT id, project_id, title, acceptance_criteria, status, created_at FROM work_packages WHERE project_id = %s ORDER BY created_at", (project_id,))
            result = []
            for row in cursor.fetchall():
                cursor.execute("SELECT depends_on_id FROM work_package_dependencies WHERE work_package_id = %s ORDER BY depends_on_id", (row[0],))
                result.append({"id": str(row[0]), "project_id": str(row[1]), "title": row[2], "acceptance_criteria": row[3], "status": row[4], "created_at": row[5], "depends_on": [str(item[0]) for item in cursor.fetchall()]})
            return result

    def submit_professional_application(self, professional_id: str, actor: str) -> None:
        with self.transaction() as connection:
            cursor = connection.cursor()
            cursor.execute(
                """INSERT INTO professional_admissions(professional_id, status)
                   VALUES (%s, 'pending')
                   ON CONFLICT (professional_id) DO UPDATE
                   SET status = 'pending', decided_by = NULL, decided_at = NULL""",
                (professional_id,),
            )
            self._audit(cursor, None, actor, "professional.application_submitted", "professional", professional_id)

    def decide_professional(self, professional_id: str, status: str, actor: str) -> None:
        if status not in {"approved", "rejected", "revoked"}:
            raise ValueError("Unsupported professional decision")
        with self.transaction() as connection:
            cursor = connection.cursor()
            cursor.execute(
                """INSERT INTO professional_admissions(professional_id, status, decided_by, decided_at)
                   VALUES (%s, %s, %s, now())
                   ON CONFLICT (professional_id) DO UPDATE SET status = EXCLUDED.status, decided_by = EXCLUDED.decided_by, decided_at = now()""",
                (professional_id, status, actor),
            )
            self._audit(cursor, None, actor, f"professional.{status}", "professional", professional_id)

    def approve_professional(self, professional_id: str, actor: str) -> None:
        """Compatibility wrapper for the original approval endpoint."""
        self.decide_professional(professional_id, "approved", actor)

    def assign_work(self, package_id: UUID, professional_id: str, expires_at: datetime | None, actor: str) -> UUID:
        assignment_id = uuid4()
        with self.transaction() as connection:
            cursor = connection.cursor()
            cursor.execute(
                """SELECT e.organization_id FROM work_packages w
                   JOIN projects p ON p.id = w.project_id
                   JOIN engagements e ON e.id = p.engagement_id
                   WHERE w.id = %s""",
                (package_id,),
            )
            row = cursor.fetchone()
            if row is None:
                raise LookupError("Work package not found")
            organization_id = row[0]
            self._require_owner(cursor, organization_id, actor)
            cursor.execute("SELECT 1 FROM professional_admissions WHERE professional_id = %s AND status = 'approved'", (professional_id,))
            if cursor.fetchone() is None:
                raise ValueError("Professional approval is required before assignment")
            cursor.execute(
                "SELECT 1 FROM memberships WHERE organization_id = %s AND actor_id = %s AND role = 'professional' AND revoked_at IS NULL",
                (organization_id, professional_id),
            )
            if cursor.fetchone() is None:
                raise PermissionError("Professional is not admitted to this organization")
            cursor.execute(
                """INSERT INTO assignments(id, work_package_id, professional_id, status, expires_at)
                   VALUES (%s, %s, %s, 'invited', %s)""",
                (assignment_id, package_id, professional_id, expires_at),
            )
            cursor.execute("UPDATE work_packages SET status = 'assigned' WHERE id = %s", (package_id,))
            self._audit(cursor, organization_id, actor, "assignment.invited", "assignment", str(assignment_id))
        return assignment_id

    def accept_assignment(self, assignment_id: UUID, professional_id: str) -> None:
        with self.transaction() as connection:
            cursor = connection.cursor()
            cursor.execute(
                """SELECT a.status, a.expires_at, e.organization_id
                   FROM assignments a
                   JOIN work_packages w ON w.id = a.work_package_id
                   JOIN projects p ON p.id = w.project_id
                   JOIN engagements e ON e.id = p.engagement_id
                   WHERE a.id = %s AND a.professional_id = %s""",
                (assignment_id, professional_id),
            )
            row = cursor.fetchone()
            if row is None:
                raise LookupError("Assignment not found")
            status, expires_at, organization_id = row
            if status != "invited":
                raise ValueError("Assignment invitation is no longer active")
            if expires_at and expires_at <= datetime.now(timezone.utc):
                cursor.execute("UPDATE assignments SET status = 'expired' WHERE id = %s", (assignment_id,))
                raise ValueError("Assignment invitation has expired")
            cursor.execute("UPDATE assignments SET status = 'accepted' WHERE id = %s", (assignment_id,))
            self._audit(cursor, organization_id, professional_id, "assignment.accepted", "assignment", str(assignment_id))

    def decline_assignment(self, assignment_id: UUID, professional_id: str) -> None:
        with self.transaction() as connection:
            cursor = connection.cursor()
            cursor.execute(
                """SELECT a.status, e.organization_id
                   FROM assignments a
                   JOIN work_packages w ON w.id = a.work_package_id
                   JOIN projects p ON p.id = w.project_id
                   JOIN engagements e ON e.id = p.engagement_id
                   WHERE a.id = %s AND a.professional_id = %s""",
                (assignment_id, professional_id),
            )
            row = cursor.fetchone()
            if row is None:
                raise LookupError("Assignment not found")
            current_status, organization_id = row
            if current_status != "invited":
                raise ValueError("Only an active invitation can be declined")
            cursor.execute("UPDATE assignments SET status = 'declined' WHERE id = %s", (assignment_id,))
            self._audit(cursor, organization_id, professional_id, "assignment.declined", "assignment", str(assignment_id))

    def list_assignments(self, professional_id: str, actor: str, admin: bool = False) -> list[dict[str, Any]]:
        if actor != professional_id and not admin:
            raise PermissionError("Assignment access is not authorized")
        with self.transaction() as connection:
            cursor = connection.cursor()
            cursor.execute(
                """SELECT a.id, a.work_package_id, a.professional_id, a.status, a.expires_at, a.created_at
                   FROM assignments a
                   WHERE a.professional_id = %s
                   ORDER BY a.created_at""",
                (professional_id,),
            )
            return [
                {"id": str(row[0]), "work_package_id": str(row[1]), "professional_id": row[2], "status": row[3], "expires_at": row[4], "created_at": row[5]}
                for row in cursor.fetchall()
            ]

    def create_ai_run(self, package_id: UUID, requested_by: str, specification: str, budget_cents: int, output: dict[str, Any]) -> tuple[UUID, UUID, UUID]:
        run_id, artifact_id = uuid4(), uuid4()
        with self.transaction() as connection:
            cursor = connection.cursor()
            cursor.execute(
                """SELECT e.organization_id FROM work_packages w
                   JOIN projects p ON p.id = w.project_id
                   JOIN engagements e ON e.id = p.engagement_id
                   WHERE w.id = %s""",
                (package_id,),
            )
            row = cursor.fetchone()
            if row is None:
                raise LookupError("Work package not found")
            organization_id = row[0]
            self._require_owner(cursor, organization_id, requested_by)
            cursor.execute(
                """INSERT INTO ai_runs(id, work_package_id, requested_by, agent_version, policy_version, budget_cents, spent_cents, status, started_at, finished_at)
                   VALUES (%s, %s, %s, 'synthetic-planner-v1', 'planning-only-v1', %s, 0, 'succeeded', now(), now())""",
                (run_id, package_id, requested_by, budget_cents),
            )
            cursor.execute(
                """INSERT INTO artifacts(id, run_id, version, content, status)
                   VALUES (%s, %s, 1, %s, 'pending_review')""",
                (artifact_id, run_id, json.dumps(output)),
            )
            self._audit(cursor, organization_id, requested_by, "ai_run.completed", "ai_run", str(run_id))
        return run_id, artifact_id, UUID(str(organization_id))

    def get_ai_run(self, run_id: UUID, actor: str, admin: bool = False) -> dict[str, Any]:
        with self.transaction() as connection:
            cursor = connection.cursor()
            cursor.execute(
                """SELECT r.id, r.work_package_id, r.requested_by, r.agent_version, r.policy_version,
                          r.budget_cents, r.spent_cents, r.status, r.cancel_requested,
                          r.error_code, r.created_at, r.started_at, r.finished_at, e.organization_id
                   FROM ai_runs r
                   JOIN work_packages w ON w.id = r.work_package_id
                   JOIN projects p ON p.id = w.project_id
                   JOIN engagements e ON e.id = p.engagement_id
                   WHERE r.id = %s""",
                (run_id,),
            )
            row = cursor.fetchone()
            if row is None:
                raise LookupError("AI run not found")
            if not admin:
                cursor.execute(
                    "SELECT 1 FROM memberships WHERE organization_id = %s AND actor_id = %s AND role IN ('owner', 'reviewer') AND revoked_at IS NULL",
                    (row[13], actor),
                )
                if cursor.fetchone() is None:
                    raise PermissionError("AI run access is not authorized")
            cursor.execute(
                "SELECT id, version, content, status, created_at FROM artifacts WHERE run_id = %s ORDER BY version DESC LIMIT 1",
                (run_id,),
            )
            artifact = cursor.fetchone()
            return {
                "id": str(row[0]),
                "work_package_id": str(row[1]),
                "requested_by": row[2],
                "agent_version": row[3],
                "policy_version": row[4],
                "budget_cents": row[5],
                "spent_cents": row[6],
                "status": row[7],
                "cancel_requested": row[8],
                "error_code": row[9],
                "created_at": row[10],
                "started_at": row[11],
                "finished_at": row[12],
                "artifact": None if artifact is None else {"id": str(artifact[0]), "version": artifact[1], "content": artifact[2], "status": artifact[3], "created_at": artifact[4]},
            }

    def decide_ai_artifact(self, run_id: UUID, reviewer_id: str, decision: str, comment: str) -> dict[str, Any]:
        with self.transaction() as connection:
            cursor = connection.cursor()
            cursor.execute(
                """SELECT a.id, a.status, r.status, r.requested_by, e.organization_id, a.content
                   FROM artifacts a
                   JOIN ai_runs r ON r.id = a.run_id
                   JOIN work_packages w ON w.id = r.work_package_id
                   JOIN projects p ON p.id = w.project_id
                   JOIN engagements e ON e.id = p.engagement_id
                   WHERE r.id = %s""",
                (run_id,),
            )
            row = cursor.fetchone()
            if row is None:
                raise LookupError("AI run not found")
            artifact_id, artifact_status, run_status, requested_by, organization_id, content = row
            if requested_by == reviewer_id:
                raise ValueError("Independent approval is required")
            cursor.execute(
                "SELECT 1 FROM memberships WHERE organization_id = %s AND actor_id = %s AND role IN ('reviewer', 'owner') AND revoked_at IS NULL",
                (organization_id, reviewer_id),
            )
            if cursor.fetchone() is None:
                raise PermissionError("Reviewer is not authorized for this organization")
            if run_status == "cancelled":
                raise ValueError("Cancelled AI runs cannot be approved")
            if artifact_status != "pending_review":
                raise ValueError("AI artifact is no longer pending review")
            cursor.execute("UPDATE artifacts SET status = %s WHERE id = %s", (decision, artifact_id))
            self._audit(cursor, organization_id, reviewer_id, f"ai_artifact.{decision}", "ai_artifact", str(artifact_id), {"comment": comment})
            return {"id": str(artifact_id), "run_id": str(run_id), "status": decision, "content": content, "decision_by": reviewer_id, "decision_comment": comment}

    def cancel_ai_run(self, run_id: UUID, actor: str) -> None:
        with self.transaction() as connection:
            cursor = connection.cursor()
            cursor.execute(
                """SELECT r.status, e.organization_id FROM ai_runs r
                   JOIN work_packages w ON w.id = r.work_package_id
                   JOIN projects p ON p.id = w.project_id
                   JOIN engagements e ON e.id = p.engagement_id
                   WHERE r.id = %s""",
                (run_id,),
            )
            row = cursor.fetchone()
            if row is None:
                raise LookupError("AI run not found")
            status, organization_id = row
            self._require_owner(cursor, organization_id, actor)
            if status in ("cancelled", "failed", "succeeded"):
                raise ValueError("AI run is already terminal")
            cursor.execute("UPDATE ai_runs SET cancel_requested = true, status = 'cancelled', finished_at = now() WHERE id = %s", (run_id,))
            self._audit(cursor, organization_id, actor, "ai_run.cancelled", "ai_run", str(run_id))

    def submit_deliverable(self, package_id: UUID, title: str, content: str, submitted_by: str) -> dict[str, Any]:
        deliverable_id = uuid4()
        with self.transaction() as connection:
            cursor = connection.cursor()
            cursor.execute(
                """SELECT e.organization_id FROM work_packages w
                   JOIN projects p ON p.id = w.project_id
                   JOIN engagements e ON e.id = p.engagement_id
                   WHERE w.id = %s""",
                (package_id,),
            )
            row = cursor.fetchone()
            if row is None:
                raise LookupError("Work package not found")
            organization_id = row[0]
            cursor.execute(
                """SELECT 1 FROM memberships WHERE organization_id = %s AND actor_id = %s AND role IN ('owner', 'client') AND revoked_at IS NULL
                   UNION SELECT 1 FROM assignments WHERE work_package_id = %s AND professional_id = %s AND status = 'accepted'""",
                (organization_id, submitted_by, package_id, submitted_by),
            )
            if cursor.fetchone() is None:
                raise PermissionError("Only an authorized delivery resource may submit")
            cursor.execute("SELECT COALESCE(MAX(version), 0) + 1 FROM deliverables WHERE work_package_id = %s", (package_id,))
            version = cursor.fetchone()[0]
            cursor.execute("SELECT status FROM deliverables WHERE work_package_id = %s ORDER BY version DESC LIMIT 1", (package_id,))
            latest = cursor.fetchone()
            if latest and latest[0] in {"under_review", "approved", "accepted"}:
                raise ValueError("A new version requires a revision request on the latest deliverable")
            cursor.execute(
                "INSERT INTO deliverables(id, work_package_id, version, title, content, submitted_by, status) VALUES (%s, %s, %s, %s, %s, %s, 'under_review')",
                (deliverable_id, package_id, version, title, content, submitted_by),
            )
            self._audit(cursor, organization_id, submitted_by, "deliverable.submitted", "deliverable", str(deliverable_id))
            return {"id": str(deliverable_id), "work_package_id": str(package_id), "version": version, "title": title, "content": content, "submitted_by": submitted_by, "status": "under_review"}

    def list_deliverables(self, package_id: UUID, actor: str, admin: bool = False) -> list[dict[str, Any]]:
        with self.transaction() as connection:
            cursor = connection.cursor()
            cursor.execute(
                """SELECT e.organization_id FROM work_packages w
                   JOIN projects p ON p.id = w.project_id
                   JOIN engagements e ON e.id = p.engagement_id
                   WHERE w.id = %s""",
                (package_id,),
            )
            package = cursor.fetchone()
            if package is None:
                raise LookupError("Work package not found")
            organization_id = package[0]
            role = None
            if not admin:
                cursor.execute(
                    "SELECT role FROM memberships WHERE organization_id = %s AND actor_id = %s AND revoked_at IS NULL ORDER BY CASE role WHEN 'owner' THEN 1 WHEN 'reviewer' THEN 2 WHEN 'client' THEN 3 ELSE 4 END LIMIT 1",
                    (organization_id, actor),
                )
                membership = cursor.fetchone()
                if membership:
                    role = membership[0]
                if role is None:
                    cursor.execute(
                        "SELECT 1 FROM assignments WHERE work_package_id = %s AND professional_id = %s AND status = 'accepted' AND (expires_at IS NULL OR expires_at > now())",
                        (package_id, actor),
                    )
                    if cursor.fetchone() is None:
                        raise PermissionError("Deliverable access is not authorized")
                    role = "professional"
            query = "SELECT id, work_package_id, version, title, content, submitted_by, status, created_at FROM deliverables WHERE work_package_id = %s"
            params: list[Any] = [package_id]
            if role == "client":
                query += " AND status IN ('approved', 'accepted')"
            query += " ORDER BY version"
            cursor.execute(query, params)
            return [
                {"id": str(row[0]), "work_package_id": str(row[1]), "version": row[2], "title": row[3], "content": row[4], "submitted_by": row[5], "status": row[6], "created_at": row[7]}
                for row in cursor.fetchall()
            ]

    def review_deliverable(self, deliverable_id: UUID, reviewer_id: str, decision: str, comment: str) -> dict[str, Any]:
        with self.transaction() as connection:
            cursor = connection.cursor()
            cursor.execute(
                """SELECT d.work_package_id, d.version, d.title, d.content, d.submitted_by, d.status, e.organization_id
                   FROM deliverables d JOIN work_packages w ON w.id = d.work_package_id
                   JOIN projects p ON p.id = w.project_id JOIN engagements e ON e.id = p.engagement_id
                   WHERE d.id = %s""",
                (deliverable_id,),
            )
            row = cursor.fetchone()
            if row is None:
                raise LookupError("Deliverable not found")
            package_id, version, title, content, submitted_by, current_status, organization_id = row
            if submitted_by == reviewer_id:
                raise ValueError("Independent review is required")
            cursor.execute("SELECT 1 FROM memberships WHERE organization_id = %s AND actor_id = %s AND role IN ('reviewer', 'owner') AND revoked_at IS NULL", (organization_id, reviewer_id))
            if cursor.fetchone() is None:
                raise PermissionError("Reviewer is not authorized for this organization")
            cursor.execute("UPDATE deliverables SET status = %s WHERE id = %s", (decision, deliverable_id))
            cursor.execute("INSERT INTO deliverable_reviews(id, deliverable_id, reviewer_id, decision, comment) VALUES (%s, %s, %s, %s, %s)", (uuid4(), deliverable_id, reviewer_id, decision, comment))
            self._audit(cursor, organization_id, reviewer_id, f"deliverable.{decision}", "deliverable", str(deliverable_id), {"comment": comment})
            return {"id": str(deliverable_id), "work_package_id": str(package_id), "version": version, "title": title, "content": content, "submitted_by": submitted_by, "status": decision, "reviewer": reviewer_id, "comment": comment}

    def accept_deliverable(self, deliverable_id: UUID, client_id: str) -> dict[str, Any]:
        with self.transaction() as connection:
            cursor = connection.cursor()
            cursor.execute(
                """SELECT d.work_package_id, d.version, d.title, d.content, d.submitted_by, d.status, e.organization_id
                   FROM deliverables d JOIN work_packages w ON w.id = d.work_package_id
                   JOIN projects p ON p.id = w.project_id JOIN engagements e ON e.id = p.engagement_id
                   WHERE d.id = %s""",
                (deliverable_id,),
            )
            row = cursor.fetchone()
            if row is None:
                raise LookupError("Deliverable not found")
            package_id, version, title, content, submitted_by, status, organization_id = row
            cursor.execute("SELECT 1 FROM memberships WHERE organization_id = %s AND actor_id = %s AND role = 'client' AND revoked_at IS NULL", (organization_id, client_id))
            if cursor.fetchone() is None:
                raise PermissionError("Client is not authorized for this organization")
            if status != "approved":
                raise ValueError("Only an internally approved deliverable can be accepted")
            cursor.execute("UPDATE deliverables SET status = 'accepted' WHERE id = %s", (deliverable_id,))
            self._audit(cursor, organization_id, client_id, "deliverable.client_accepted", "deliverable", str(deliverable_id))
            return {"id": str(deliverable_id), "work_package_id": str(package_id), "version": version, "title": title, "content": content, "submitted_by": submitted_by, "status": "accepted", "accepted_by": client_id}

    def complete_project(self, project_id: UUID, actor: str) -> dict[str, Any]:
        with self.transaction() as connection:
            cursor = connection.cursor()
            cursor.execute("SELECT e.organization_id, p.status FROM projects p JOIN engagements e ON e.id = p.engagement_id WHERE p.id = %s", (project_id,))
            row = cursor.fetchone()
            if row is None:
                raise LookupError("Project not found")
            organization_id, status = row
            self._require_owner(cursor, organization_id, actor)
            cursor.execute("SELECT 1 FROM deliverables d JOIN work_packages w ON w.id = d.work_package_id WHERE w.project_id = %s AND d.status = 'accepted'", (project_id,))
            if cursor.fetchone() is None:
                raise ValueError("At least one client-accepted deliverable is required")
            cursor.execute("UPDATE projects SET status = 'completed' WHERE id = %s", (project_id,))
            self._audit(cursor, organization_id, actor, "project.completed", "project", str(project_id))
            return {"id": str(project_id), "status": "completed"}

    def revoke_membership(self, organization_id: UUID, actor_id: str, role: str, actor: str) -> None:
        with self.transaction() as connection:
            cursor = connection.cursor()
            self._require_owner(cursor, organization_id, actor)
            cursor.execute(
                "SELECT COUNT(*) FROM memberships WHERE organization_id = %s AND role = 'owner' AND revoked_at IS NULL AND actor_id <> %s",
                (organization_id, actor_id),
            )
            remaining_owners = cursor.fetchone()[0]
            if role == "owner" and remaining_owners == 0:
                raise ValueError("The final organization owner cannot be revoked")
            cursor.execute(
                """UPDATE memberships SET revoked_at = now()
                   WHERE organization_id = %s AND actor_id = %s AND role = %s AND revoked_at IS NULL""",
                (organization_id, actor_id, role),
            )
            if cursor.rowcount != 1:
                raise LookupError("Membership role not found")
            self._audit(cursor, organization_id, actor, "membership.revoked", "organization_membership", f"{actor_id}:{organization_id}")

    def list_audit(self, actor_id: str, admin: bool = False) -> list[dict[str, Any]]:
        with self.transaction() as connection:
            cursor = connection.cursor()
            if admin:
                cursor.execute("SELECT organization_id, actor_id, action, resource_type, resource_id, metadata, created_at FROM audit_events ORDER BY created_at")
            else:
                cursor.execute(
                    """SELECT e.organization_id, e.actor_id, e.action, e.resource_type, e.resource_id, e.metadata, e.created_at
                       FROM audit_events e
                       JOIN memberships m ON m.organization_id = e.organization_id
                       WHERE m.actor_id = %s AND m.revoked_at IS NULL
                       ORDER BY e.created_at""",
                    (actor_id,),
                )
            return [
                {
                    "organization_id": row[0],
                    "actor_id": row[1],
                    "action": row[2],
                    "resource_type": row[3],
                    "resource_id": row[4],
                    "metadata": row[5],
                    "created_at": row[6],
                }
                for row in cursor.fetchall()
            ]

    @staticmethod
    def _require_owner(cursor: Any, organization_id: UUID, actor_id: str) -> None:
        cursor.execute(
            "SELECT 1 FROM memberships WHERE organization_id = %s AND actor_id = %s AND role = 'owner' AND revoked_at IS NULL",
            (organization_id, actor_id),
        )
        if cursor.fetchone() is None:
            raise PermissionError("Organization owner authorization is required")

    @staticmethod
    def _audit(cursor: Any, organization_id: UUID, actor_id: str, action: str, resource_type: str, resource_id: str, metadata: dict[str, Any] | None = None) -> None:
        cursor.execute(
            """INSERT INTO audit_events(id, organization_id, actor_id, action, resource_type, resource_id, metadata)
               VALUES (%s, %s, %s, %s, %s, %s, %s)""",
            (uuid4(), organization_id, actor_id, action, resource_type, resource_id, json.dumps(metadata or {})),
        )
