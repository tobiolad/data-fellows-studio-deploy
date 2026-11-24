import os
import unittest

from fastapi.testclient import TestClient

import backend.app as app_module
from backend.app import app, store


def auth(actor: str, role: str) -> dict[str, str]:
    return {"Authorization": f"Bearer test:{actor}:{role}"}


@unittest.skipUnless(os.getenv("STUDIO_TEST_DATABASE_URL"), "Set STUDIO_TEST_DATABASE_URL for PostgreSQL API tests")
class ReferralLinkIntegrationTests(unittest.TestCase):
    def setUp(self) -> None:
        store.reset()
        os.environ["STUDIO_TEST_MODE"] = "true"
        os.environ["STUDIO_PERSISTENCE"] = "postgres"
        os.environ["STUDIO_DATABASE_URL"] = os.environ["STUDIO_TEST_DATABASE_URL"]
        app_module.postgres_repository.cache_clear()
        app_module.postgres_repository().migrate()
        self.client = TestClient(app)
        self.admin = auth("referral-admin", "admin")
        self.reviewer = auth("referral-reviewer", "reviewer")

    def tearDown(self) -> None:
        os.environ.pop("STUDIO_PERSISTENCE", None)
        os.environ.pop("STUDIO_DATABASE_URL", None)
        app_module.postgres_repository.cache_clear()

    def test_only_admin_may_create_a_referral_link(self):
        denied = self.client.post("/api/referral-links", headers=self.reviewer, json={"partner_name": "Launch Accelerator"})
        self.assertEqual(denied.status_code, 403)
        created = self.client.post("/api/referral-links", headers=self.admin, json={"partner_name": "Launch Accelerator"})
        self.assertEqual(created.status_code, 201)
        body = created.json()
        self.assertEqual(len(body["code"]), 8)
        self.assertGreaterEqual(len(body["view_token"]), 16)
        self.assertEqual(body["visit_count"], 0)
        self.assertEqual(body["signup_count"], 0)

    def test_visits_and_signups_are_tracked_and_visible_via_view_token(self):
        link = self.client.post("/api/referral-links", headers=self.admin, json={"partner_name": "Northstar Accelerator"}).json()

        self.assertEqual(self.client.post(f"/api/referral-links/{link['code']}/visit").status_code, 204)
        self.assertEqual(self.client.post(f"/api/referral-links/{link['code']}/visit").status_code, 204)

        org = self.client.post("/api/organizations", headers=self.admin, json={"name": "Referred Co", "referral_code": link["code"]})
        self.assertEqual(org.status_code, 201)

        listing = self.client.get("/api/referral-links", headers=self.admin).json()
        row = next(item for item in listing if item["code"] == link["code"])
        self.assertEqual(row["visit_count"], 2)
        self.assertEqual(row["signup_count"], 1)

        stats = self.client.get(f"/api/referral/{link['view_token']}/stats")
        self.assertEqual(stats.status_code, 200)
        self.assertEqual(stats.json()["partner_name"], "Northstar Accelerator")
        self.assertEqual(stats.json()["visit_count"], 2)
        self.assertEqual(stats.json()["signup_count"], 1)

    def test_visit_to_unknown_code_returns_404(self):
        response = self.client.post("/api/referral-links/NOTREAL1/visit")
        self.assertEqual(response.status_code, 404)

    def test_organization_creation_with_invalid_referral_code_still_succeeds(self):
        response = self.client.post("/api/organizations", headers=self.admin, json={"name": "No Referral Co", "referral_code": "NOTREAL1"})
        self.assertEqual(response.status_code, 201)

    def test_stats_lookup_with_unknown_token_is_404(self):
        response = self.client.get("/api/referral/not-a-real-token-xxxxxxxxxxxxxxxxxxxx/stats")
        self.assertEqual(response.status_code, 404)
