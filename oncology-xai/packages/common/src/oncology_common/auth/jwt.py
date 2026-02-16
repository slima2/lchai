"""JWT validation with JWKS support for Keycloak."""

import asyncio
from datetime import datetime, timezone
from typing import Any

import httpx
from jose import JWTError, jwt
from pydantic import BaseModel, Field
from tenacity import retry, stop_after_attempt, wait_exponential


class TokenPayload(BaseModel):
    """Decoded JWT token payload."""

    sub: str
    exp: int
    iat: int
    iss: str | None = None
    aud: str | list[str] | None = None
    realm_roles: list[str] = Field(default_factory=list)
    client_roles: list[str] = Field(default_factory=list)
    email: str | None = None
    preferred_username: str | None = None
    name: str | None = None

    @property
    def user_id(self) -> str:
        return self.sub

    @property
    def roles(self) -> list[str]:
        return list(set(self.realm_roles + self.client_roles))

    @property
    def is_expired(self) -> bool:
        return datetime.now(timezone.utc).timestamp() > self.exp


class JWTValidator:
    """JWT validator with JWKS caching."""

    def __init__(
        self,
        jwks_url: str,
        audience: str | None = None,
        issuer: str | None = None,
        cache_ttl: int = 3600,
    ):
        self.jwks_url = jwks_url
        self.audience = audience
        self.issuer = issuer
        self.cache_ttl = cache_ttl
        self._jwks: dict[str, Any] | None = None
        self._jwks_fetched_at: float = 0
        self._lock = asyncio.Lock()

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=10))
    async def _fetch_jwks(self) -> dict[str, Any]:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(self.jwks_url)
            resp.raise_for_status()
            return resp.json()

    async def get_jwks(self) -> dict[str, Any]:
        now = datetime.now(timezone.utc).timestamp()
        async with self._lock:
            if self._jwks is None or (now - self._jwks_fetched_at) > self.cache_ttl:
                self._jwks = await self._fetch_jwks()
                self._jwks_fetched_at = now
            return self._jwks

    def _find_key(self, jwks: dict[str, Any], kid: str) -> dict | None:
        for key in jwks.get("keys", []):
            if key.get("kid") == kid:
                return key
        return None

    async def validate_token(self, token: str) -> TokenPayload:
        try:
            header = jwt.get_unverified_header(token)
            kid = header.get("kid")
            if not kid:
                raise JWTError("Missing kid")

            jwks = await self.get_jwks()
            key = self._find_key(jwks, kid)
            if not key:
                self._jwks = None
                jwks = await self.get_jwks()
                key = self._find_key(jwks, kid)
                if not key:
                    raise JWTError(f"Key not found: {kid}")

            payload = jwt.decode(
                token, key, algorithms=["RS256"],
                audience=self.audience, issuer=self.issuer,
                options={
                    "verify_aud": self.audience is not None,
                    "verify_iss": self.issuer is not None,
                },
            )

            realm_roles = payload.get("realm_access", {}).get("roles", [])
            client_roles = payload.get("resource_access", {}).get(
                "oncology-api", {}
            ).get("roles", [])

            return TokenPayload(
                sub=payload["sub"],
                exp=payload["exp"],
                iat=payload.get("iat", 0),
                iss=payload.get("iss"),
                aud=payload.get("aud"),
                realm_roles=realm_roles,
                client_roles=client_roles,
                email=payload.get("email"),
                preferred_username=payload.get("preferred_username"),
                name=payload.get("name"),
            )
        except JWTError as e:
            raise ValueError(f"Invalid token: {e}") from e
        except Exception as e:
            raise ValueError(f"Token validation failed: {e}") from e
