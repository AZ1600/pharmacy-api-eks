import time
import unittest
from unittest.mock import patch

import jwt
from cryptography.hazmat.primitives.asymmetric import (
    rsa,
)
from fastapi import HTTPException

from app.core.config import settings
from app.core.security import (
    validate_token,
)


class TestJwtAuthentication(
    unittest.TestCase
):
    @classmethod
    def setUpClass(cls):
        cls.private_key = (
            rsa.generate_private_key(
                public_exponent=65537,
                key_size=2048,
            )
        )

        cls.public_key = (
            cls.private_key.public_key()
        )

    def setUp(self):
        self.issuer = (
            "https://identity.example.com/"
            "test-pool"
        )

        self.client_id = (
            "pharmacy-api-client"
        )

        self.settings_patchers = [
            patch.object(
                settings,
                "OIDC_ISSUER",
                self.issuer,
            ),
            patch.object(
                settings,
                "OIDC_CLIENT_ID",
                self.client_id,
            ),
            patch.object(
                settings,
                "OIDC_JWKS_URL",
                (
                    "https://identity.example.com/"
                    "jwks.json"
                ),
            ),
            patch.object(
                settings,
                "OIDC_TENANT_CLAIM",
                "custom:tenant_id",
            ),
            patch.object(
                settings,
                "OIDC_ROLE_CLAIM",
                "custom:role",
            ),
        ]

        for patcher in (
            self.settings_patchers
        ):
            patcher.start()

        self.key_patcher = patch(
            "app.core.security."
            "_get_signing_key",
            return_value=self.public_key,
        )

        self.key_patcher.start()

    def tearDown(self):
        self.key_patcher.stop()

        for patcher in reversed(
            self.settings_patchers
        ):
            patcher.stop()

    def create_token(
        self,
        **overrides,
    ):
        now = int(time.time())

        claims = {
            "iss": self.issuer,
            "sub": "user-123",
            "client_id":
                self.client_id,
            "token_use": "access",
            "iat": now,
            "exp": now + 300,
            "custom:tenant_id":
                "tenant-001",
            "custom:role":
                "HospitalAdmin",
        }

        claims.update(
            overrides
        )

        return jwt.encode(
            claims,
            self.private_key,
            algorithm="RS256",
            headers={
                "kid": "test-key",
            },
        )

    def test_valid_access_token_returns_principal(
        self,
    ):
        token = self.create_token()

        principal = validate_token(
            token
        )

        self.assertEqual(
            principal.user_id,
            "user-123",
        )

        self.assertEqual(
            principal.tenant_id,
            "tenant-001",
        )

        self.assertEqual(
            principal.role,
            "HospitalAdmin",
        )

    def test_missing_tenant_claim_is_forbidden(
        self,
    ):
        token = self.create_token(
            **{
                "custom:tenant_id":
                    None,
            }
        )

        with self.assertRaises(
            HTTPException
        ) as context:
            validate_token(token)

        self.assertEqual(
            context.exception.status_code,
            403,
        )

    def test_wrong_client_is_unauthorized(
        self,
    ):
        token = self.create_token(
            client_id="wrong-client"
        )

        with self.assertRaises(
            HTTPException
        ) as context:
            validate_token(token)

        self.assertEqual(
            context.exception.status_code,
            401,
        )

    def test_id_token_is_rejected(
        self,
    ):
        token = self.create_token(
            token_use="id"
        )

        with self.assertRaises(
            HTTPException
        ) as context:
            validate_token(token)

        self.assertEqual(
            context.exception.status_code,
            401,
        )

    def test_expired_token_is_rejected(
        self,
    ):
        now = int(time.time())

        token = self.create_token(
            iat=now - 600,
            exp=now - 300,
        )

        with self.assertRaises(
            HTTPException
        ) as context:
            validate_token(token)

        self.assertEqual(
            context.exception.status_code,
            401,
        )


if __name__ == "__main__":
    unittest.main()