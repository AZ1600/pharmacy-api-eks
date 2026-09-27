from dataclasses import dataclass
from functools import lru_cache
from typing import Any

import jwt
from fastapi import (
    Depends,
    HTTPException,
    status,
)
from fastapi.security import (
    HTTPAuthorizationCredentials,
    HTTPBearer,
)
from jwt import PyJWKClient
from jwt.exceptions import PyJWTError

from app.core.config import settings


bearer_scheme = HTTPBearer(
    auto_error=False
)


@dataclass(frozen=True)
class Principal:
    user_id: str
    tenant_id: str
    role: str | None
    claims: dict[str, Any]


def _authentication_not_configured():
    raise HTTPException(
        status_code=(
            status.HTTP_503_SERVICE_UNAVAILABLE
        ),
        detail=(
            "OIDC authentication is not "
            "configured."
        ),
    )


def _unauthorized(
    detail: str = "Authentication failed.",
):
    raise HTTPException(
        status_code=(
            status.HTTP_401_UNAUTHORIZED
        ),
        detail=detail,
        headers={
            "WWW-Authenticate": "Bearer",
        },
    )


def _forbidden(
    detail: str,
):
    raise HTTPException(
        status_code=(
            status.HTTP_403_FORBIDDEN
        ),
        detail=detail,
    )


def _ensure_authentication_configured():
    if not settings.OIDC_ISSUER:
        _authentication_not_configured()

    if not settings.OIDC_CLIENT_ID:
        _authentication_not_configured()

    if not settings.resolved_jwks_url:
        _authentication_not_configured()


@lru_cache(maxsize=4)
def _get_jwks_client(
    jwks_url: str,
) -> PyJWKClient:
    return PyJWKClient(
        jwks_url,
        cache_keys=True,
    )


def _get_signing_key(
    token: str,
):
    client = _get_jwks_client(
        settings.resolved_jwks_url
    )

    return (
        client
        .get_signing_key_from_jwt(token)
        .key
    )


def _validate_client_binding(
    claims: dict[str, Any],
):
    expected_client_id = (
        settings.OIDC_CLIENT_ID
    )

    audience = claims.get("aud")
    client_id = claims.get("client_id")

    audience_matches = False

    if isinstance(audience, list):
        audience_matches = (
            expected_client_id in audience
        )

    elif isinstance(audience, str):
        audience_matches = (
            audience == expected_client_id
        )

    client_id_matches = (
        client_id == expected_client_id
    )

    if not (
        audience_matches
        or client_id_matches
    ):
        _unauthorized(
            "JWT client or audience "
            "validation failed."
        )


def _group_value(
    claims: dict[str, Any],
    prefix: str,
) -> str | None:
    groups = claims.get(
        "cognito:groups",
        [],
    )

    if not isinstance(groups, list):
        return None

    for group in groups:
        if (
            isinstance(group, str)
            and group.startswith(prefix)
        ):
            return group[
                len(prefix):
            ]

    return None


def validate_token(
    token: str,
) -> Principal:
    _ensure_authentication_configured()

    try:
        signing_key = _get_signing_key(
            token
        )

        claims = jwt.decode(
            token,
            signing_key,
            algorithms=["RS256"],
            issuer=settings.OIDC_ISSUER,
            options={
                "verify_aud": False,
                "require": [
                    "exp",
                    "iat",
                    "iss",
                    "sub",
                ],
            },
        )

    except PyJWTError:
        _unauthorized(
            "JWT validation failed."
        )

    except Exception:
        _unauthorized(
            "Unable to validate JWT."
        )

    _validate_client_binding(
        claims
    )

    token_use = claims.get(
        "token_use"
    )

    if (
        token_use is not None
        and token_use != "access"
    ):
        _unauthorized(
            "JWT is not an access token."
        )

    user_id = claims.get("sub")

    tenant_id = (
        claims.get(
            settings.OIDC_TENANT_CLAIM
        )
        or _group_value(
            claims,
            "tenant-",
        )
    )

    role = (
        claims.get(
            settings.OIDC_ROLE_CLAIM
        )
        or _group_value(
            claims,
            "role-",
        )
    )

    if not user_id:
        _forbidden(
            "JWT does not contain "
            "a subject claim."
        )

    if not tenant_id:
        _forbidden(
            "JWT does not contain "
            "the required tenant identity."
        )

    return Principal(
        user_id=user_id,
        tenant_id=tenant_id,
        role=role,
        claims=claims,
    )


def get_current_principal(
    credentials:
        HTTPAuthorizationCredentials
        | None = Depends(
            bearer_scheme
        ),
) -> Principal:
    _ensure_authentication_configured()

    if credentials is None:
        _unauthorized(
            "Bearer token is required."
        )

    if (
        credentials.scheme.lower()
        != "bearer"
    ):
        _unauthorized(
            "Bearer authentication "
            "is required."
        )

    return validate_token(
        credentials.credentials
    )