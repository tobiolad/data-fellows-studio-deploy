"""PostgreSQL persistence primitives for Studio.

The synthetic API intentionally keeps its in-memory store for deterministic
tests. Production startup must select this repository with
``STUDIO_DATABASE_URL`` and run the versioned migrations before accepting
real data. No caller-supplied role or organization is trusted here.
"""

from __future__ import annotations

import hashlib
import json
import os
import secrets
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator
from uuid import UUID, uuid4


from backend.admission import QUALIFICATION_POLICY_VERSION, check_approval

MIGRATIONS_DIR = Path(__file__).resolve().parent.parent / "migrations"

# Seeded in migrations/011_agent_registry.sql; kept as a constant so every
# caller that omits an explicit agent_id resolves to the same registry row
# the previous hardcoded "synthetic-planner-v1" literal represented.
SYNTHETIC_AGENT_ID = UUID("00000000-0000-0000-0000-000000000001")


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
        return psycopg.connect(self.dsn, connect_timeout=5)

    @contextmanager
    def transaction(self) -> Iterator[Any]:
        """Commit a transaction only after the caller exits successfully."""
        connection = self._connect()
        try:
            with connection.transaction():
                yield connection
        finally:
            connection.close()

    def schema_current(self) -> bool:
        expected = {p.name.split("_", 1)[0]: hashlib.sha256(p.read_bytes()).hexdigest() for p in MIGRATIONS_DIR.glob("*.sql")}
        if not expected:
            return False
        with self.transaction() as connection:
            return dict(connection.execute("SELECT version, checksum FROM studio_schema_migrations")) == expected

    def migrate(self) -> None:
        """Apply migrations in lexical order inside one transaction."""
        scripts = sorted(MIGRATIONS_DIR.glob("*.sql"))
        if not scripts:
            raise PersistenceConfigurationError("No Studio migrations were found")
        with self.transaction() as connection:
            cursor = connection.cursor()
            if os.getenv("STUDIO_ENV", "").lower() == "staging":
                from psycopg.conninfo import conninfo_to_dict
                if conninfo_to_dict(self.dsn).get("sslmode") != "verify-full":
                    raise PersistenceConfigurationError("Staging migration requires certificate-verified PostgreSQL")
                cursor.execute("SELECT current_database(), current_user")
                if cursor.fetchone() != ("studio_staging", "studio_migrator"):
                    raise PersistenceConfigurationError("Staging migration requires the dedicated Studio database and migrator")
            cursor.execute("SELECT pg_advisory_xact_lock(hashtext('data-fellows-studio-migrate'))")
            cursor.execute("CREATE TABLE IF NOT EXISTS studio_schema_migrations (version text PRIMARY KEY, checksum text, applied_at timestamptz NOT NULL DEFAULT now())")
            cursor.execute("ALTER TABLE studio_schema_migrations ADD COLUMN IF NOT EXISTS checksum text")
            for script in scripts:
                version = script.name.split("_", 1)[0]
                checksum = hashlib.sha256(script.read_bytes()).hexdigest()
                cursor.execute("SELECT checksum FROM studio_schema_migrations WHERE version = %s", (version,))
                applied = cursor.fetchone()
                if applied:
                    if applied[0] and applied[0] != checksum:
                        raise PersistenceConfigurationError(f"Migration checksum mismatch for {script.name}")
                    if not applied[0]:
                        cursor.execute("UPDATE studio_schema_migrations SET checksum = %s WHERE version = %s", (checksum, version))
                    continue
                cursor.execute(script.read_text(encoding="utf-8"))
                cursor.execute("INSERT INTO studio_schema_migrations(version, checksum) VALUES (%s, %s)", (version, checksum))

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

    def list_organizations(self, actor: str, admin: bool = False) -> list[dict[str, Any]]:
        with self.transaction() as connection:
            cursor = connection.cursor()
            if admin:
                cursor.execute("SELECT id, name, created_at FROM organizations ORDER BY created_at")
            else:
                cursor.execute(
                    """SELECT o.id, o.name, o.created_at FROM organizations o
                       JOIN memberships m ON m.organization_id = o.id
                       WHERE m.actor_id = %s AND m.revoked_at IS NULL
                       ORDER BY o.created_at""",
                    (actor,),
                )
            return [{"id": str(row[0]), "name": row[1], "created_at": row[2]} for row in cursor.fetchall()]

    def grant_membership(self, organization_id: UUID, actor_id: str, role: str, actor: str) -> None:
        with self.transaction() as connection:
            cursor = connection.cursor()
            self._require_owner(cursor, organization_id, actor)
            if role == "professional":
                cursor.execute("""SELECT revoked_at FROM memberships WHERE organization_id=%s AND actor_id=%s
                               AND role='professional' FOR UPDATE""", (organization_id, actor_id))
                previous = cursor.fetchone()
                if previous is None or previous[0] is not None:
                    # Older releases left invitation rows behind after revocation.
                    cursor.execute("""UPDATE assignments a SET status='revoked' FROM work_packages w
                                   JOIN projects p ON p.id=w.project_id JOIN engagements e ON e.id=p.engagement_id
                                   WHERE a.work_package_id=w.id AND e.organization_id=%s AND a.professional_id=%s
                                   AND a.status IN ('accepted','invited')""", (organization_id, actor_id))
            cursor.execute(
                """INSERT INTO memberships(organization_id, actor_id, role)
                   VALUES (%s, %s, %s)
                   ON CONFLICT (organization_id, actor_id, role)
                   DO UPDATE SET revoked_at = NULL""",
                (organization_id, actor_id, role),
            )
            self._audit(cursor, organization_id, actor, "membership.granted", "organization_membership", f"{actor_id}:{organization_id}")

    def list_memberships(self, organization_id: UUID, actor: str, admin: bool = False) -> list[dict[str, Any]]:
        with self.transaction() as connection:
            cursor = connection.cursor()
            if not admin:
                cursor.execute("SELECT 1 FROM memberships WHERE organization_id = %s AND actor_id = %s AND role = 'owner' AND revoked_at IS NULL", (organization_id, actor))
                if cursor.fetchone() is None:
                    raise PermissionError("Only an organization owner may view the membership roster")
            cursor.execute(
                "SELECT actor_id, role, created_at, revoked_at FROM memberships WHERE organization_id = %s AND revoked_at IS NULL ORDER BY actor_id, role",
                (organization_id,),
            )
            return [{"actor_id": row[0], "role": row[1], "created_at": row[2], "revoked_at": row[3]} for row in cursor.fetchall()]

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
                    """SELECT DISTINCT e.id, e.organization_id, e.name, e.objective, e.status, e.created_at
                       FROM engagements e
                       JOIN memberships m ON m.organization_id = e.organization_id
                       WHERE m.actor_id = %s AND m.revoked_at IS NULL AND
                           (m.role IN ('client','owner','reviewer') OR EXISTS
                           (SELECT 1 FROM studio_current_assignments a WHERE a.engagement_id=e.id AND a.professional_id=m.actor_id AND a.status='accepted'))
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

    def admin_overview(self, actor: str) -> dict[str, Any]:
        """Read-only operational summary for the internal Mission Control UI."""
        with self.transaction() as connection:
            cursor = connection.cursor()
            cursor.execute("SELECT id, name, created_at FROM organizations ORDER BY created_at DESC")
            organizations = [{"id": str(row[0]), "name": row[1], "created_at": row[2]} for row in cursor.fetchall()]
            cursor.execute("""SELECT e.id, e.organization_id, e.name, e.objective, e.status, e.created_at, o.name
                            FROM engagements e JOIN organizations o ON o.id = e.organization_id ORDER BY e.created_at DESC""")
            engagements = [{"id": str(row[0]), "organization_id": str(row[1]), "name": row[2], "objective": row[3], "status": row[4], "created_at": row[5], "organization_name": row[6]} for row in cursor.fetchall()]
            cursor.execute("""SELECT p.id, p.engagement_id, p.name, p.status, p.created_at, e.name, o.name,
                                   COUNT(DISTINCT w.id), COUNT(DISTINCT d.id), COUNT(DISTINCT CASE WHEN d.status = 'under_review' THEN d.id END)
                            FROM projects p JOIN engagements e ON e.id = p.engagement_id JOIN organizations o ON o.id = e.organization_id
                            LEFT JOIN work_packages w ON w.project_id = p.id LEFT JOIN deliverables d ON d.work_package_id = w.id
                            GROUP BY p.id, e.name, o.name ORDER BY p.created_at DESC""")
            projects = [{"id": str(row[0]), "engagement_id": str(row[1]), "name": row[2], "status": row[3], "created_at": row[4], "engagement_name": row[5], "organization_name": row[6], "work_package_count": row[7], "deliverable_count": row[8], "awaiting_review": row[9]} for row in cursor.fetchall()]
            cursor.execute("SELECT a.professional_id, a.status, a.decided_by, a.decided_at, a.created_at, a.reviewed_at, a.decision_reason, a.missing_information, a.assessment_requests, a.next_action, p.display_name FROM professional_admissions a LEFT JOIN professional_profiles p ON p.professional_id = a.professional_id ORDER BY a.created_at DESC")
            applications = [{"display_name": row[10], "professional_id": row[0], "status": row[1], "decided_by": row[2], "decided_at": row[3], "created_at": row[4], "reviewed_at": row[5], "decision_reason": row[6], "missing_information": row[7], "assessment_requests": row[8], "next_action": row[9]} for row in cursor.fetchall()]
            cursor.execute("SELECT id, title, summary, specialization, skills, compensation, deadline, status, created_at FROM opportunities WHERE status = 'published' ORDER BY created_at DESC")
            opportunities = [{"id": str(row[0]), "title": row[1], "summary": row[2], "specialization": row[3], "skills": row[4], "compensation": row[5], "deadline": row[6], "status": row[7], "created_at": row[8]} for row in cursor.fetchall()]
            cursor.execute("""SELECT d.id, d.work_package_id, d.version, d.title, d.submitted_by, d.status, d.created_at, p.name, e.name, o.name
                            FROM deliverables d JOIN work_packages w ON w.id = d.work_package_id JOIN projects p ON p.id = w.project_id
                            JOIN engagements e ON e.id = p.engagement_id JOIN organizations o ON o.id = e.organization_id ORDER BY d.created_at DESC""")
            deliverables = [{"id": str(row[0]), "work_package_id": str(row[1]), "version": row[2], "title": row[3], "submitted_by": row[4], "status": row[5], "created_at": row[6], "project_name": row[7], "engagement_name": row[8], "organization_name": row[9]} for row in cursor.fetchall()]
            cursor.execute("""SELECT r.id, r.work_package_id, r.requested_by, r.agent_version, r.policy_version, r.budget_cents,
                                   r.spent_cents, r.status, r.cancel_requested, r.error_code, r.created_at, w.title, p.name, e.name
                            FROM ai_runs r JOIN work_packages w ON w.id = r.work_package_id JOIN projects p ON p.id = w.project_id
                            JOIN engagements e ON e.id = p.engagement_id ORDER BY r.created_at DESC""")
            ai_runs = [{"id": str(row[0]), "work_package_id": str(row[1]), "requested_by": row[2], "agent_version": row[3], "policy_version": row[4], "budget_cents": row[5], "spent_cents": row[6], "status": row[7], "cancel_requested": row[8], "error_code": row[9], "created_at": row[10], "work_package_title": row[11], "project_name": row[12], "engagement_name": row[13]} for row in cursor.fetchall()]
            cursor.execute("SELECT run_id, status FROM artifacts WHERE version = (SELECT MAX(a2.version) FROM artifacts a2 WHERE a2.run_id = artifacts.run_id)")
            artifact_status = {str(row[0]): row[1] for row in cursor.fetchall()}
            for run in ai_runs:
                run["artifact_status"] = artifact_status.get(run["id"])
            cursor.execute("SELECT organization_id, actor_id, action, resource_type, resource_id, metadata, created_at FROM audit_events ORDER BY created_at DESC LIMIT 25")
            audit = [{"organization_id": None if row[0] is None else str(row[0]), "actor_id": row[1], "action": row[2], "resource_type": row[3], "resource_id": row[4], "metadata": row[5], "created_at": row[6]} for row in cursor.fetchall()]
            cursor.execute("SELECT COUNT(*) FROM artifacts WHERE status = 'pending_review'")
            pending_ai_approvals = int(cursor.fetchone()[0])
            metrics = {
                "active_engagements": sum(item["status"] in {"authorized", "active"} for item in engagements),
                "projects_awaiting_kickoff": sum(item["status"] == "active" and item["work_package_count"] == 0 for item in projects),
                "active_projects": sum(item["status"] == "active" for item in projects),
                "awaiting_review": sum(item["status"] == "under_review" for item in deliverables),
                "client_approvals_pending": sum(item["status"] == "approved" for item in deliverables),
                "pending_applications": sum(item["status"] in {"pending", "submitted", "under_review", "assessment"} for item in applications),
                "open_opportunities": len(opportunities),
                "active_assignments": self._count_active_assignments(cursor),
                "ai_pending_approval": pending_ai_approvals,
                "ai_failed": sum(item["status"] == "failed" for item in ai_runs),
            }
            return {"organizations": organizations, "engagements": engagements, "projects": projects, "applications": applications, "professionals": applications, "opportunities": opportunities, "deliverables": deliverables, "ai_runs": ai_runs, "audit": audit, "metrics": metrics}

    def _project_context(self, cursor: Any, project_id: UUID, actor: str, admin: bool = False) -> tuple[UUID, set[str]]:
        cursor.execute(
            "SELECT e.organization_id FROM projects p JOIN engagements e ON e.id = p.engagement_id WHERE p.id = %s",
            (project_id,),
        )
        row = cursor.fetchone()
        if row is None:
            raise LookupError("Project not found")
        organization_id = row[0]
        if admin:
            return organization_id, {"admin"}
        cursor.execute(
            "SELECT role FROM memberships WHERE organization_id = %s AND actor_id = %s AND revoked_at IS NULL",
            (organization_id, actor),
        )
        roles = {item[0] for item in cursor.fetchall()}
        cursor.execute(
            """SELECT 1 FROM studio_current_assignments a
               WHERE a.project_id = %s AND a.professional_id = %s AND a.status = 'accepted'
                 AND (a.expires_at IS NULL OR a.expires_at > now())""",
            (project_id, actor),
        )
        roles.discard("professional")
        if cursor.fetchone() is not None:
            roles.add("professional")
        if not roles.intersection({"owner", "reviewer", "client", "professional"}):
            raise PermissionError("Project access is not authorized")
        return organization_id, roles

    def project_coordination(self, project_id, actor, admin):
        with self.transaction() as connection:
            cursor = connection.cursor()
            _, roles = self._project_context(cursor, project_id, actor, admin)
            if not roles.intersection({"admin", "client", "owner"}):
                raise PermissionError("Client project coordination access is required")
            cursor.execute("""SELECT id, project_id, subject, created_at, decision, rationale, decided_at
                           FROM project_requests WHERE project_id=%s ORDER BY created_at DESC, id""", (project_id,))
            requests = [dict(zip(("id", "project_id", "subject", "created_at", "decision", "rationale", "decided_at"), row))
                        for row in cursor.fetchall()]
            cursor.execute("SELECT versions, created_at FROM project_handovers WHERE project_id=%s", (project_id,))
            handover = cursor.fetchone()
            return {"requests": requests, "handover": dict(zip(("versions", "created_at"), handover)) if handover else None}

    def open_project_request(self, project_id, actor, subject):
        with self.transaction() as connection:
            cursor = connection.cursor()
            org, roles = self._project_context(cursor, project_id, actor)
            if "client" not in roles:
                raise PermissionError("Client membership is required")
            key = uuid4()
            cursor.execute("INSERT INTO project_requests(id, project_id, subject, requested_by) VALUES (%s,%s,%s,%s)",
                           (key, project_id, subject, actor))
            cursor.execute("""INSERT INTO notifications(id, project_id, recipient_group, kind, title, body)
                           VALUES (%s,%s,'internal','project.request.opened','Client request','A client request needs a decision.')""",
                           (uuid4(), project_id))
            self._audit(cursor, org, actor, "project.request.opened", "project_request", str(key))
            return {"id": key}

    def decide_project_request(self, project_id, request_id, actor, decision, rationale):
        with self.transaction() as connection:
            cursor = connection.cursor()
            org, _ = self._project_context(cursor, project_id, actor, admin=True)
            cursor.execute("SELECT decision FROM project_requests WHERE project_id=%s AND id=%s FOR UPDATE", (project_id, request_id))
            row = cursor.fetchone()
            if row is None:
                raise LookupError("Project request not found")
            if row[0]:
                raise ValueError("A decision has already been recorded")
            cursor.execute("UPDATE project_requests SET decision=%s,rationale=%s,decided_by=%s,decided_at=now() WHERE id=%s",
                           (decision, rationale, actor, request_id))
            cursor.execute("""INSERT INTO notifications(id, project_id, recipient_group, kind, title, body)
                           VALUES (%s,%s,'client','project.request.decided','Request decision','Data Fellows responded to a request.')""",
                           (uuid4(), project_id))
            self._audit(cursor, org, actor, "project.request.decided", "project_request", str(request_id))
            return {"id": request_id, "decision": decision}

    def list_project_messages(self, project_id: UUID, actor: str, admin: bool = False) -> list[dict[str, Any]]:
        with self.transaction() as connection:
            cursor = connection.cursor()
            _organization_id, roles = self._project_context(cursor, project_id, actor, admin)
            cursor.execute(
                "SELECT id, project_id, sender_id, recipient_group, body, created_at FROM project_messages WHERE project_id = %s ORDER BY created_at",
                (project_id,),
            )
            internal = admin or bool(roles.intersection({"owner", "reviewer"}))
            allowed_groups = set()
            if "client" in roles:
                allowed_groups.add("client")
            if "professional" in roles:
                allowed_groups.add("professional")
            if not roles.intersection({"client", "professional"}):
                allowed_groups = {"client", "professional", "internal"}
            return [
                {"id": str(row[0]), "project_id": str(row[1]), "sender_id": row[2], "recipient_group": row[3], "body": row[4], "created_at": row[5]}
                for row in cursor.fetchall()
                if internal or row[2] == actor or row[3] in allowed_groups
            ]

    def send_project_message(self, project_id: UUID, actor: str, body: str, recipient_group: str, admin: bool = False) -> dict[str, Any]:
        message_id = uuid4()
        with self.transaction() as connection:
            cursor = connection.cursor()
            organization_id, roles = self._project_context(cursor, project_id, actor, admin)
            if not admin and roles.intersection({"client", "professional"}) and recipient_group != "internal":
                raise PermissionError("Clients and professionals may only message Data Fellows internally")
            cursor.execute(
                "INSERT INTO project_messages(id, project_id, sender_id, recipient_group, body) VALUES (%s, %s, %s, %s, %s)",
                (message_id, project_id, actor, recipient_group, body),
            )
            notification_id = uuid4()
            cursor.execute(
                "INSERT INTO notifications(id, project_id, recipient_group, kind, title, body) VALUES (%s, %s, %s, 'project.message', 'New project message', 'A new message is available in the project workspace.')",
                (notification_id, project_id, recipient_group),
            )
            self._audit(cursor, organization_id, actor, "project.message.sent", "project_message", str(message_id))
            return {"id": str(message_id), "project_id": str(project_id), "sender_id": actor, "recipient_group": recipient_group, "body": body}

    def list_project_documents(self, project_id: UUID, actor: str, admin: bool = False) -> list[dict[str, Any]]:
        with self.transaction() as connection:
            cursor = connection.cursor()
            _organization_id, roles = self._project_context(cursor, project_id, actor, admin)
            cursor.execute(
                "SELECT id, project_id, name, description, classification, storage_reference, created_by, created_at FROM project_documents WHERE project_id = %s ORDER BY created_at",
                (project_id,),
            )
            hide_reference = not (admin or roles.intersection({"owner", "reviewer"}))
            results = []
            for row in cursor.fetchall():
                if row[4] == "support" and roles.intersection({"client", "professional"}):
                    continue
                record = {"id": str(row[0]), "project_id": str(row[1]), "name": row[2], "description": row[3], "classification": row[4], "created_by": row[6], "created_at": row[7]}
                if not hide_reference:
                    record["storage_reference"] = row[5]
                results.append(record)
            return results

    def create_project_document(self, project_id: UUID, actor: str, document: dict[str, Any], admin: bool = False) -> dict[str, Any]:
        document_id = uuid4()
        with self.transaction() as connection:
            cursor = connection.cursor()
            organization_id, roles = self._project_context(cursor, project_id, actor, admin)
            if not admin and "owner" not in roles:
                raise PermissionError("Only a Data Fellows owner may add project documents")
            cursor.execute(
                "INSERT INTO project_documents(id, project_id, name, description, classification, storage_reference, created_by) VALUES (%s, %s, %s, %s, %s, %s, %s)",
                (document_id, project_id, document["name"], document.get("description", ""), document["classification"], document["storage_reference"], actor),
            )
            self._audit(cursor, organization_id, actor, "project.document.added", "project_document", str(document_id))
            return {"id": str(document_id), "project_id": str(project_id), "name": document["name"], "description": document.get("description", ""), "classification": document["classification"], "created_by": actor}

    def project_activity(self, project_id: UUID, actor: str, admin: bool = False) -> list[dict[str, Any]]:
        with self.transaction() as connection:
            cursor = connection.cursor()
            organization_id, roles = self._project_context(cursor, project_id, actor, admin)
            if not admin and not roles.intersection({"owner", "reviewer"}):
                cursor.execute("""SELECT action, created_at FROM audit_events WHERE organization_id=%s
                           AND resource_type='project' AND resource_id=%s AND action IN ('project.created','project.completed')
                           ORDER BY created_at DESC""", (organization_id, str(project_id)))
                return [{"action": action, "created_at": when} for action, when in cursor.fetchall()]
            cursor.execute("SELECT id FROM work_packages WHERE project_id = %s", (project_id,))
            package_ids = [str(row[0]) for row in cursor.fetchall()]
            resource_ids = [str(project_id), *package_ids]
            if package_ids:
                cursor.execute("SELECT id FROM assignments WHERE work_package_id = ANY(%s::uuid[])", (package_ids,))
                resource_ids.extend(str(row[0]) for row in cursor.fetchall())
                cursor.execute("SELECT id FROM deliverables WHERE work_package_id = ANY(%s::uuid[])", (package_ids,))
                resource_ids.extend(str(row[0]) for row in cursor.fetchall())
                cursor.execute("SELECT id FROM ai_runs WHERE work_package_id = ANY(%s::uuid[])", (package_ids,))
                resource_ids.extend(str(row[0]) for row in cursor.fetchall())
            cursor.execute("SELECT id FROM project_messages WHERE project_id = %s UNION ALL SELECT id FROM project_documents WHERE project_id = %s", (project_id, project_id))
            resource_ids.extend(str(row[0]) for row in cursor.fetchall())
            cursor.execute(
                "SELECT organization_id, actor_id, action, resource_type, resource_id, metadata, created_at FROM audit_events WHERE organization_id = %s AND resource_id = ANY(%s::text[]) ORDER BY created_at DESC",
                (organization_id, resource_ids),
            )
            return [
                {"organization_id": str(row[0]), "actor_id": row[1], "action": row[2], "resource_type": row[3], "resource_id": row[4], "metadata": row[5], "created_at": row[6]}
                for row in cursor.fetchall()
                if admin or not roles.intersection({"client", "professional"}) or row[3] not in {"ai_run", "ai_artifact"}
            ]

    def list_notifications(self, actor: str, admin: bool = False) -> list[dict[str, Any]]:
        with self.transaction() as connection:
            cursor = connection.cursor()
            if admin:
                cursor.execute("SELECT id, project_id, recipient_group, kind, title, body, read_at, created_at FROM notifications ORDER BY created_at DESC")
            else:
                cursor.execute(
                    """SELECT DISTINCT n.id, n.project_id, n.recipient_group, n.kind, n.title, n.body, n.read_at, n.created_at
                       FROM notifications n JOIN projects p ON p.id = n.project_id
                       JOIN engagements e ON e.id = p.engagement_id
                       JOIN memberships m ON m.organization_id = e.organization_id
                       WHERE m.actor_id = %s AND m.revoked_at IS NULL
                         AND (m.role <> 'professional' OR EXISTS (SELECT 1 FROM studio_current_assignments a
                             WHERE a.project_id=n.project_id AND a.professional_id=m.actor_id AND a.status='accepted'))
                         AND (n.recipient_group = m.role OR (n.recipient_group = 'internal' AND m.role IN ('owner', 'reviewer')))
                       ORDER BY n.created_at DESC""",
                    (actor,),
                )
            return [{"id": str(row[0]), "project_id": None if row[1] is None else str(row[1]), "recipient_group": row[2], "kind": row[3], "title": row[4], "body": row[5], "read_at": row[6], "created_at": row[7]} for row in cursor.fetchall()]

    @staticmethod
    def _count_active_assignments(cursor: Any) -> int:
        cursor.execute("SELECT COUNT(*) FROM studio_current_assignments WHERE status = 'accepted' AND (expires_at IS NULL OR expires_at > now())")
        return int(cursor.fetchone()[0])

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
            cursor.execute("""SELECT 1 FROM memberships WHERE organization_id=%s AND actor_id=%s
                              AND revoked_at IS NULL AND role IN ('owner','reviewer','client')""", (organization_id, actor))
            broad = admin or cursor.fetchone() is not None
            cursor.execute("""SELECT id, engagement_id, name, status, created_at FROM projects p
                WHERE engagement_id=%s AND (%s OR EXISTS (SELECT 1 FROM studio_current_assignments a
                    WHERE a.project_id=p.id AND a.professional_id=%s AND a.status='accepted')) ORDER BY created_at""",
                (engagement_id, broad, actor))
            rows = cursor.fetchall()
            if not broad and not rows:
                raise PermissionError("Project access is not authorized")
            return [
                {"id": str(row[0]), "engagement_id": str(row[1]), "name": row[2], "status": row[3], "created_at": row[4]}
                for row in rows
            ]

    def client_overview(self, actor: str) -> dict[str, Any]:
        """Build a client-safe read model from active client memberships only."""
        with self.transaction() as connection:
            cursor = connection.cursor()
            cursor.execute(
                """SELECT o.id, o.name, o.created_at
                   FROM organizations o JOIN memberships m ON m.organization_id = o.id
                   WHERE m.actor_id = %s AND m.role = 'client' AND m.revoked_at IS NULL
                   ORDER BY o.created_at""",
                (actor,),
            )
            organizations = [{"id": str(row[0]), "name": row[1], "created_at": row[2]} for row in cursor.fetchall()]
            organization_ids = [item["id"] for item in organizations]
            if not organization_ids:
                raise PermissionError("An active client membership is required")
            cursor.execute(
                """SELECT e.id, e.organization_id, e.name, e.objective, e.status, e.created_at, o.name
                   FROM engagements e JOIN organizations o ON o.id = e.organization_id
                   WHERE e.organization_id = ANY(%s::uuid[]) ORDER BY e.created_at""",
                (organization_ids,),
            )
            engagements = [{"id": str(row[0]), "organization_id": str(row[1]), "name": row[2], "objective": row[3], "status": row[4], "created_at": row[5], "organization_name": row[6]} for row in cursor.fetchall()]
            engagement_ids = [item["id"] for item in engagements]
            if not engagement_ids:
                return {"organizations": organizations, "engagements": [], "projects": [], "deliverables": [], "metrics": {"active_projects": 0, "completed_projects": 0, "deliverables_for_review": 0, "accepted_deliverables": 0}}
            cursor.execute(
                """SELECT p.id, p.engagement_id, p.name, p.status, p.created_at, e.name, o.name
                   FROM projects p JOIN engagements e ON e.id = p.engagement_id JOIN organizations o ON o.id = e.organization_id
                   WHERE p.engagement_id = ANY(%s::uuid[]) ORDER BY p.created_at""",
                (engagement_ids,),
            )
            project_rows = cursor.fetchall()
            projects: list[dict[str, Any]] = []
            deliverables: list[dict[str, Any]] = []
            for row in project_rows:
                project = {"id": str(row[0]), "engagement_id": str(row[1]), "name": row[2], "status": row[3], "created_at": row[4], "engagement_name": row[5], "organization_name": row[6], "work_packages": []}
                cursor.execute("SELECT id, title, acceptance_criteria, status, created_at FROM work_packages WHERE project_id = %s ORDER BY created_at", (row[0],))
                for package_row in cursor.fetchall():
                    cursor.execute(
                        """SELECT id, work_package_id, version, title, content, status, created_at
                           FROM deliverables WHERE work_package_id = %s AND status IN ('approved', 'accepted') ORDER BY version""",
                        (package_row[0],),
                    )
                    versions = [{"id": str(item[0]), "work_package_id": str(item[1]), "version": item[2], "title": item[3], "content": item[4], "status": item[5], "created_at": item[6]} for item in cursor.fetchall()]
                    deliverables.extend(versions)
                    project["work_packages"].append({"id": str(package_row[0]), "project_id": str(row[0]), "title": package_row[1], "acceptance_criteria": package_row[2], "status": package_row[3], "created_at": package_row[4], "deliverables": versions})
                projects.append(project)
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
            _, roles = self._project_context(cursor, project_id, actor, admin)
            broad = bool(roles.intersection({"admin", "owner", "reviewer", "client"}))
            cursor.execute("""SELECT id, project_id, title, acceptance_criteria, status, created_at FROM work_packages w
                WHERE project_id=%s AND (%s OR EXISTS (SELECT 1 FROM studio_current_assignments a
                WHERE a.work_package_id=w.id AND a.professional_id=%s AND a.status='accepted')) ORDER BY created_at""",
                (project_id, broad, actor))
            result = []
            for row in cursor.fetchall():
                cursor.execute("SELECT depends_on_id FROM work_package_dependencies WHERE work_package_id = %s ORDER BY depends_on_id", (row[0],))
                result.append({"id": str(row[0]), "project_id": str(row[1]), "title": row[2], "acceptance_criteria": row[3], "status": row[4], "created_at": row[5], "depends_on": [str(item[0]) for item in cursor.fetchall()]})
            return result

    def submit_professional_application(self, professional_id: str, actor: str) -> None:
        with self.transaction() as connection:
            cursor = connection.cursor()
            cursor.execute(
                """INSERT INTO professional_admissions(professional_id, status, submitted_at)
                   VALUES (%s, 'submitted', now())
                   ON CONFLICT (professional_id) DO NOTHING RETURNING professional_id""",
                (professional_id,),
            )
            if cursor.fetchone() is None:
                cursor.execute("SELECT status FROM professional_admissions WHERE professional_id = %s FOR SHARE", (professional_id,))
                if cursor.fetchone()[0] != "submitted":
                    raise ValueError("An application already exists. Update the current profile or contact admission staff.")
                return
            self._audit(cursor, None, actor, "professional.application_submitted", "professional", professional_id)

    def get_professional_application(self, professional_id: str) -> dict[str, Any] | None:
        with self.transaction() as connection:
            cursor = connection.cursor()
            cursor.execute("""SELECT professional_id, status, decided_by, decided_at, created_at,
                                    submitted_at, reviewed_at, decision_reason, missing_information,
                                    assessment_requests, evidence_references, next_action
                             FROM professional_admissions WHERE professional_id = %s""", (professional_id,))
            row = cursor.fetchone()
            if row is None:
                return None
            return {"professional_id": row[0], "status": row[1], "decided_by": row[2], "decided_at": row[3], "created_at": row[4],
                    "submitted_at": row[5], "reviewed_at": row[6], "decision_reason": row[7],
                    "missing_information": row[8], "assessment_requests": row[9],
                    "evidence_references": row[10], "next_action": row[11]}

    def admission_history(self, professional_id: str) -> list[dict]:
        with self.transaction() as connection:
            cursor = connection.cursor()
            cursor.execute("""SELECT action, actor_id, created_at, metadata FROM audit_events WHERE resource_id=%s
                AND resource_type IN ('professional','professional_admission') ORDER BY created_at DESC, id DESC""", (professional_id,))
            return [{"action": action, "reviewer": actor, "created_at": when, **metadata} for action, actor, when, metadata in cursor.fetchall()]

    def get_professional_profile(self, professional_id: str) -> dict[str, Any] | None:
        with self.transaction() as connection:
            cursor = connection.cursor()
            cursor.execute("SELECT status FROM professional_admissions WHERE professional_id = %s", (professional_id,))
            admission = cursor.fetchone()
            if admission is None:
                raise LookupError("Professional application not found")
            cursor.execute(
                """SELECT professional_id, display_name, headline, bio, skills, specializations,
                          education, experience, portfolio, availability, evidence_references, version, updated_at
                   FROM professional_profiles WHERE professional_id = %s""",
                (professional_id,),
            )
            row = cursor.fetchone()
            if row is None:
                return None
            return {
                "professional_id": row[0], "display_name": row[1], "headline": row[2], "bio": row[3],
                "skills": row[4], "specializations": row[5], "education": row[6], "experience": row[7],
                "portfolio": row[8], "availability": row[9], "evidence_references": row[10], "version": row[11], "updated_at": row[12],
                "application_status": admission[0],
            }

    def upsert_professional_profile(self, professional_id: str, payload: dict[str, Any], actor: str, expected_version: int | None = None) -> dict[str, Any]:
        with self.transaction() as connection:
            cursor = connection.cursor()
            cursor.execute("SELECT status FROM professional_admissions WHERE professional_id = %s FOR UPDATE", (professional_id,))
            admission = cursor.fetchone()
            if admission is None:
                raise LookupError("Submit a professional application before editing a profile")
            cursor.execute("SELECT version FROM professional_profiles WHERE professional_id = %s", (professional_id,))
            current = cursor.fetchone()
            current_version = int(current[0]) if current else 0
            if expected_version is not None and expected_version != current_version:
                raise ValueError("Profile changed since it was loaded; refresh before saving")
            version = current_version + 1
            cursor.execute(
                """INSERT INTO professional_profiles
                   (professional_id, display_name, headline, bio, skills, specializations, education, experience, portfolio, availability, evidence_references, version, updated_at)
                   VALUES (%s, %s, %s, %s, %s::jsonb, %s::jsonb, %s::jsonb, %s::jsonb, %s::jsonb, %s, %s::jsonb, %s, now())
                   ON CONFLICT (professional_id) DO UPDATE SET display_name = EXCLUDED.display_name,
                     headline = EXCLUDED.headline, bio = EXCLUDED.bio, skills = EXCLUDED.skills,
                     specializations = EXCLUDED.specializations, education = EXCLUDED.education,
                     experience = EXCLUDED.experience, portfolio = EXCLUDED.portfolio,
                     availability = EXCLUDED.availability, evidence_references = EXCLUDED.evidence_references,
                     version = EXCLUDED.version, updated_at = now()""",
                (professional_id, payload["display_name"], payload.get("headline", ""), payload.get("bio", ""),
                 json.dumps(payload.get("skills", [])), json.dumps(payload.get("specializations", [])),
                 json.dumps(payload.get("education", [])), json.dumps(payload.get("experience", [])),
                 json.dumps(payload.get("portfolio", [])), payload.get("availability", ""),
                 json.dumps(payload.get("evidence_references", [])), version),
            )
            self._audit(cursor, None, actor, "professional_profile.updated", "professional_profile", professional_id, {"version": version})
            return {**payload, "professional_id": professional_id, "version": version, "application_status": admission[0]}

    def review_professional_admission(self, professional_id: str, review: dict[str, Any], actor: str) -> dict[str, Any]:
        """Record an independent admission review with explicit, auditable state."""
        with self.transaction() as connection:
            cursor = connection.cursor()
            cursor.execute("SELECT status, missing_information, assessment_requests FROM professional_admissions WHERE professional_id = %s FOR UPDATE", (professional_id,))
            existing = cursor.fetchone()
            if existing is None:
                raise LookupError("Professional application not found")
            verified_evidence = []
            if review["status"] == "approved":
                cursor.execute("SELECT version, skills, evidence_references FROM professional_profiles WHERE professional_id = %s FOR SHARE", (professional_id,))
                row = cursor.fetchone()
                profile = dict(zip(("version", "skills", "evidence_references"), row)) if row else None
                application = dict(zip(("status", "missing_information", "assessment_requests"), existing))
                verified_evidence = check_approval(application, profile, review, professional_id, actor)
            if existing[0] != "approved" or review["status"] != "approved":
                cursor.execute("UPDATE assignments SET status='revoked' WHERE professional_id=%s AND status IN ('invited','accepted')", (professional_id,))
            terminal = review["status"] in {"approved", "declined", "revoked"}
            cursor.execute(
                """UPDATE professional_admissions
                   SET status = %s, reviewed_at = now(),
                       decided_by = CASE WHEN %s THEN %s ELSE decided_by END,
                       decided_at = CASE WHEN %s THEN now() ELSE decided_at END,
                       decision_reason = %s, missing_information = %s::jsonb,
                       assessment_requests = %s::jsonb, next_action = %s
                   WHERE professional_id = %s
                   RETURNING professional_id, status, decided_by, decided_at, created_at,
                             submitted_at, reviewed_at, decision_reason, missing_information,
                             assessment_requests, evidence_references, next_action""",
                (review["status"], terminal, actor, terminal, review.get("reason", ""),
                 json.dumps(review.get("missing_information", [])), json.dumps(review.get("assessment_requests", [])),
                 review.get("next_action", ""), professional_id),
            )
            row = cursor.fetchone()
            self._audit(cursor, None, actor, f"professional.admission_{review['status']}", "professional_admission", professional_id,
                        {"verified_evidence": verified_evidence, "policy_version": QUALIFICATION_POLICY_VERSION, "previous_status": existing[0], "reason": review.get("reason", ""), "reviewed_profile_version": review.get("reviewed_profile_version"), "missing_information_count": len(review.get("missing_information", []))})
            return {"professional_id": row[0], "status": row[1], "decided_by": row[2], "decided_at": row[3], "created_at": row[4],
                    "submitted_at": row[5], "reviewed_at": row[6], "decision_reason": row[7], "missing_information": row[8],
                    "assessment_requests": row[9], "evidence_references": row[10], "next_action": row[11]}

    def list_professional_admissions(self, status: str | None = None) -> list[dict[str, Any]]:
        with self.transaction() as connection:
            cursor = connection.cursor()
            if status:
                cursor.execute(
                    """SELECT professional_id, status, decided_by, decided_at, created_at, reviewed_at,
                                      decision_reason, missing_information, assessment_requests, next_action
                       FROM professional_admissions WHERE status = %s ORDER BY created_at, professional_id""",
                    (status,),
                )
            else:
                cursor.execute(
                    """SELECT professional_id, status, decided_by, decided_at, created_at, reviewed_at,
                                      decision_reason, missing_information, assessment_requests, next_action
                       FROM professional_admissions ORDER BY created_at, professional_id"""
                )
            return [
                {"professional_id": row[0], "status": row[1], "decided_by": row[2], "decided_at": row[3], "created_at": row[4],
                 "reviewed_at": row[5], "decision_reason": row[6], "missing_information": row[7],
                 "assessment_requests": row[8], "next_action": row[9]}
                for row in cursor.fetchall()
            ]

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
            cursor.execute("SELECT 1 FROM professional_admissions WHERE professional_id = %s AND status = 'approved' FOR SHARE", (professional_id,))
            if cursor.fetchone() is None:
                raise ValueError("Professional approval is required before assignment")
            cursor.execute(
                "SELECT 1 FROM memberships WHERE organization_id = %s AND actor_id = %s AND role = 'professional' AND revoked_at IS NULL FOR SHARE",
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
                   WHERE a.id = %s AND a.professional_id = %s FOR UPDATE OF a""",
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
            cursor.execute("SELECT 1 FROM studio_current_assignments WHERE id=%s", (assignment_id,))
            if cursor.fetchone() is None:
                raise ValueError("Assignment access is no longer active")
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
                   WHERE a.id = %s AND a.professional_id = %s FOR UPDATE OF a""",
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
                """SELECT a.id, a.work_package_id, a.professional_id, a.status, a.expires_at, a.created_at,
                          w.title, p.name, e.name, e.objective, p.id
                   FROM assignments a
                   JOIN work_packages w ON w.id = a.work_package_id
                   JOIN projects p ON p.id = w.project_id
                   JOIN engagements e ON e.id = p.engagement_id
                   WHERE a.professional_id = %s AND (%s OR EXISTS
                     (SELECT 1 FROM studio_current_assignments v WHERE v.id=a.id))
                   ORDER BY a.created_at DESC""",
                (professional_id, admin),
            )
            return [
                {"id": str(row[0]), "work_package_id": str(row[1]), "professional_id": row[2], "status": row[3], "expires_at": row[4], "created_at": row[5], "title": row[6], "project_name": row[7], "engagement_name": row[8], "objective": row[9], "project_id": str(row[10])}
                for row in cursor.fetchall()
            ]

    def create_opportunity(self, title: str, summary: str, specialization: str, skills: list[str], compensation: str | None, deadline: datetime | None, actor: str) -> UUID:
        opportunity_id = uuid4()
        with self.transaction() as connection:
            cursor = connection.cursor()
            cursor.execute(
                """INSERT INTO opportunities(id, title, summary, specialization, skills, compensation, deadline, status, created_by)
                   VALUES (%s, %s, %s, %s, %s, %s, %s, 'published', %s)""",
                (opportunity_id, title, summary, specialization, json.dumps(skills), compensation, deadline, actor),
            )
        return opportunity_id

    def list_opportunities(self, professional_id: str, admin: bool = False) -> list[dict[str, Any]]:
        with self.transaction() as connection:
            cursor = connection.cursor()
            if not admin:
                cursor.execute("SELECT 1 FROM professional_admissions WHERE professional_id = %s AND status = 'approved' FOR SHARE", (professional_id,))
                if cursor.fetchone() is None:
                    raise PermissionError("Professional approval is required to view opportunities")
            cursor.execute("SELECT id, title, summary, specialization, skills, compensation, deadline, status, created_at FROM opportunities WHERE status = 'published' ORDER BY created_at DESC")
            rows = cursor.fetchall()
            results = []
            for row in rows:
                cursor.execute("SELECT id, status FROM opportunity_interests WHERE opportunity_id = %s AND professional_id = %s", (row[0], professional_id))
                interest = cursor.fetchone()
                results.append({"id": str(row[0]), "title": row[1], "summary": row[2], "specialization": row[3], "skills": row[4], "compensation": row[5], "deadline": row[6], "status": row[7], "created_at": row[8], "interest_id": None if interest is None else str(interest[0]), "interest_status": None if interest is None else interest[1]})
            return results

    def express_interest(self, opportunity_id: UUID, professional_id: str, approach: str) -> UUID:
        interest_id = uuid4()
        with self.transaction() as connection:
            cursor = connection.cursor()
            cursor.execute("SELECT 1 FROM professional_admissions WHERE professional_id = %s AND status = 'approved' FOR SHARE", (professional_id,))
            if cursor.fetchone() is None:
                raise PermissionError("Professional approval is required to express interest")
            cursor.execute("SELECT 1 FROM opportunities WHERE id = %s AND status = 'published'", (opportunity_id,))
            if cursor.fetchone() is None:
                raise LookupError("Opportunity not found")
            cursor.execute(
                """INSERT INTO opportunity_interests(id, opportunity_id, professional_id, approach, status)
                   VALUES (%s, %s, %s, %s, 'interested')
                   ON CONFLICT (opportunity_id, professional_id)
                   DO UPDATE SET approach = EXCLUDED.approach, status = 'interested'
                   RETURNING id""",
                (interest_id, opportunity_id, professional_id, approach),
            )
            interest_id = cursor.fetchone()[0]
        return interest_id

    def list_opportunity_interests(self, admin: str) -> list[dict[str, Any]]:
        with self.transaction() as connection:
            cursor = connection.cursor()
            cursor.execute("SELECT id, opportunity_id, professional_id, approach, status, created_at FROM opportunity_interests ORDER BY created_at DESC")
            return [{"id": str(row[0]), "opportunity_id": str(row[1]), "professional_id": row[2], "approach": row[3], "status": row[4], "created_at": row[5]} for row in cursor.fetchall()]

    def decide_opportunity_interest(self, interest_id: UUID, decision: str) -> dict[str, Any]:
        if decision not in {"selected", "withdrawn"}:
            raise ValueError("Unsupported opportunity decision")
        with self.transaction() as connection:
            cursor = connection.cursor()
            cursor.execute("UPDATE opportunity_interests SET status = %s WHERE id = %s RETURNING id, opportunity_id, professional_id, approach, status, created_at", (decision, interest_id))
            row = cursor.fetchone()
            if row is None:
                raise LookupError("Opportunity interest not found")
            return {"id": str(row[0]), "opportunity_id": str(row[1]), "professional_id": row[2], "approach": row[3], "status": row[4], "created_at": row[5]}

    def create_agent(self, actor_id: str, fields: dict[str, Any]) -> dict[str, Any]:
        agent_id = uuid4()
        with self.transaction() as connection:
            cursor = connection.cursor()
            cursor.execute(
                """INSERT INTO ai_agents(id, name, purpose, capability_category, provider, model, model_version,
                                          allowed_tools, data_access_scope, autonomy_level, requires_human_approval,
                                          budget_cap_cents, owner_actor_id)
                   VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                   RETURNING created_at, status""",
                (
                    agent_id, fields["name"], fields["purpose"], fields["capability_category"],
                    fields["provider"], fields["model"], fields["model_version"],
                    json.dumps(fields["allowed_tools"]), fields["data_access_scope"], fields["autonomy_level"],
                    fields["requires_human_approval"], fields["budget_cap_cents"], fields["owner_actor_id"],
                ),
            )
            created_at, created_status = cursor.fetchone()
            self._audit(cursor, None, actor_id, "ai_agent.registered", "ai_agent", str(agent_id), {"name": fields["name"], "provider": fields["provider"]})
        return {"id": str(agent_id), "created_at": created_at, "status": created_status, **fields}

    def list_agents(self) -> list[dict[str, Any]]:
        with self.transaction() as connection:
            cursor = connection.cursor()
            cursor.execute(
                """SELECT id, name, purpose, capability_category, provider, model, model_version, allowed_tools,
                          data_access_scope, autonomy_level, requires_human_approval, budget_cap_cents,
                          owner_actor_id, status, created_at
                   FROM ai_agents ORDER BY created_at"""
            )
            columns = ["id", "name", "purpose", "capability_category", "provider", "model", "model_version",
                       "allowed_tools", "data_access_scope", "autonomy_level", "requires_human_approval",
                       "budget_cap_cents", "owner_actor_id", "status", "created_at"]
            return [dict(zip(columns, (str(row[0]), *row[1:]))) for row in cursor.fetchall()]

    def get_agent(self, agent_id: UUID) -> dict[str, Any] | None:
        with self.transaction() as connection:
            cursor = connection.cursor()
            cursor.execute(
                """SELECT id, name, purpose, capability_category, provider, model, model_version, allowed_tools,
                          data_access_scope, autonomy_level, requires_human_approval, budget_cap_cents,
                          owner_actor_id, status, created_at
                   FROM ai_agents WHERE id = %s""",
                (agent_id,),
            )
            row = cursor.fetchone()
            if row is None:
                return None
            columns = ["id", "name", "purpose", "capability_category", "provider", "model", "model_version",
                       "allowed_tools", "data_access_scope", "autonomy_level", "requires_human_approval",
                       "budget_cap_cents", "owner_actor_id", "status", "created_at"]
            return dict(zip(columns, (str(row[0]), *row[1:])))

    def create_ai_run(
        self,
        package_id: UUID,
        requested_by: str,
        specification: str,
        budget_cents: int,
        output: dict[str, Any],
        agent_id: UUID = SYNTHETIC_AGENT_ID,
        agent_version: str = "synthetic-planner-v1",
        provider: str = "synthetic",
        model: str = "planner",
        model_version: str = "planning-only-v1",
    ) -> tuple[UUID, UUID, UUID]:
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
                """INSERT INTO ai_runs(id, work_package_id, requested_by, agent_version, policy_version, budget_cents,
                                        spent_cents, status, started_at, finished_at, agent_id, provider, model, model_version)
                   VALUES (%s, %s, %s, %s, 'planning-only-v1', %s, 0, 'succeeded', now(), now(), %s, %s, %s, %s)""",
                (run_id, package_id, requested_by, agent_version, budget_cents, agent_id, provider, model, model_version),
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
                          r.error_code, r.created_at, r.started_at, r.finished_at, e.organization_id,
                          r.agent_id, r.provider, r.model, r.model_version
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
                "agent_id": str(row[14]) if row[14] else None,
                "provider": row[15],
                "model": row[16],
                "model_version": row[17],
                "artifact": None if artifact is None else {"id": str(artifact[0]), "version": artifact[1], "content": artifact[2], "status": artifact[3], "created_at": artifact[4]},
            }

    def decide_ai_artifact(self, run_id: UUID, reviewer_id: str, decision: str, comment: str, admin: bool = False) -> dict[str, Any]:
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
            if not admin:
                cursor.execute(
                    "SELECT 1 FROM memberships WHERE organization_id = %s AND actor_id = %s AND role IN ('reviewer', 'owner') AND revoked_at IS NULL",
                    (organization_id, reviewer_id),
                )
            if not admin and cursor.fetchone() is None:
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
                   WHERE w.id = %s FOR UPDATE OF w""",
                (package_id,),
            )
            row = cursor.fetchone()
            if row is None:
                raise LookupError("Work package not found")
            organization_id = row[0]
            cursor.execute(
                """SELECT 1 FROM memberships WHERE organization_id = %s AND actor_id = %s AND role = 'owner' AND revoked_at IS NULL
                   UNION SELECT 1 FROM assignments a JOIN professional_admissions p ON p.professional_id = a.professional_id
                   WHERE a.work_package_id = %s AND a.professional_id = %s AND a.status = 'accepted'
                   AND (a.expires_at IS NULL OR a.expires_at > now()) AND p.status = 'approved'
                   AND EXISTS (SELECT 1 FROM memberships m WHERE m.organization_id = %s
                       AND m.actor_id = a.professional_id AND m.role = 'professional' AND m.revoked_at IS NULL)""",
                (organization_id, submitted_by, package_id, submitted_by, organization_id),
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
                if role in {None, "professional"}:
                    cursor.execute(
                        "SELECT 1 FROM studio_current_assignments WHERE work_package_id = %s AND professional_id = %s AND status = 'accepted'",
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

    def reviewer_queue(self, reviewer: str, offset: int, limit: int) -> list[dict[str, Any]]:
        with self.transaction() as connection:
            cursor = connection.cursor()
            cursor.execute(
                """WITH queue AS (
                     SELECT d.id, d.work_package_id, d.title, d.version, d.content, d.created_at,
                            p.name AS project_name, w.title AS package_title, w.acceptance_criteria
                     FROM deliverables d JOIN work_packages w ON w.id = d.work_package_id
                     JOIN projects p ON p.id = w.project_id JOIN engagements e ON e.id = p.engagement_id
                     WHERE d.status = 'under_review' AND d.submitted_by <> %s AND EXISTS (
                       SELECT 1 FROM memberships m WHERE m.organization_id = e.organization_id
                       AND m.actor_id = %s AND m.revoked_at IS NULL AND m.role IN ('owner','reviewer'))
                     ORDER BY d.created_at, d.id LIMIT %s OFFSET %s)
                   SELECT q.id, q.title, q.version, q.content, q.project_name, q.package_title, q.acceptance_criteria,
                          COALESCE((SELECT jsonb_agg(to_jsonb(history) ORDER BY history.version DESC) FROM (
                            SELECT d.version, r.decision, r.comment FROM deliverable_reviews r
                            JOIN deliverables d ON d.id = r.deliverable_id
                            WHERE d.work_package_id = q.work_package_id AND d.version < q.version
                            ORDER BY d.version DESC, r.created_at DESC LIMIT 5) history), '[]'::jsonb)
                   FROM queue q ORDER BY q.created_at, q.id""", (reviewer, reviewer, limit, offset))
            return [{"id": str(row[0]), "title": row[1], "version": row[2], "content": row[3],
                     "project_name": row[4], "package_title": row[5], "acceptance_criteria": row[6],
                     "previous_reviews": row[7]} for row in cursor.fetchall()]

    def review_deliverable(self, deliverable_id: UUID, reviewer_id: str, decision: str, comment: str) -> dict[str, Any]:
        with self.transaction() as connection:
            cursor = connection.cursor()
            cursor.execute(
                """SELECT d.work_package_id, d.version, d.title, d.content, d.submitted_by, d.status, e.organization_id
                   FROM deliverables d JOIN work_packages w ON w.id = d.work_package_id
                   JOIN projects p ON p.id = w.project_id JOIN engagements e ON e.id = p.engagement_id
                   WHERE d.id = %s FOR UPDATE OF d""",
                (deliverable_id,),
            )
            row = cursor.fetchone()
            if row is None:
                raise LookupError("Deliverable not found")
            package_id, version, title, content, submitted_by, current_status, organization_id = row
            if submitted_by == reviewer_id:
                raise ValueError("Independent review is required")
            cursor.execute("SELECT 1 FROM memberships WHERE organization_id = %s AND actor_id = %s AND role IN ('reviewer', 'owner') AND revoked_at IS NULL FOR SHARE", (organization_id, reviewer_id))
            if cursor.fetchone() is None:
                raise PermissionError("Reviewer is not authorized for this organization")
            if current_status != "under_review":
                raise ValueError("This version has already received a decision")
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
            cursor.execute("INSERT INTO notifications(id, project_id, recipient_group, kind, title, body) SELECT %s, p.id, 'internal', 'deliverable.client_accepted', 'Client acceptance recorded', 'A client accepted an internally approved deliverable.' FROM projects p WHERE p.id = (SELECT project_id FROM work_packages WHERE id = %s)", (uuid4(), package_id))
            self._audit(cursor, organization_id, client_id, "deliverable.client_accepted", "deliverable", str(deliverable_id))
            return {"id": str(deliverable_id), "work_package_id": str(package_id), "version": version, "title": title, "content": content, "submitted_by": submitted_by, "status": "accepted", "accepted_by": client_id}

    def request_client_revision(self, deliverable_id: UUID, client_id: str, comment: str) -> dict[str, Any]:
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
            cursor.execute("SELECT 1 FROM memberships WHERE organization_id = %s AND actor_id = %s AND role = 'client' AND revoked_at IS NULL", (organization_id, client_id))
            if cursor.fetchone() is None:
                raise PermissionError("Client is not authorized for this organization")
            if current_status != "approved":
                raise ValueError("Only an internally approved deliverable can be sent back for revision")
            request_id = uuid4()
            cursor.execute("UPDATE deliverables SET status = 'revision_requested' WHERE id = %s", (deliverable_id,))
            cursor.execute("INSERT INTO client_revision_requests(id, deliverable_id, client_id, comment) VALUES (%s, %s, %s, %s)", (request_id, deliverable_id, client_id, comment))
            cursor.execute("INSERT INTO notifications(id, project_id, recipient_group, kind, title, body) SELECT %s, p.id, 'internal', 'deliverable.client_revision_requested', 'Client revision requested', 'A client requested changes to an approved deliverable.' FROM projects p WHERE p.id = (SELECT project_id FROM work_packages WHERE id = %s)", (uuid4(), package_id))
            self._audit(cursor, organization_id, client_id, "deliverable.client_revision_requested", "deliverable", str(deliverable_id), {"comment": comment})
            return {"deliverable": {"id": str(deliverable_id), "work_package_id": str(package_id), "version": version, "title": title, "content": content, "submitted_by": submitted_by, "status": "revision_requested"}, "revision_request": {"id": str(request_id), "deliverable_id": str(deliverable_id), "client_id": client_id, "comment": comment}}

    def complete_project(self, project_id: UUID, actor: str) -> dict[str, Any]:
        with self.transaction() as connection:
            cursor = connection.cursor()
            cursor.execute("SELECT e.organization_id, p.status FROM projects p JOIN engagements e ON e.id = p.engagement_id WHERE p.id = %s FOR UPDATE OF p", (project_id,))
            row = cursor.fetchone()
            if row is None:
                raise LookupError("Project not found")
            organization_id, status = row
            self._require_owner(cursor, organization_id, actor)
            if status == "completed":
                return {"id": str(project_id), "status": status}
            cursor.execute("""SELECT d.id, d.title, d.version FROM deliverables d JOIN work_packages w ON w.id=d.work_package_id
                           WHERE w.project_id=%s AND d.status='accepted' ORDER BY d.id""", (project_id,))
            versions = [{"id": str(key), "title": title, "version": version} for key, title, version in cursor.fetchall()]
            if not versions:
                raise ValueError("At least one client-accepted deliverable is required")
            cursor.execute("UPDATE projects SET status = 'completed' WHERE id = %s", (project_id,))
            cursor.execute("INSERT INTO project_handovers(project_id, recorded_by, versions) VALUES (%s,%s,%s::jsonb)",
                           (project_id, actor, json.dumps(versions)))
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
            if role == "professional":
                cursor.execute("""UPDATE assignments a SET status='revoked' FROM work_packages w
                    JOIN projects p ON p.id=w.project_id JOIN engagements e ON e.id=p.engagement_id
                    WHERE a.work_package_id=w.id AND e.organization_id=%s AND a.professional_id=%s
                      AND a.status IN ('accepted','invited')""", (organization_id, actor_id))
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
                       WHERE EXISTS (SELECT 1 FROM memberships m WHERE m.organization_id = e.organization_id AND m.actor_id = %s
                         AND m.revoked_at IS NULL AND m.role IN ('owner','reviewer'))
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

    def create_diagnostic_link(self, organization_id: UUID, source_system: str, source_engagement_id: str, actor: str) -> dict[str, Any]:
        link_id = uuid4()
        with self.transaction() as connection:
            cursor = connection.cursor()
            self._require_owner(cursor, organization_id, actor)
            cursor.execute("SELECT 1 FROM organizations WHERE id = %s", (organization_id,))
            if cursor.fetchone() is None:
                raise LookupError("Organization not found")
            cursor.execute("SELECT 1 FROM diagnostic_links WHERE source_system = %s AND source_engagement_id = %s", (source_system, source_engagement_id))
            if cursor.fetchone() is not None:
                raise ValueError("This diagnostic engagement is already linked to a Studio organization")
            cursor.execute(
                """INSERT INTO diagnostic_links(id, organization_id, source_system, source_engagement_id, linked_by)
                   VALUES (%s, %s, %s, %s, %s) RETURNING created_at""",
                (link_id, organization_id, source_system, source_engagement_id, actor),
            )
            created_at = cursor.fetchone()[0]
            self._audit(cursor, organization_id, actor, "diagnostic_link.created", "diagnostic_link", str(link_id), {"source_engagement_id": source_engagement_id})
        return {"id": str(link_id), "organization_id": str(organization_id), "source_system": source_system, "source_engagement_id": source_engagement_id, "linked_by": actor, "created_at": created_at}

    def get_diagnostic_link(self, source_system: str, source_engagement_id: str) -> dict[str, Any] | None:
        with self.transaction() as connection:
            cursor = connection.cursor()
            cursor.execute(
                "SELECT id, organization_id, linked_by FROM diagnostic_links WHERE source_system = %s AND source_engagement_id = %s",
                (source_system, source_engagement_id),
            )
            row = cursor.fetchone()
            if row is None:
                return None
            return {"id": str(row[0]), "organization_id": str(row[1]), "linked_by": row[2]}

    def get_diagnostic_handoff(self, link_id: UUID, idempotency_key: str) -> dict[str, Any] | None:
        with self.transaction() as connection:
            cursor = connection.cursor()
            cursor.execute(
                """SELECT id, engagement_id, project_id, created_at FROM diagnostic_handoffs
                   WHERE link_id = %s AND idempotency_key = %s""",
                (link_id, idempotency_key),
            )
            row = cursor.fetchone()
            if row is None:
                return None
            handoff_id = row[0]
            cursor.execute(
                "SELECT work_package_id, source_recommendation_id, evidence_references FROM diagnostic_handoff_work_packages WHERE handoff_id = %s",
                (handoff_id,),
            )
            work_packages = [{"id": str(item[0]), "source_recommendation_id": item[1], "evidence_references": item[2]} for item in cursor.fetchall()]
            return {"id": str(handoff_id), "engagement_id": str(row[1]), "project_id": str(row[2]), "created_at": row[3], "work_packages": work_packages}

    def record_diagnostic_handoff(
        self, link_id: UUID, idempotency_key: str, source_report_id: str, source_report_version: int,
        engagement_id: UUID, project_id: UUID, work_packages: list[dict[str, Any]], actor: str,
    ) -> dict[str, Any]:
        handoff_id = uuid4()
        with self.transaction() as connection:
            cursor = connection.cursor()
            cursor.execute("SELECT organization_id FROM engagements WHERE id = %s", (engagement_id,))
            organization_id = cursor.fetchone()[0]
            cursor.execute(
                """INSERT INTO diagnostic_handoffs(id, link_id, idempotency_key, source_report_id, source_report_version, engagement_id, project_id, received_by)
                   VALUES (%s, %s, %s, %s, %s, %s, %s, %s) RETURNING created_at""",
                (handoff_id, link_id, idempotency_key, source_report_id, source_report_version, engagement_id, project_id, actor),
            )
            created_at = cursor.fetchone()[0]
            for item in work_packages:
                cursor.execute(
                    """INSERT INTO diagnostic_handoff_work_packages(id, handoff_id, work_package_id, source_recommendation_id, evidence_references)
                       VALUES (%s, %s, %s, %s, %s)""",
                    (uuid4(), handoff_id, UUID(item["id"]), item["source_recommendation_id"], json.dumps(item["evidence_references"])),
                )
            self._audit(cursor, organization_id, actor, "diagnostic_handoff.received", "diagnostic_handoff", str(handoff_id), {"source_report_id": source_report_id})
        return {"id": str(handoff_id), "engagement_id": str(engagement_id), "project_id": str(project_id), "created_at": created_at, "work_packages": work_packages}

    def create_referral_link(self, partner_name: str, actor: str) -> dict[str, Any]:
        link_id = uuid4()
        code = secrets.token_hex(4).upper()
        view_token = secrets.token_urlsafe(24)
        with self.transaction() as connection:
            cursor = connection.cursor()
            cursor.execute(
                """INSERT INTO referral_links(id, code, view_token, partner_name, created_by)
                   VALUES (%s, %s, %s, %s, %s) RETURNING status, created_at""",
                (link_id, code, view_token, partner_name, actor),
            )
            status_value, created_at = cursor.fetchone()
            self._audit(cursor, None, actor, "referral_link.created", "referral_link", str(link_id), {"partner_name": partner_name})
        return {
            "id": str(link_id), "code": code, "view_token": view_token, "partner_name": partner_name,
            "created_by": actor, "status": status_value, "created_at": created_at, "visit_count": 0, "signup_count": 0,
        }

    def list_referral_links(self) -> list[dict[str, Any]]:
        with self.transaction() as connection:
            cursor = connection.cursor()
            cursor.execute(
                """SELECT l.id, l.code, l.view_token, l.partner_name, l.created_by, l.status, l.created_at,
                          COUNT(*) FILTER (WHERE e.event_type = 'visit') AS visit_count,
                          COUNT(*) FILTER (WHERE e.event_type = 'signup') AS signup_count
                   FROM referral_links l LEFT JOIN referral_events e ON e.link_id = l.id
                   GROUP BY l.id ORDER BY l.created_at DESC"""
            )
            columns = ["id", "code", "view_token", "partner_name", "created_by", "status", "created_at", "visit_count", "signup_count"]
            return [dict(zip(columns, (str(row[0]), *row[1:]))) for row in cursor.fetchall()]

    def record_referral_visit(self, code: str) -> None:
        with self.transaction() as connection:
            cursor = connection.cursor()
            cursor.execute("SELECT id FROM referral_links WHERE code = %s AND status = 'active'", (code,))
            row = cursor.fetchone()
            if row is None:
                raise LookupError("Referral link not found")
            cursor.execute(
                "INSERT INTO referral_events(id, link_id, event_type) VALUES (%s, %s, 'visit')",
                (uuid4(), row[0]),
            )

    def record_referral_signup(self, code: str, organization_id: UUID) -> None:
        with self.transaction() as connection:
            cursor = connection.cursor()
            cursor.execute("SELECT id FROM referral_links WHERE code = %s AND status = 'active'", (code,))
            row = cursor.fetchone()
            if row is None:
                return
            cursor.execute(
                "INSERT INTO referral_events(id, link_id, event_type, referred_organization_id) VALUES (%s, %s, 'signup', %s)",
                (uuid4(), row[0], organization_id),
            )

    def get_referral_stats_by_token(self, view_token: str) -> dict[str, Any] | None:
        with self.transaction() as connection:
            cursor = connection.cursor()
            cursor.execute(
                """SELECT l.partner_name, l.code, l.status, l.created_at,
                          COUNT(*) FILTER (WHERE e.event_type = 'visit') AS visit_count,
                          COUNT(*) FILTER (WHERE e.event_type = 'signup') AS signup_count
                   FROM referral_links l LEFT JOIN referral_events e ON e.link_id = l.id
                   WHERE l.view_token = %s GROUP BY l.id""",
                (view_token,),
            )
            row = cursor.fetchone()
            if row is None:
                return None
            return {"partner_name": row[0], "code": row[1], "status": row[2], "created_at": row[3], "visit_count": row[4], "signup_count": row[5]}

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
