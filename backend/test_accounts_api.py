import os
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient

import backend.app as app_module
from backend.app import app, store
from backend.google_auth import GoogleIdentity


def auth(actor: str, role: str) -> dict[str, str]:
    return {"Authorization": f"Bearer test:{actor}:{role}"}


def _fake_google_client(email: str, name: str = "Pat Example", picture: str | None = None):
    class _FakeGoogleClient:
        def __init__(self, settings):
            pass

        def exchange(self, code, redirect_uri):
            return GoogleIdentity(email=email, name=name, picture=picture)

    return _FakeGoogleClient


@unittest.skipUnless(os.getenv("STUDIO_TEST_DATABASE_URL"), "Set STUDIO_TEST_DATABASE_URL for PostgreSQL API tests")
class GoogleAccountsIntegrationTests(unittest.TestCase):
    def setUp(self) -> None:
        store.reset()
        os.environ["STUDIO_TEST_MODE"] = "true"
        os.environ["STUDIO_PERSISTENCE"] = "postgres"
        os.environ["STUDIO_DATABASE_URL"] = os.environ["STUDIO_TEST_DATABASE_URL"]
        os.environ["STUDIO_GOOGLE_ENABLED"] = "true"
        os.environ["STUDIO_GOOGLE_CLIENT_ID"] = "test-client-id"
        os.environ["STUDIO_GOOGLE_CLIENT_SECRET"] = "test-client-secret"
        os.environ["STUDIO_SESSION_SECRET"] = "a-sufficiently-long-test-session-secret"
        app_module.postgres_repository.cache_clear()
        app_module.postgres_repository().migrate()
        self.client = TestClient(app)
        self.admin = auth("accounts-admin", "admin")
        self.reviewer = auth("accounts-reviewer", "reviewer")

    def tearDown(self) -> None:
        for key in ["STUDIO_PERSISTENCE", "STUDIO_DATABASE_URL", "STUDIO_GOOGLE_ENABLED", "STUDIO_GOOGLE_CLIENT_ID", "STUDIO_GOOGLE_CLIENT_SECRET", "STUDIO_SESSION_SECRET"]:
            os.environ.pop(key, None)
        app_module.postgres_repository.cache_clear()

    def _sign_in(self, email: str, name: str = "Pat Example") -> dict:
        with patch("backend.app.GoogleOAuthClient", _fake_google_client(email, name)):
            response = self.client.post("/api/auth/google", json={"code": "irrelevant", "redirect_uri": "https://studio.example.com/sso-callback"})
        self.assertEqual(response.status_code, 200)
        return response.json()

    def test_sign_in_is_refused_when_google_is_not_enabled(self):
        os.environ["STUDIO_GOOGLE_ENABLED"] = "false"
        response = self.client.post("/api/auth/google", json={"code": "irrelevant", "redirect_uri": "https://studio.example.com/sso-callback"})
        self.assertEqual(response.status_code, 503)

    def test_a_new_google_sign_in_creates_a_pending_account_with_no_access(self):
        body = self._sign_in("new-person@example.com")
        self.assertTrue(body["pending"])
        self.assertIsNone(body["role"])
        self.assertEqual(body["email"], "new-person@example.com")

        session_header = {"Authorization": f"Bearer studio:{body['access_token']}"}
        me = self.client.get("/api/me", headers=session_header)
        self.assertEqual(me.status_code, 200)
        self.assertEqual(me.json()["roles"], [])
        self.assertEqual(me.json()["authentication"], "google")

        denied = self.client.get("/api/referral-links", headers=session_header)
        self.assertEqual(denied.status_code, 403)

    def test_an_unverified_or_malformed_session_token_is_rejected(self):
        response = self.client.get("/api/me", headers={"Authorization": "Bearer studio:not-a-real-jwt"})
        self.assertEqual(response.status_code, 401)

    def test_only_an_admin_may_list_or_assign_accounts(self):
        self._sign_in("pending-person@example.com")
        denied_list = self.client.get("/api/accounts", headers=self.reviewer)
        self.assertEqual(denied_list.status_code, 403)

        pending = self.client.get("/api/accounts?role=pending", headers=self.admin)
        self.assertEqual(pending.status_code, 200)
        row = next(item for item in pending.json() if item["email"] == "pending-person@example.com")

        denied_assign = self.client.post(f"/api/accounts/{row['id']}/role", headers=self.reviewer, json={"role": "client"})
        self.assertEqual(denied_assign.status_code, 403)

        assigned = self.client.post(f"/api/accounts/{row['id']}/role", headers=self.admin, json={"role": "client"})
        self.assertEqual(assigned.status_code, 200)
        self.assertEqual(assigned.json()["global_role"], "client")

    def test_assigning_a_role_unlocks_access_on_the_next_sign_in(self):
        self._sign_in("future-client@example.com")
        account = next(item for item in self.client.get("/api/accounts", headers=self.admin).json() if item["email"] == "future-client@example.com")
        self.client.post(f"/api/accounts/{account['id']}/role", headers=self.admin, json={"role": "client"})

        body = self._sign_in("future-client@example.com")
        self.assertFalse(body["pending"])
        self.assertEqual(body["role"], "client")

        session_header = {"Authorization": f"Bearer studio:{body['access_token']}"}
        me = self.client.get("/api/me", headers=session_header)
        self.assertEqual(me.json()["roles"], ["client"])

    def test_assigning_a_role_to_an_unknown_account_is_404(self):
        response = self.client.post(
            "/api/accounts/00000000-0000-0000-0000-000000000099/role",
            headers=self.admin,
            json={"role": "client"},
        )
        self.assertEqual(response.status_code, 404)

    def test_signing_in_twice_refreshes_the_profile_without_creating_a_second_account(self):
        self._sign_in("repeat-person@example.com", name="First Name")
        self._sign_in("repeat-person@example.com", name="Updated Name")
        matches = [item for item in self.client.get("/api/accounts", headers=self.admin).json() if item["email"] == "repeat-person@example.com"]
        self.assertEqual(len(matches), 1)
        self.assertEqual(matches[0]["name"], "Updated Name")


if __name__ == "__main__":
    unittest.main()
