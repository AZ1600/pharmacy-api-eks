import os


class Settings:
    TABLE_NAME = os.getenv(
        "TABLE_NAME",
        "pharmacy-table",
    )

    AWS_REGION = os.getenv(
        "AWS_DEFAULT_REGION",
        "eu-west-2",
    )

    LOW_STOCK_QUEUE_URL = os.getenv(
        "LOW_STOCK_QUEUE_URL",
        "",
    )

    EVENT_BUS_NAME = os.getenv(
        "EVENT_BUS_NAME",
        "default",
    )

    # OIDC / JWT authentication
    OIDC_ISSUER = os.getenv(
        "OIDC_ISSUER",
        "",
    ).rstrip("/")

    OIDC_CLIENT_ID = os.getenv(
        "OIDC_CLIENT_ID",
        "",
    )

    OIDC_JWKS_URL = os.getenv(
        "OIDC_JWKS_URL",
        "",
    )

    OIDC_TENANT_CLAIM = os.getenv(
        "OIDC_TENANT_CLAIM",
        "custom:tenant_id",
    )

    OIDC_ROLE_CLAIM = os.getenv(
        "OIDC_ROLE_CLAIM",
        "custom:role",
    )

    @property
    def resolved_jwks_url(self) -> str:
        if self.OIDC_JWKS_URL:
            return self.OIDC_JWKS_URL

        if not self.OIDC_ISSUER:
            return ""

        return (
            f"{self.OIDC_ISSUER}/"
            ".well-known/jwks.json"
        )


settings = Settings()