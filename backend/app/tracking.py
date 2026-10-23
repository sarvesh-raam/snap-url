"""Turns a raw redirect request into a click event, and click events into rows."""

import hashlib
import ipaddress
import logging
from datetime import UTC, datetime
from functools import lru_cache
from urllib.parse import urlsplit

from fastapi import Request
from user_agents import parse as parse_ua

from app.config import get_settings

log = logging.getLogger(__name__)

COUNTRY_HEADERS = ("cf-ipcountry", "x-vercel-ip-country", "cloudfront-viewer-country", "x-country-code")


def client_ip(request: Request) -> str:
    if get_settings().trust_proxy_headers:
        forwarded = request.headers.get("x-forwarded-for")
        if forwarded:
            return forwarded.split(",")[0].strip()
        real = request.headers.get("x-real-ip")
        if real:
            return real.strip()
    return request.client.host if request.client else "0.0.0.0"


def capture(request: Request, link_id: int) -> dict[str, str]:
    """The cheap part, done on the redirect hot path: copy what we need off the request."""
    headers = request.headers
    country = ""
    if get_settings().trust_proxy_headers:
        country = next((headers[h] for h in COUNTRY_HEADERS if headers.get(h)), "")
    return {
        "link_id": str(link_id),
        "ts": datetime.now(UTC).isoformat(),
        "ip": client_ip(request),
        "ua": headers.get("user-agent", "")[:512],
        "ref": headers.get("referer", "")[:1024],
        "country": country,
    }


@lru_cache(maxsize=1)
def _geoip_reader():
    path = get_settings().geoip_db_path
    if not path:
        return None
    try:
        import geoip2.database

        return geoip2.database.Reader(path)
    except Exception:  # missing file or package: country falls back to headers only
        log.warning("GeoIP database at %s could not be opened; countries will be unknown", path)
        return None


def lookup_country(ip: str, header_country: str) -> str | None:
    code = header_country.strip().upper()
    if len(code) == 2 and code.isalpha() and code not in ("XX", "T1"):
        return code
    reader = _geoip_reader()
    if reader is None:
        return None
    try:
        if ipaddress.ip_address(ip).is_private:
            return None
        return reader.country(ip).country.iso_code
    except Exception:
        return None


def referrer_domain(ref: str) -> str | None:
    if not ref:
        return None
    host = (urlsplit(ref).hostname or "").lower()
    if host.startswith("www."):
        host = host[4:]
    if not host or host == (urlsplit(get_settings().base_url).hostname or "").lower():
        return None
    return host[:255]


def classify_device(ua_string: str) -> tuple[str, str, str, bool]:
    ua = parse_ua(ua_string)
    if ua.is_bot or not ua_string:
        device = "bot"
    elif ua.is_tablet:
        device = "tablet"
    elif ua.is_mobile:
        device = "mobile"
    elif ua.is_pc:
        device = "desktop"
    else:
        device = "other"
    browser = ua.browser.family or "Other"
    os_name = ua.os.family or "Other"
    return device, browser[:64], os_name[:64], device == "bot"


def visitor_hash(ip: str, ua: str, day: str) -> str:
    # Unique-visitor key without storing IPs: the daily salt means hashes can't be
    # joined across days or reversed with a lookup table that ignores the secret.
    salt = f"{get_settings().jwt_secret}:{day}"
    return hashlib.sha256(f"{salt}|{ip}|{ua}".encode()).hexdigest()[:32]


def enrich(event_id: str, fields: dict[str, str]) -> dict:
    """The expensive part, done by the worker: parse UA, geolocate, hash."""
    ts = datetime.fromisoformat(fields["ts"])
    device, browser, os_name, is_bot = classify_device(fields.get("ua", ""))
    ip = fields.get("ip", "")
    return {
        "event_id": event_id,
        "link_id": int(fields["link_id"]),
        "clicked_at": ts,
        "country": lookup_country(ip, fields.get("country", "")),
        "device": device,
        "browser": browser,
        "os": os_name,
        "referrer": referrer_domain(fields.get("ref", "")),
        "visitor_hash": visitor_hash(ip, fields.get("ua", ""), ts.date().isoformat()),
        "is_bot": is_bot,
    }
