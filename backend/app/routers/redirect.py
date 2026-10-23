from fastapi import APIRouter, BackgroundTasks, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy import select

from app import cache, clicks, tracking
from app.cache import CachedLink
from app.deps import Session
from app.models import Link

router = APIRouter(tags=["redirect"])

_PAGE = """<!doctype html><html><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>{title} · SnapURL</title>
<style>body{{font-family:system-ui,sans-serif;display:grid;place-items:center;min-height:100vh;margin:0;
background:#0b0d12;color:#e6e8ee}}main{{text-align:center;padding:24px}}h1{{font-size:20px;margin:0 0 8px}}
p{{color:#9aa3b2;margin:0}}</style></head><body><main><h1>{title}</h1><p>{body}</p></main></body></html>"""


def _page(status: int, title: str, body: str) -> HTMLResponse:
    return HTMLResponse(_PAGE.format(title=title, body=body), status_code=status)


async def resolve(session: Session, code: str) -> CachedLink | None:
    hit = await cache.get(code)
    if hit is False:
        return None
    if hit is not None:
        return hit
    link = await session.scalar(select(Link).where(Link.code == code))
    if link is None:
        await cache.put(code, None)
        return None
    entry = CachedLink(
        id=link.id,
        url=link.target_url,
        active=link.is_active,
        expires_at=link.expires_at.isoformat() if link.expires_at else None,
    )
    await cache.put(code, entry)
    return entry


@router.api_route("/{code}", methods=["GET", "HEAD"], include_in_schema=True, summary="Follow a short link")
async def follow(code: str, request: Request, background: BackgroundTasks, session: Session):
    if len(code) > 32:
        return _page(404, "Link not found", "This short link doesn't exist.")
    link = await resolve(session, code)
    if link is None:
        return _page(404, "Link not found", "This short link doesn't exist.")
    if not link.is_live():
        return _page(410, "Link unavailable", "This short link has expired or was turned off by its owner.")

    if request.method == "GET":
        # Enqueued after the response is sent, so analytics never add redirect latency.
        background.add_task(clicks.enqueue, tracking.capture(request, link.id))
    # 302 + no-store (not 301) so browsers ask us every time and every click is counted.
    return RedirectResponse(link.url, status_code=302, headers={"Cache-Control": "private, no-store"})
