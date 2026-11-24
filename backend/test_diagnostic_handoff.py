import os
import unittest

from fastapi.testclient import TestClient

import backend.app as app_module
from backend.app import app, store


def auth(actor: str, role: str) -> dict[str, str]:
    return {"Authorization": f"Bearer test:{actor}:{role}"}


def handoff_payload(**overrides):
    payload = {
        "idempotency_key": "report:11111111-1111-1111-1111-111111111111",
        "schema_version": 1,
        "engagement_id": "bizpilot-engagement-1",
        "report_id": "report-1",
        "report_version": 1,
        "problem": "Stockout investigations take too long to complete.",
        "desired_outcome": "Reduce stockout investigation time by half.",
        "work_packages": [
            {
                "id": "recommendation-1",
                "intervention": "Capture completion timestamps automatically",
                "outcome": "Faster completion visibility",
                "acceptance": "Timestamps are captured for every completed investigation",
                "research_claim": {"id": "claim-1", "sources": [{"source_id": "s1", "provider": "tavily", "url": "https://example.com", "mode": "search"}]},
            }
        ],
    }
    payload.update(overrides)
    return payload


@unittest.skipUnless(os.getenv("STUDIO_TEST_DATABASE_URL"), "Set STUDIO_TEST_DATABASE_URL for PostgreSQL API tests")
class DiagnosticHandoffIntegrationTests(unittest.TestCase):
    def setUp(self) -> None:
        store.reset()
        os.environ["STUDIO_TEST_MODE"] = "true"
        os.environ["STUDIO_PERSISTENCE"] = "postgres"
        os.environ["STUDIO_DATABASE_URL"] = os.environ["STUDIO_TEST_DATABASE_URL"]
        app_module.postgres_repository.cache_clear()
        app_module.postgres_repository().migrate()
        self.client = TestClient(app)
        self.admin = auth("handoff-admin", "admin")
        self.diagnostics_service = auth("bizpilot-service", "diagnostics_service")
        self.client_user = auth("handoff-client", "client")

    def tearDown(self) -> None:
        os.environ.pop("STUDIO_PERSISTENCE", None)
        os.environ.pop("STUDIO_DATABASE_URL", None)
        app_module.postgres_repository.cache_clear()

    def make_org(self):
        return self.client.post("/api/organizations", headers=self.admin, json={"name": "Diagnostic client co"}).json()["id"]

    def test_only_admin_may_create_a_link(self):
        org_id = self.make_org()
        denied = self.client.post("/api/diagnostic-links", headers=self.client_user, json={"organization_id": org_id, "source_engagement_id": "bizpilot-engagement-admin-only"})
        self.assertEqual(denied.status_code, 403)
        created = self.client.post("/api/diagnostic-links", headers=self.admin, json={"organization_id": org_id, "source_engagement_id": "bizpilot-engagement-admin-only"})
        self.assertEqual(created.status_code, 201)

    def test_linking_the_same_source_engagement_twice_is_rejected(self):
        org_id = self.make_org()
        first = self.client.post("/api/diagnostic-links", headers=self.admin, json={"organization_id": org_id, "source_engagement_id": "bizpilot-engagement-dup"})
        self.assertEqual(first.status_code, 201)
        second = self.client.post("/api/diagnostic-links", headers=self.admin, json={"organization_id": org_id, "source_engagement_id": "bizpilot-engagement-dup"})
        self.assertEqual(second.status_code, 409)

    def test_handoff_without_a_link_is_rejected(self):
        response = self.client.post("/api/diagnostic-handoffs", headers=self.diagnostics_service, json=handoff_payload(engagement_id="unlinked-engagement"))
        self.assertEqual(response.status_code, 404)

    def test_handoff_creates_scoped_project_and_is_idempotent(self):
        org_id = self.make_org()
        self.client.post("/api/diagnostic-links", headers=self.admin, json={"organization_id": org_id, "source_engagement_id": "bizpilot-engagement-1"}).raise_for_status()

        denied = self.client.post("/api/diagnostic-handoffs", headers=self.client_user, json=handoff_payload())
        self.assertEqual(denied.status_code, 403)

        first = self.client.post("/api/diagnostic-handoffs", headers=self.diagnostics_service, json=handoff_payload())
        self.assertEqual(first.status_code, 201)
        body = first.json()
        self.assertFalse(body["idempotent"])
        self.assertEqual(len(body["work_packages"]), 1)
        self.assertEqual(body["work_packages"][0]["source_recommendation_id"], "recommendation-1")
        self.assertEqual(body["work_packages"][0]["evidence_references"][0]["provider"], "tavily")

        project = self.client.get(f"/api/engagements/{body['engagement_id']}/projects", headers=self.admin).json()
        self.assertEqual(project[0]["id"], body["project_id"])
        packages = self.client.get(f"/api/projects/{body['project_id']}/work-packages", headers=self.admin).json()
        self.assertEqual(packages[0]["id"], body["work_packages"][0]["id"])
        self.assertEqual(packages[0]["acceptance_criteria"], ["Timestamps are captured for every completed investigation"])
        self.assertEqual(packages[0]["status"], "unassigned")

        second = self.client.post("/api/diagnostic-handoffs", headers=self.diagnostics_service, json=handoff_payload())
        self.assertEqual(second.status_code, 201)
        self.assertTrue(second.json()["idempotent"])
        self.assertEqual(second.json()["engagement_id"], body["engagement_id"])
        self.assertEqual(second.json()["project_id"], body["project_id"])

    def test_unsupported_schema_version_is_rejected(self):
        org_id = self.make_org()
        self.client.post("/api/diagnostic-links", headers=self.admin, json={"organization_id": org_id, "source_engagement_id": "bizpilot-engagement-schema"}).raise_for_status()
        response = self.client.post("/api/diagnostic-handoffs", headers=self.diagnostics_service, json=handoff_payload(engagement_id="bizpilot-engagement-schema", schema_version=2))
        self.assertEqual(response.status_code, 422)
