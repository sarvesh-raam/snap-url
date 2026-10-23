import pytest

from app.shortcode import ALPHABET, alias_error, generate_code
from app.tracking import classify_device, lookup_country, referrer_domain, visitor_hash
from app.urlcheck import normalize_target

CHROME_WIN = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36"
)
SAFARI_IPHONE = (
    "Mozilla/5.0 (iPhone; CPU iPhone OS 18_0 like Mac OS X) AppleWebKit/605.1.15 "
    "(KHTML, like Gecko) Version/18.0 Mobile/15E148 Safari/604.1"
)
IPAD = (
    "Mozilla/5.0 (iPad; CPU OS 17_0 like Mac OS X) AppleWebKit/605.1.15 "
    "(KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1"
)
GOOGLEBOT = "Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)"


def test_generated_codes_use_base62_and_length():
    codes = {generate_code(7) for _ in range(2000)}
    assert len(codes) == 2000
    assert all(len(c) == 7 and set(c) <= set(ALPHABET) for c in codes)


@pytest.mark.parametrize(
    ("alias", "ok"),
    [
        ("my-link", True),
        ("abc", True),
        ("ab", False),
        ("has space", False),
        ("x" * 33, False),
        ("dashboard", False),
        ("API", False),
        ("ünï", False),
    ],
)
def test_alias_rules(alias, ok):
    assert (alias_error(alias) is None) is ok


def test_normalize_target_adds_scheme_and_rejects_bad_urls():
    assert normalize_target("  example.com/path ") == "https://example.com/path"
    assert normalize_target("http://localhost:3000/x") == "http://localhost:3000/x"
    for bad in [
        "javascript:alert(1)",
        "ftp://example.com",
        "https://",
        "https://nodot",
        "http://sn.test/abc",
        "https://e.com/" + "a" * 2050,
    ]:
        with pytest.raises(ValueError):
            normalize_target(bad)


@pytest.mark.parametrize(
    ("ua", "device", "browser", "os_name"),
    [
        (CHROME_WIN, "desktop", "Chrome", "Windows"),
        (SAFARI_IPHONE, "mobile", "Mobile Safari", "iOS"),
        (IPAD, "tablet", "Mobile Safari", "iOS"),
        (GOOGLEBOT, "bot", "Googlebot", "Other"),
    ],
)
def test_classify_device(ua, device, browser, os_name):
    d, b, o, is_bot = classify_device(ua)
    assert (d, b, o, is_bot) == (device, browser, os_name, device == "bot")


def test_empty_user_agent_is_a_bot():
    assert classify_device("")[0] == "bot"


def test_referrer_domain():
    assert referrer_domain("https://www.twitter.com/x/status/1") == "twitter.com"
    assert referrer_domain("") is None
    assert referrer_domain("http://sn.test/abc") is None  # our own pages are not a referrer


def test_country_from_header_ignores_placeholders():
    assert lookup_country("1.2.3.4", "in") == "IN"
    assert lookup_country("1.2.3.4", "XX") is None
    assert lookup_country("1.2.3.4", "") is None


def test_visitor_hash_is_stable_per_day_and_rotates_daily():
    a = visitor_hash("1.2.3.4", "ua", "2026-10-23")
    assert a == visitor_hash("1.2.3.4", "ua", "2026-10-23")
    assert a != visitor_hash("1.2.3.4", "ua", "2026-10-24")
    assert "1.2.3.4" not in a
