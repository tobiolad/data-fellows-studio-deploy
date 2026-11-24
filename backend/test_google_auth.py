import os
import time
import unittest
from unittest.mock import patch

import jwt

from backend import google_auth


def _settings() -> google_auth.GoogleOAuthSettings:
    return google_auth.GoogleOAuthSettings(client_id="studio-client", client_secret="studio-secret")


class GoogleOAuthSettingsTests(unittest.TestCase):
    def test_requires_both_client_id_and_secret(self):
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("STUDIO_GOOGLE_CLIENT_ID", None)
            os.environ.pop("STUDIO_GOOGLE_CLIENT_SECRET", None)
            with self.assertRaises(google_auth.GoogleAuthError):
                google_auth.GoogleOAuthSettings.from_environment()

    def test_reads_both_values_from_environment(self):
        with patch.dict(os.environ, {"STUDIO_GOOGLE_CLIENT_ID": "id-1", "STUDIO_GOOGLE_CLIENT_SECRET": "secret-1"}):
            settings = google_auth.GoogleOAuthSettings.from_environment()
            self.assertEqual(settings.client_id, "id-1")
            self.assertEqual(settings.client_secret, "secret-1")


class GoogleOAuthClientTests(unittest.TestCase):
    def setUp(self) -> None:
        self.client = google_auth.GoogleOAuthClient(_settings())

    def _stub_responses(self, token_response: dict, userinfo_response: dict):
        def fake_send(request):
            if request.full_url == self.client.token_endpoint:
                return token_response
            if request.full_url == self.client.userinfo_endpoint:
                return userinfo_response
            raise AssertionError(f"Unexpected URL {request.full_url}")
        return patch.object(self.client, "_send", side_effect=fake_send)

    def test_exchange_returns_identity_for_a_verified_email(self):
        with self._stub_responses(
            {"access_token": "token-abc"},
            {"email": "person@example.com", "verified_email": True, "name": "Person Example", "picture": "https://example.com/p.png"},
        ):
            identity = self.client.exchange("auth-code", "https://studio.example.com/sso-callback")
        self.assertEqual(identity.email, "person@example.com")
        self.assertEqual(identity.name, "Person Example")
        self.assertEqual(identity.picture, "https://example.com/p.png")

    def test_exchange_rejects_an_unverified_email(self):
        with self._stub_responses(
            {"access_token": "token-abc"},
            {"email": "person@example.com", "verified_email": False},
        ):
            with self.assertRaises(google_auth.GoogleAuthError):
                self.client.exchange("auth-code", "https://studio.example.com/sso-callback")

    def test_exchange_rejects_a_missing_verified_email_field(self):
        with self._stub_responses({"access_token": "token-abc"}, {"email": "person@example.com"}):
            with self.assertRaises(google_auth.GoogleAuthError):
                self.client.exchange("auth-code", "https://studio.example.com/sso-callback")

    def test_exchange_rejects_a_missing_access_token(self):
        with self._stub_responses({}, {}):
            with self.assertRaises(google_auth.GoogleAuthError):
                self.client.exchange("auth-code", "https://studio.example.com/sso-callback")

    def test_exchange_rejects_an_empty_code(self):
        with self.assertRaises(google_auth.GoogleAuthError):
            self.client.exchange("", "https://studio.example.com/sso-callback")


class SessionTokenTests(unittest.TestCase):
    def setUp(self) -> None:
        self._env = patch.dict(os.environ, {"STUDIO_SESSION_SECRET": "a-test-session-secret"})
        self._env.start()

    def tearDown(self) -> None:
        self._env.stop()

    def test_round_trip_carries_the_account_and_role(self):
        token = google_auth.issue_session_token("account-1", "person@example.com", "client")
        principal = google_auth.validate_session_token(token)
        self.assertEqual(principal.actor_id, "account-1")
        self.assertEqual(principal.email, "person@example.com")
        self.assertEqual(principal.roles, frozenset({"client"}))

    def test_a_pending_account_validates_to_an_empty_role_set(self):
        token = google_auth.issue_session_token("account-2", "pending@example.com", None)
        principal = google_auth.validate_session_token(token)
        self.assertEqual(principal.roles, frozenset())

    def test_requires_the_session_secret_to_be_configured(self):
        os.environ.pop("STUDIO_SESSION_SECRET", None)
        with self.assertRaises(google_auth.GoogleAuthError):
            google_auth.issue_session_token("account-1", "person@example.com", "client")

    def test_rejects_a_token_signed_with_a_different_secret(self):
        token = jwt.encode(
            {"purpose": "studio-google-session", "sub": "account-1", "email": "x@example.com", "role": "admin",
             "iat": time.time(), "exp": time.time() + 3600},
            "a-different-secret",
            algorithm="HS256",
        )
        with self.assertRaises(google_auth.GoogleAuthError):
            google_auth.validate_session_token(token)

    def test_rejects_an_expired_token(self):
        token = jwt.encode(
            {"purpose": "studio-google-session", "sub": "account-1", "email": "x@example.com", "role": "admin",
             "iat": time.time() - 7200, "exp": time.time() - 3600},
            "a-test-session-secret",
            algorithm="HS256",
        )
        with self.assertRaises(google_auth.GoogleAuthError):
            google_auth.validate_session_token(token)

    def test_rejects_a_token_issued_for_a_different_purpose(self):
        token = jwt.encode(
            {"purpose": "some-other-purpose", "sub": "account-1", "email": "x@example.com", "role": "admin",
             "iat": time.time(), "exp": time.time() + 3600},
            "a-test-session-secret",
            algorithm="HS256",
        )
        with self.assertRaises(google_auth.GoogleAuthError):
            google_auth.validate_session_token(token)

    def test_rejects_an_empty_token(self):
        with self.assertRaises(google_auth.GoogleAuthError):
            google_auth.validate_session_token("")


if __name__ == "__main__":
    unittest.main()
