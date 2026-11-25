import os
import unittest

from fastapi.testclient import TestClient

import backend.app as app_module
from backend.app import app, store


def auth(actor: str, role: str) -> dict[str, str]:
    return {"Authorization": f"Bearer test:{actor}:{role}"}


@unittest.skipUnless(os.getenv("STUDIO_TEST_DATABASE_URL"), "Set STUDIO_TEST_DATABASE_URL for PostgreSQL API tests")
class SupportRequestIntegrationTests(unittest.TestCase):
    def setUp(self) -> None:
        store.reset()
        os.environ["STUDIO_TEST_MODE"] = "true"
        os.environ["STUDIO_PERSISTENCE"] = "postgres"
        os.environ["STUDIO_DATABASE_URL"] = os.environ["STUDIO_TEST_DATABASE_URL"]
        app_module.postgres_repository.cache_clear()
        app_module.postgres_repository().migrate()
        self.client = TestClient(app)
        self.admin = auth("support-admin", "admin")

    def tearDown(self) -> None:
        for key in ["STUDIO_PERSISTENCE", "STUDIO_DATABASE_URL"]:
            os.environ.pop(key, None)
        app_module.postgres_repository.cache_clear()

    def _create_org_with_client(self, client_id: str) -> str:
        org_id = self.client.post("/api/organizations", headers=self.admin, json={"name": "Acme Logistics"}).json()["id"]
        self.client.post(f"/api/organizations/{org_id}/members", headers=self.admin, json={"actor_id": client_id, "role": "client"}).raise_for_status()
        return org_id

    def test_a_client_may_submit_and_read_back_their_own_request(self):
        org_id = self._create_org_with_client("support-client")
        client_header = auth("support-client", "client")
        created = self.client.post(
            f"/api/organizations/{org_id}/support-requests", headers=client_header,
            json={"subject": "Can't find my invoice", "body": "I was told an invoice was sent but I don't see it."},
        )
        self.assertEqual(created.status_code, 201)
        self.assertEqual(created.json()["status"], "open")

        own = self.client.get(f"/api/organizations/{org_id}/support-requests", headers=client_header)
        self.assertEqual(own.status_code, 200)
        self.assertEqual(len(own.json()), 1)
        self.assertEqual(own.json()[0]["organization_name"], "Acme Logistics")

    def test_a_non_member_may_not_submit_a_request_for_another_organization(self):
        org_id = self._create_org_with_client("support-client-2")
        other_org_id = self._create_org_with_client("someone-else")
        response = self.client.post(
            f"/api/organizations/{org_id}/support-requests", headers=auth("someone-else", "client"),
            json={"subject": "Hi", "body": "trying to submit for someone else's org"},
        )
        self.assertEqual(response.status_code, 403)
        self.assertNotEqual(org_id, other_org_id)

    def test_a_client_may_not_list_support_requests_across_every_organization(self):
        self._create_org_with_client("support-client-3")
        response = self.client.get("/api/support-requests", headers=auth("support-client-3", "client"))
        self.assertEqual(response.status_code, 403)

    def test_admin_sees_the_request_in_the_global_inbox_and_can_resolve_it(self):
        org_id = self._create_org_with_client("support-client-4")
        created = self.client.post(
            f"/api/organizations/{org_id}/support-requests", headers=auth("support-client-4", "client"),
            json={"subject": "Billing question", "body": "Does the invoice include tax?"},
        )
        request_id = created.json()["id"]

        inbox = self.client.get("/api/support-requests", headers=self.admin)
        self.assertEqual(inbox.status_code, 200)
        self.assertTrue(any(item["id"] == request_id for item in inbox.json()))

        open_only = self.client.get("/api/support-requests?status_filter=open", headers=self.admin)
        self.assertTrue(any(item["id"] == request_id for item in open_only.json()))

        resolved = self.client.post(f"/api/support-requests/{request_id}/resolve", headers=self.admin)
        self.assertEqual(resolved.status_code, 200)
        self.assertEqual(resolved.json()["status"], "resolved")
        self.assertEqual(resolved.json()["resolved_by"], "support-admin")

        # Resolving an already-resolved request is refused, not silently repeated.
        self.assertEqual(self.client.post(f"/api/support-requests/{request_id}/resolve", headers=self.admin).status_code, 409)

        still_open = self.client.get("/api/support-requests?status_filter=open", headers=self.admin)
        self.assertFalse(any(item["id"] == request_id for item in still_open.json()))


if __name__ == "__main__":
    unittest.main()
