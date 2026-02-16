"""FastAPI auth dependencies — JWT + RBAC."""

import os
from typing import Annotated, Callable

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from oncology_common.auth.jwt import JWTValidator, TokenPayload

security = HTTPBearer(auto_error=False)

# Dev-mode auth bypass: when ENVIRONMENT=development, skip JWT validation
_DEV_MODE = os.getenv("ENVIRONMENT", "").lower() == "development"

_DEV_USER = TokenPayload(
    sub="dev-user",
    email="dev@lchai.local",
    name="Development User",
    realm_roles=["clinician", "admin", "auditor"],
    exp=9999999999,
    iat=0,
)


async def get_current_user(
    request: Request,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(security)],
) -> TokenPayload:
    """Extract and validate JWT, return token payload."""
    # Development bypass — no JWT required
    if _DEV_MODE:
        return _DEV_USER

    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    jwt_validator: JWTValidator | None = getattr(
        request.app.state, "jwt_validator", None
    )
    if not jwt_validator:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="JWT validator not configured",
        )

    try:
        payload = await jwt_validator.validate_token(credentials.credentials)
        if payload.is_expired:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token expired",
                headers={"WWW-Authenticate": "Bearer"},
            )
        return payload
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
            headers={"WWW-Authenticate": "Bearer"},
        ) from e


def require_roles(*required_roles: str) -> Callable:
    """Dependency factory for RBAC.

    Usage::

        @router.get("/admin", dependencies=[Depends(require_roles("admin"))])
        async def admin_only(): ...
    """

    async def _checker(
        current_user: Annotated[TokenPayload, Depends(get_current_user)],
    ) -> TokenPayload:
        # In dev mode, skip role check
        if _DEV_MODE:
            return _DEV_USER
        if not set(required_roles).intersection(current_user.roles):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Required roles: {', '.join(required_roles)}",
            )
        return current_user

    return _checker
