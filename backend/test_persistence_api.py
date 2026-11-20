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
        self.assertIn(engagement.json()["id"], {item["id"] for item in listed.json()})
        project = self.client.post("/api/projects", headers=self.admin, json={"engagement_id": engagement.json()["id"], "name": "Persistent project"})
        self.assertEqual(project.status_code, 201)
        package = self.client.post(
            "/api/work-packages",
            headers=self.admin,
            json={"project_id": project.json()["id"], "title": "Persistent package", "acceptance_criteria": ["reviewed"]},
        )
        self.assertEqual(package.status_code, 201)
        professional = self.client.post(
            f"/api/organizations/{organization_id}/members",
            headers=self.admin,
            json={"actor_id": "postgres-professional", "role": "professional"},
        )
        self.assertEqual(professional.status_code, 201)
        reviewer = self.client.post(
            f"/api/organizations/{organization_id}/members",
            headers=self.admin,
            json={"actor_id": "postgres-reviewer", "role": "reviewer"},
        )
        self.assertEqual(reviewer.status_code, 201)
        approval = self.client.post("/api/professionals/postgres-professional/approve", headers=self.admin)
        self.assertEqual(approval.status_code, 200)
        invitation = self.client.post(
            f"/api/work-packages/{package.json()['id']}/assignments",
            headers=self.admin,
            json={"professional_id": "postgres-professional"},
        )
        self.assertEqual(invitation.status_code, 201)
        accepted = self.client.post(
            f"/api/assignments/{invitation.json()['id']}/accept",
            headers=auth("postgres-professional", "professional"),
        )
        self.assertEqual(accepted.status_code, 200)
        run = self.client.post(
            "/api/ai-runs",
            headers=self.admin,
            json={"work_package_id": package.json()["id"], "specification": "Prepare a bounded synthetic plan for the approved work package."},
        )
        self.assertEqual(run.status_code, 201)
        self.assertEqual(self.client.post(f"/api/ai-runs/{run.json()['id']}/decision", headers=self.admin, json={"decision": "approved"}).status_code, 409)
        decision = self.client.post(
            f"/api/ai-runs/{run.json()['id']}/decision",
            headers=auth("postgres-reviewer", "reviewer"),
            json={"decision": "approved", "comment": "Synthetic review complete"},
        )
        self.assertEqual(decision.status_code, 200)


if __name__ == "__main__":
    unittest.main()
