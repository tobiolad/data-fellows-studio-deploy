import time
import unittest

import jwt
from cryptography.hazmat.primitives.asymmetric import rsa

from backend.auth import EntraSettings, EntraTokenValidator, TokenValidationError


class StaticProvider:
    def __init__(self, key):
        self.key = key

    def key_for(self, key_id: str):
        if key_id != "test-key":
            raise TokenValidationError("unknown key")
        return self.key


class EntraTokenTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        cls.settings = EntraSettings(
            tenant_id="synthetic-tenant",
            audience="api://studio",
            issuer="https://issuer.example/synthetic-tenant/v2.0",
            jwks_url="https://issuer.example/keys",
        )
        cls.validator = EntraTokenValidator(cls.settings, StaticProvider(cls.private_key.public_key()))

    def token(self, **overrides):
        claims = {
            "iss": self.settings.issuer,
            "aud": self.settings.audience,
            "tid": self.settings.tenant_id,
            "oid": "staff-1",
            "sub": "subject-1",
            "iat": int(time.time()),
            "exp": int(time.time()) + 300,
            "roles": ["Reviewer"],
        }
        claims.update(overrides)
        return jwt.encode(claims, self.private_key, algorithm="RS256", headers={"kid": "test-key"})

    def test_valid_token_returns_identity_metadata(self) -> None:
        principal = self.validator.validate(self.token())
        self.assertEqual(principal.actor_id, "staff-1")
        self.assertEqual(principal.tenant_id, "synthetic-tenant")
        self.assertEqual(principal.roles, {"Reviewer"})

    def test_wrong_audience_is_rejected(self) -> None:
        with self.assertRaises(TokenValidationError):
            self.validator.validate(self.token(aud="api://other"))

    def test_wrong_tenant_is_rejected(self) -> None:
        with self.assertRaises(TokenValidationError):
            self.validator.validate(self.token(tid="other-tenant"))

    def test_token_roles_do_not_replace_membership_checks(self) -> None:
        principal = self.validator.validate(self.token(roles=["Administrator"]))
        self.assertIn("Administrator", principal.roles)
        self.assertEqual(principal.actor_id, "staff-1")


if __name__ == "__main__":
    unittest.main()
