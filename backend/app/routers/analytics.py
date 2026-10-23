from datetime import UTC, date, datetime, timedelta

from fastapi import APIRouter, Query
from sqlalchemy import func, select, text

from app.deps import CurrentUser, Session
from app.models import Link
from app.routers.links import owned_link, to_out
from app.schemas import CountRow, DayRow, LinkStats, Overview

router = APIRouter(prefix="/api", tags=["analytics"])

TOP_N = 10

# Column name -> label used when the value is NULL. Interpolated into SQL, so it is a closed set.
BREAKDOWNS = {"country": "Unknown", "device": "Unknown", "browser": "Unknown", "os": "Unknown", "referrer": "Direct"}


def _since(days: int) -> tuple[date, datetime]:
    first_day = datetime.now(UTC).date() - timedelta(days=days - 1)
    return first_day, datetime(first_day.year, first_day.month, first_day.day, tzinfo=UTC)


def _fill_days(first_day: date, days: int, rows) -> list[DayRow]:
    by_day = {r.day: r for r in rows}
    out = []
    for i in range(days):
        d = first_day + timedelta(days=i)
        r = by_day.get(d)
        out.append(DayRow(date=d, clicks=r.clicks if r else 0, visitors=r.visitors if r else 0))
    return out


async def _breakdown(session: Session, column: str, link_id: int, since: datetime) -> list[CountRow]:
    null_label = BREAKDOWNS[column]
    rows = await session.execute(
        text(
            f"""
            SELECT coalesce({column}, :null_label) AS key, count(*) AS count
            FROM clicks
            WHERE link_id = :link_id AND clicked_at >= :since AND NOT is_bot
            GROUP BY 1 ORDER BY 2 DESC, 1 LIMIT :n
            """
        ),
        {"null_label": null_label, "link_id": link_id, "since": since, "n": TOP_N},
    )
    return [CountRow(key=r.key, count=r.count) for r in rows]


@router.get("/links/{link_id}/stats", response_model=LinkStats)
async def link_stats(
    link_id: int, user: CurrentUser, session: Session, days: int = Query(default=30, ge=1, le=365)
) -> LinkStats:
    await owned_link(session, user.id, link_id)
    first_day, since = _since(days)
    params = {"link_id": link_id, "since": since}

    totals = (
        await session.execute(
            text(
                """
                SELECT count(*) FILTER (WHERE NOT is_bot) AS clicks,
                       count(DISTINCT (visitor_hash, (clicked_at AT TIME ZONE 'UTC')::date))
                           FILTER (WHERE NOT is_bot) AS visitors,
                       count(*) FILTER (WHERE is_bot) AS bots
                FROM clicks WHERE link_id = :link_id AND clicked_at >= :since
                """
            ),
            params,
        )
    ).one()
    series = await session.execute(
        text(
            """
            SELECT (clicked_at AT TIME ZONE 'UTC')::date AS day, count(*) AS clicks,
                   count(DISTINCT visitor_hash) AS visitors
            FROM clicks WHERE link_id = :link_id AND clicked_at >= :since AND NOT is_bot
            GROUP BY 1
            """
        ),
        params,
    )
    return LinkStats(
        link_id=link_id,
        days=days,
        total_clicks=totals.clicks,
        unique_visitors=totals.visitors,
        bot_clicks=totals.bots,
        timeseries=_fill_days(first_day, days, series),
        countries=await _breakdown(session, "country", link_id, since),
        devices=await _breakdown(session, "device", link_id, since),
        browsers=await _breakdown(session, "browser", link_id, since),
        os=await _breakdown(session, "os", link_id, since),
        referrers=await _breakdown(session, "referrer", link_id, since),
    )


@router.get("/stats/overview", response_model=Overview)
async def overview(user: CurrentUser, session: Session, days: int = Query(default=30, ge=1, le=365)) -> Overview:
    first_day, since = _since(days)
    counts = (
        await session.execute(
            select(
                func.count(Link.id),
                func.count(Link.id).filter(Link.is_active),
                func.coalesce(func.sum(Link.click_count), 0),
            ).where(Link.user_id == user.id)
        )
    ).one()
    series = (
        await session.execute(
            text(
                """
                SELECT (c.clicked_at AT TIME ZONE 'UTC')::date AS day, count(*) AS clicks,
                       count(DISTINCT c.visitor_hash) AS visitors
                FROM clicks c JOIN links l ON l.id = c.link_id
                WHERE l.user_id = :user_id AND c.clicked_at >= :since AND NOT c.is_bot
                GROUP BY 1
                """
            ),
            {"user_id": user.id, "since": since},
        )
    ).all()
    timeseries = _fill_days(first_day, days, series)
    top = await session.scalars(
        select(Link).where(Link.user_id == user.id).order_by(Link.click_count.desc(), Link.id.desc()).limit(5)
    )
    return Overview(
        total_links=counts[0],
        active_links=counts[1],
        total_clicks=counts[2],
        clicks_last_7d=sum(d.clicks for d in timeseries[-7:]),
        timeseries=timeseries,
        top_links=[to_out(link) for link in top],
    )
