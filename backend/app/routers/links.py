from datetime import UTC, datetime

from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError

from app import cache, ratelimit
from app.config import get_settings
from app.deps import CurrentUser, Session
from app.models import Link
from app.schemas import LinkCreate, LinkOut, LinkPage, LinkUpdate
from app.shortcode import alias_error, generate_code
from app.urlcheck import normalize_target

router = APIRouter(prefix="/api/links", tags=["links"])

MAX_CODE_ATTEMPTS = 5


def to_out(link: Link) -> LinkOut:
    return LinkOut(
        id=link.id,
        code=link.code,
        short_url=f"{get_settings().base_url.rstrip('/')}/{link.code}",
        target_url=link.target_url,
        title=link.title,
        is_active=link.is_active,
        expires_at=link.expires_at,
        click_count=link.click_count,
        created_at=link.created_at,
        updated_at=link.updated_at,
    )


def _check_url(url: str) -> str:
    try:
        return normalize_target(url)
    except ValueError as e:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, str(e)) from None


def _check_expiry(expires_at: datetime | None) -> None:
    if expires_at is None:
        return
    if expires_at.tzinfo is None:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "expires_at must include a timezone")
    if expires_at <= datetime.now(UTC):
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "expires_at must be in the future")


async def owned_link(session: Session, user_id: int, link_id: int) -> Link:
    link = await session.get(Link, link_id)
    # 404 rather than 403 for other users' links, so IDs don't reveal what exists.
    if link is None or link.user_id != user_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Link not found")
    return link


@router.post("", response_model=LinkOut, status_code=status.HTTP_201_CREATED)
async def create_link(body: LinkCreate, user: CurrentUser, session: Session) -> LinkOut:
    s = get_settings()
    user_id = user.id  # read before any rollback expires the instance
    await ratelimit.enforce(f"create:user:{user_id}", s.rate_limit_create_per_min)
    if s.max_links_per_user:
        owned = await session.scalar(select(func.count()).select_from(Link).where(Link.user_id == user_id))
        if owned >= s.max_links_per_user:
            raise HTTPException(status.HTTP_403_FORBIDDEN, f"This demo allows {s.max_links_per_user} links per account")
    target = _check_url(body.url)
    _check_expiry(body.expires_at)

    if body.alias:
        if err := alias_error(body.alias):
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, err)
        candidates = [body.alias]
    else:
        candidates = [generate_code(s.code_length) for _ in range(MAX_CODE_ATTEMPTS)]

    for code in candidates:
        link = Link(user_id=user_id, code=code, target_url=target, title=body.title, expires_at=body.expires_at)
        session.add(link)
        try:
            await session.commit()
        except IntegrityError:
            # The unique index is the source of truth for collisions; no check-then-insert race.
            await session.rollback()
            continue
        await session.refresh(link)
        await cache.invalidate(code)  # clear a negative-cache entry for this code, if any
        return to_out(link)

    if body.alias:
        raise HTTPException(status.HTTP_409_CONFLICT, "That alias is already taken")
    raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "Could not allocate a short code, try again")


@router.get("", response_model=LinkPage)
async def list_links(
    user: CurrentUser,
    session: Session,
    q: str | None = Query(default=None, max_length=200),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    sort: str = Query(default="recent", pattern="^(recent|clicks)$"),
) -> LinkPage:
    where = [Link.user_id == user.id]
    if q:
        escaped = q.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        pattern = f"%{escaped}%"
        where.append(or_(Link.code.ilike(pattern), Link.target_url.ilike(pattern), Link.title.ilike(pattern)))
    total = await session.scalar(select(func.count()).select_from(Link).where(*where))
    order = (Link.click_count.desc(), Link.id.desc()) if sort == "clicks" else (Link.id.desc(),)
    rows = await session.scalars(
        select(Link).where(*where).order_by(*order).offset((page - 1) * page_size).limit(page_size)
    )
    return LinkPage(items=[to_out(link) for link in rows], total=total or 0, page=page, page_size=page_size)


@router.get("/{link_id}", response_model=LinkOut)
async def get_link(link_id: int, user: CurrentUser, session: Session) -> LinkOut:
    return to_out(await owned_link(session, user.id, link_id))


@router.patch("/{link_id}", response_model=LinkOut)
async def update_link(link_id: int, body: LinkUpdate, user: CurrentUser, session: Session) -> LinkOut:
    link = await owned_link(session, user.id, link_id)
    changes = body.model_dump(exclude_unset=True)
    if "url" in changes:
        if changes["url"] is None:
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "url can't be empty")
        link.target_url = _check_url(changes["url"])
    if "title" in changes:
        link.title = changes["title"]
    if "is_active" in changes and changes["is_active"] is not None:
        link.is_active = changes["is_active"]
    if "expires_at" in changes:
        _check_expiry(changes["expires_at"])
        link.expires_at = changes["expires_at"]
    await session.commit()
    await session.refresh(link)
    await cache.invalidate(link.code)
    return to_out(link)


@router.delete("/{link_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_link(link_id: int, user: CurrentUser, session: Session) -> None:
    link = await owned_link(session, user.id, link_id)
    code = link.code
    await session.delete(link)
    await session.commit()
    await cache.invalidate(code)
