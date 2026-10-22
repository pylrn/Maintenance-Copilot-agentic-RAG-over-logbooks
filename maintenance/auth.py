"""Signed anonymous identities. Session authorization remains an owned DB lookup."""

from uuid import UUID, uuid4

from fastapi import HTTPException, Request, Response
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer

COOKIE_NAME = "maintenance_owner"


class IdentitySigner:
    def __init__(self, secret: str, max_age: int = 86400 * 30):
        if len(secret) < 32:
            raise ValueError("signing secret requires at least 32 characters")
        self.serializer = URLSafeTimedSerializer(secret, salt="maintenance-owner/v1")
        self.max_age = max_age

    def dumps(self, owner_id: UUID) -> str:
        return self.serializer.dumps(str(owner_id))

    def loads(self, token: str) -> UUID | None:
        try:
            return UUID(self.serializer.loads(token, max_age=self.max_age))
        except (BadSignature, SignatureExpired, ValueError, TypeError):
            return None


def check_origin(request: Request):
    if request.method in {"POST", "PUT", "PATCH", "DELETE"}:
        origin = request.headers.get("origin")
        # Cookie-authenticated browser mutations must provide exact origin.
        allowed = {request.app.state.settings.app_origin, *request.app.state.settings.additional_app_origins}
        if origin not in allowed:
            raise HTTPException(403, "origin_not_allowed")
        mime = request.headers.get("content-type", "").split(";")[0]
        if mime not in {"application/json", "multipart/form-data"}:
            raise HTTPException(415, "unsupported_content_type")


async def require_owner(request: Request, response: Response) -> UUID:
    check_origin(request)
    signer = request.app.state.identity_signer
    token = request.cookies.get(COOKIE_NAME)
    owner = signer.loads(token) if token else None
    if token and owner is None:
        raise HTTPException(401, "identity_expired")
    if owner is None:
        owner = uuid4()
        response.set_cookie(
            COOKIE_NAME,
            signer.dumps(owner),
            httponly=True,
            secure=(request.app.state.settings.app_env == "production"
                    or request.url.scheme == "https"
                    or request.headers.get("x-forwarded-proto") == "https"),
            samesite="strict",
            max_age=signer.max_age,
        )
    return owner


async def require_session_owner(pool, session_id: UUID, owner_id: UUID):
    row = await pool.fetchrow(
        "SELECT * FROM sessions WHERE session_id=$1 AND owner_id=$2", session_id, owner_id
    )
    if row is None:
        raise HTTPException(404, "session_not_found")
    return row
