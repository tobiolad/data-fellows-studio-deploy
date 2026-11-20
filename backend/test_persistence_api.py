import os
import unittest

from fastapi.testclient import TestClient

import backend.app as app_module
from backend.app import app, store


def auth(actor: str, role: str) -> dict[str, str]:
    return {"Authorization": f"Bearer test:{actor}:{role}"}


@unittest.skipUnless(os.getenv("STUDIO_TEST_DATABASE_URL"), "Set STUDIO_TEST_DATABASE_URL for PostgreSQL API tests")
class PostgresApiIntegrationTests(unittest.TestCase):
    def setUp(self) -> None:
        store.reset()
        os.environ["STUDIO_TEST_MODE"] = "true"
        os.environ["STUDIO_PERSISTENCE"] = "postgres"
        os.environ["STUDIO_DATABASE_URL"] = os.environ["STUDIO_TEST_DATABASE_URL"]
        app_module.postgres_repository.cache_clear()
        self.client = TestClient(app)
        self.admin = auth("postgres-admin", "admin")

    def tearDown(self) -> None:
        os.environ.pop("STUDIO_PERSISTENCE", None)
        os.environ.pop("STUDIO_DATABASE_URL", None)
        app_module.postgres_repository.cache_clear()

    def test_core_organization_and_engagement_routes_use_postgres(self) -> None:
        organization = self.client.post("/api/organizations", headers=self.admin, json={"name": "Persistent synthetic org"})
        self.assertEqual(organization.status_code, 201)
        organization_id = organization.json()["id"]
        membership = self.client.post(
            f"/api/organizations/{organization_id}/members",
            headers=self.admin,
            json={"actor_id": "postgres-client", "role": "client"},
        )
        self.assertEqual(membership.status_code, 201)
        engagement = self.client.post(
            "/api/engagements",
            headers=self.admin,
            json={"organization_id": organization_id, "name": "Persistent engagement", "objective": "Verify database routing"},
        )
        self.assertEqual(engagement.status_code, 201)
        listed = self.client.get("/api/engagements", headers=auth("postgres-client", "client"))
        self.assertEqual(listed.status_code, 200)
        self.assertEqual(listed.json()[0]["id"], engagement.json()["id"])
        unsupported = self.client.post("/api/projects", headers=self.admin, json={"engagement_id": engagement.json()["id"], "name": "Not migrated"})
        self.assertEqual(unsupported.status_code, 501)


if __name__ == "__main__":
    unittest.main()
