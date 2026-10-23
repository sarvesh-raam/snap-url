import uuid
from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Cookie, HTTPException, Request, Response, status
from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError

from app import ratelimit
from app.config import get_settings
from app.deps import CurrentUser, Session
from app.models import RefreshToken, User
from app.schemas import Credentials, TokenOut, UserOut
from app.security import (
    create_access_token,
    hash_password,
    hash_refresh_token,
    new_refresh_token,
    verify_password,
)

router = APIRouter(prefix="/api/auth", tags=["auth"])

COOKIE = "snapurl_refresh"
COOKIE_PATH = "/api/auth"


async def _issue(session: Session, response: Response, user: User, family: uuid.UUID | None = None) -> TokenOut:
    s = get_settings()
    raw, digest = new_refresh_token()
    session.add(
        RefreshToken(
            user_id=user.id,
            token_hash=digest,
            family_id=family or uuid.uuid4(),
            expires_at=datetime.now(UTC) + timedelta(days=s.refresh_token_days),
        )
    )
    await session.commit()
    response.set_cookie(
        COOKIE,
        raw,
        max_age=s.refresh_token_days * 86400,
        httponly=True,
        secure=s.cookie_secure,
        samesite="strict",
        path=COOKIE_PATH,
    )
    return TokenOut(
        access_token=create_access_token(user.id),
        expires_in=s.access_token_minutes * 60,
        user=UserOut.model_validate(user),
    )


@router.post("/register", response_model=TokenOut, status_code=status.HTTP_201_CREATED)
async def register(body: Credentials, request: Request, response: Response, session: Session) -> TokenOut:
    await ratelimit.enforce(ratelimit.ip_key(request, "register"), get_settings().rate_limit_login_per_min)
    user = User(email=body.email.lower(), password_hash=hash_password(body.password))
    session.add(user)
    try:
        await session.flush()
    except IntegrityError:
        await session.rollback()
        raise HTTPException(status.HTTP_409_CONFLICT, "An account with that email already exists") from None
    return await _issue(session, response, user)


@router.post("/login", response_model=TokenOut)
async def login(body: Credentials, request: Request, response: Response, session: Session) -> TokenOut:
    await ratelimit.enforce(ratelimit.ip_key(request, "login"), get_settings().rate_limit_login_per_min)
    user = await session.scalar(select(User).where(User.email == body.email.lower()))
    if not verify_password(body.password, user.password_hash if user else None):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Incorrect email or password")
    return await _issue(session, response, user)


@router.post("/refresh", response_model=TokenOut)
async def refresh(
    response: Response, session: Session, token: str | None = Cookie(default=None, alias=COOKIE)
) -> TokenOut:
    invalid = HTTPException(status.HTTP_401_UNAUTHORIZED, "Session expired, please sign in again")
    if not token:
        raise invalid
    now = datetime.now(UTC)
    row = await session.scalar(
        select(RefreshToken).where(RefreshToken.token_hash == hash_refresh_token(token)).with_for_update()
    )
    if row is None:
        raise invalid
    if row.revoked_at is not None:
        # A rotated token was presented again: someone else has a copy. Kill the whole family.
        await session.execute(
            update(RefreshToken)
            .where(RefreshToken.family_id == row.family_id, RefreshToken.revoked_at.is_(None))
            .values(revoked_at=now)
        )
        await session.commit()
        raise invalid
    if row.expires_at <= now:
        raise invalid
    row.revoked_at = now
    user = await session.get(User, row.user_id)
    return await _issue(session, response, user, family=row.family_id)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(session: Session, token: str | None = Cookie(default=None, alias=COOKIE)) -> Response:
    if token:
        await session.execute(
            update(RefreshToken)
            .where(RefreshToken.token_hash == hash_refresh_token(token), RefreshToken.revoked_at.is_(None))
            .values(revoked_at=datetime.now(UTC))
        )
        await session.commit()
    response = Response(status_code=status.HTTP_204_NO_CONTENT)
    response.delete_cookie(COOKIE, path=COOKIE_PATH)
    return response


@router.get("/me", response_model=UserOut)
async def me(user: CurrentUser) -> User:
    return user
