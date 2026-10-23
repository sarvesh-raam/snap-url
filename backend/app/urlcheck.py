from urllib.parse import urlsplit

from app.config import get_settings

MAX_URL_LENGTH = 2048


def normalize_target(url: str) -> str:
    """Validates a destination URL and returns it trimmed. Raises ValueError."""
    url = url.strip()
    if len(url) > MAX_URL_LENGTH:
        raise ValueError(f"URL is longer than {MAX_URL_LENGTH} characters")
    if "://" not in url:
        url = "https://" + url
    parts = urlsplit(url)
    if parts.scheme.lower() not in ("http", "https"):
        raise ValueError("Only http and https URLs can be shortened")
    host = (parts.hostname or "").lower()
    if not host or (" " in host) or ("." not in host and host != "localhost"):
        raise ValueError("URL must have a valid host")
    if parts.netloc.lower() == urlsplit(get_settings().base_url).netloc.lower():
        # Shortening our own short links creates redirect chains and loops.
        raise ValueError("Links to this shortener can't be shortened again")
    return url
