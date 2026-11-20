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
