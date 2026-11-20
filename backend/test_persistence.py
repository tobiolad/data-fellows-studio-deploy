import os
import unittest
from pathlib import Path

from backend.persistence import MIGRATIONS_DIR, PersistenceConfigurationError, PostgresRepository


class PersistenceConfigurationTests(unittest.TestCase):
    def test_versioned_migrations_exist_and_are_ordered(self) -> None:
        migrations = sorted(MIGRATIONS_DIR.glob("*.sql"))
        self.assertEqual([path.name for path in migrations], ["001_initial.sql"])
        self.assertIn("CREATE TABLE IF NOT EXISTS organizations", migrations[0].read_text(encoding="utf-8"))
        self.assertIn("CREATE TABLE IF NOT EXISTS audit_events", migrations[0].read_text(encoding="utf-8"))

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


if __name__ == "__main__":
    unittest.main()
