import time
import unittest
from unittest.mock import patch

import jwt
from cryptography.hazmat.primitives.asymmetric import (
    rsa,
)
from fastapi.testclient import TestClient

from app.core.config import settings
from app.main import app


class TestAuthenticatedRoutes(
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

        cls.client = TestClient(
            app
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
        include_tenant=True,
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
            "custom:role":
                "HospitalAdmin",
        }

        if include_tenant:
            claims[
                "custom:tenant_id"
            ] = "tenant-001"

        return jwt.encode(
            claims,
            self.private_key,
            algorithm="RS256",
            headers={
                "kid": "test-key",
            },
        )

    def auth_headers(
        self,
        token,
    ):
        return {
            "Authorization":
                f"Bearer {token}",
        }

    def test_health_remains_public(
        self,
    ):
        response = self.client.get(
            "/health"
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        self.assertEqual(
            response.json(),
            {
                "status": "ok",
            },
        )

    def test_create_drug_without_token_returns_401(
        self,
    ):
        response = self.client.post(
            "/drugs",
            json={
                "drug_name":
                    "Amoxicillin",
                "batch_number":
                    "AMX-001",
                "quantity": 50,
                "reorder_level": 10,
                "expiry_date":
                    "2027-12-31",
                "supplier":
                    "Demo Supplier",
            },
        )

        self.assertEqual(
            response.status_code,
            401,
        )

    def test_missing_tenant_claim_returns_403(
        self,
    ):
        token = self.create_token(
            include_tenant=False
        )

        response = self.client.post(
            "/drugs",
            headers=self.auth_headers(
                token
            ),
            json={
                "drug_name":
                    "Amoxicillin",
                "batch_number":
                    "AMX-001",
                "quantity": 50,
                "reorder_level": 10,
                "expiry_date":
                    "2027-12-31",
                "supplier":
                    "Demo Supplier",
            },
        )

        self.assertEqual(
            response.status_code,
            403,
        )

    def test_auth_me_returns_identity_claims(
        self,
    ):
        token = self.create_token()

        response = self.client.get(
            "/auth/me",
            headers=self.auth_headers(
                token
            ),
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        body = response.json()

        self.assertTrue(
            body["authenticated"]
        )

        self.assertEqual(
            body["user_id"],
            "user-123",
        )

        self.assertEqual(
            body["tenant_id"],
            "tenant-001",
        )

        self.assertEqual(
            body["role"],
            "HospitalAdmin",
        )

    @patch(
        "app.api.routes."
        "create_drug_service"
    )
    def test_valid_token_passes_identity_to_service(
        self,
        mock_create_drug,
    ):
        mock_create_drug.return_value = {
            "message":
                "Drug created successfully",
            "data": {
                "id": "drug-123",
            },
        }

        token = self.create_token()

        response = self.client.post(
            "/drugs",
            headers=self.auth_headers(
                token
            ),
            json={
                "drug_name":
                    "Amoxicillin",
                "batch_number":
                    "AMX-001",
                "quantity": 50,
                "reorder_level": 10,
                "expiry_date":
                    "2027-12-31",
                "supplier":
                    "Demo Supplier",
            },
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        mock_create_drug.assert_called_once()

        _, kwargs = (
            mock_create_drug.call_args
        )

        self.assertEqual(
            kwargs["tenant_id"],
            "tenant-001",
        )

        self.assertEqual(
            kwargs["user_id"],
            "user-123",
        )


if __name__ == "__main__":
    unittest.main()