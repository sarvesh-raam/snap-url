import re
import secrets

ALPHABET = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz"
ALIAS_RE = re.compile(r"^[A-Za-z0-9_-]{3,32}$")

# Paths the web app or API own; a custom alias can never take one of these.
RESERVED = frozenset(
    {
        "api",
        "app",
        "assets",
        "admin",
        "dashboard",
        "docs",
        "health",
        "links",
        "login",
        "logout",
        "metrics",
        "openapi.json",
        "redoc",
        "register",
        "settings",
        "static",
        "favicon.ico",
        "robots.txt",
    }
)


def generate_code(length: int) -> str:
    # Random (not sequential) codes so links can't be enumerated; 62^7 ≈ 3.5 trillion.
    return "".join(secrets.choice(ALPHABET) for _ in range(length))


def alias_error(alias: str) -> str | None:
    if not ALIAS_RE.match(alias):
        return "Alias must be 3-32 characters: letters, digits, '-' or '_'"
    if alias.lower() in RESERVED:
        return "That alias is reserved"
    return None
