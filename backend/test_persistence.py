import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import backend.persistence as persistence_module
from backend.persistence import MIGRATIONS_DIR, PersistenceConfigurationError, PostgresRepository


class PersistenceConfigurationTests(unittest.TestCase):
    def test_versioned_migrations_exist_and_are_ordered(self) -> None:
        migrations = sorted(MIGRATIONS_DIR.glob("*.sql"))
        self.assertEqual([path.name for path in migrations], ["001_initial.sql", "002_ai_execution_controls.sql", "003_work_package_dependencies.sql", "004_professional_opportunities.sql", "005_client_revision_requests.sql", "006_project_operations.sql", "007_professional_profiles.sql"])
        self.assertIn("CREATE TABLE IF NOT EXISTS organizations", migrations[0].read_text(encoding="utf-8"))
        self.assertIn("CREATE TABLE IF NOT EXISTS audit_events", migrations[0].read_text(encoding="utf-8"))
        self.assertIn("CREATE TABLE IF NOT EXISTS work_package_dependencies", migrations[2].read_text(encoding="utf-8"))

    def test_repository_requires_dsn_without_test_factory(self) -> None:
        with self.assertRaises(PersistenceConfigurationError):
            PostgresRepository(dsn=None, connect_factory=None)


@unittest.skipUnless(os.getenv("STUDIO_TEST_DATABASE_URL"), "Set STUDIO_TEST_DATABASE_URL for PostgreSQL integration tests")
class PostgresIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.repository = PostgresRepository(os.environ["STUDIO_TEST_DATABASE_URL"])
        cls.repository.migrate()

    def test_owner_membership_and_audit_scope(self) -> None:
        organization_id = self.repository.create_organization("Postgres synthetic org", "owner-1")
        self.repository.grant_membership(organization_id, "reviewer-1", "reviewer", "owner-1")
        self.repository.revoke_membership(organization_id, "reviewer-1", "reviewer", "owner-1")
        audit = self.repository.list_audit("owner-1")
        self.assertTrue(any(event["action"] == "membership.revoked" for event in audit))

    def test_migrations_are_idempotent(self) -> None:
        self.repository.migrate()
        self.repository.migrate()

    def test_migrations_record_checksums(self) -> None:
        with self.repository.transaction() as connection:
            cursor = connection.cursor()
            cursor.execute("SELECT version, checksum FROM studio_schema_migrations ORDER BY version")
            rows = cursor.fetchall()
        self.assertTrue(rows)
        self.assertTrue(all(version and checksum and len(checksum) == 64 for version, checksum in rows))

    def test_changed_applied_migration_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            tampered = Path(directory) / "001_initial.sql"
            tampered.write_text((MIGRATIONS_DIR / "001_initial.sql").read_text(encoding="utf-8") + "\n-- tampered\n", encoding="utf-8")
            with patch.object(persistence_module, "MIGRATIONS_DIR", Path(directory)):
                with self.assertRaises(PersistenceConfigurationError):
                    self.repository.migrate()


if __name__ == "__main__":
    unittest.main()
