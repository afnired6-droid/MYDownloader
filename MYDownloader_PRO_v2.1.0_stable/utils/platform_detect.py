"""
Pengesanan platform dari URL + penapis cookies mengikut domain platform.
"""
import tempfile
from pathlib import Path
from urllib.parse import urlparse
from utils.logger import logger

# Domain yang dibenarkan untuk setiap platform (cookies)
PLATFORM_COOKIE_DOMAINS = {
    "youtube": ["youtube.com", "google.com", "googlevideo.com", "youtu.be"],
    "instagram": ["instagram.com", "cdninstagram.com", "facebook.com"],
    "facebook": ["facebook.com", "fb.com", "fbcdn.net", "instagram.com"],
    "threads": ["threads.net", "threads.com", "instagram.com", "cdninstagram.com"],
    "twitter": ["twitter.com", "x.com", "twimg.com"],
    "reddit": ["reddit.com", "redd.it"],
    "tiktok": ["tiktok.com", "tiktokv.com"],
}


def _host_matches(host: str, domain: str) -> bool:
    """Match domain dengan betul (elak 't.co' match dalam 'reddit.com')."""
    host = (host or "").lower().lstrip(".")
    domain = domain.lower().lstrip(".")
    return host == domain or host.endswith("." + domain)


def detect_platform(url: str) -> str:
    """Return nama platform ringkas dari URL."""
    u = (url or "").lower().strip()
    host = urlparse(u).netloc.lower().replace("www.", "")

    # Order penting — domain spesifik dulu
    if _host_matches(host, "tiktok.com") or host.startswith("vm.tiktok.") or host.startswith("vt.tiktok."):
        return "tiktok"
    if _host_matches(host, "youtube.com") or _host_matches(host, "youtu.be") or _host_matches(host, "youtube-nocookie.com"):
        return "youtube"
    if _host_matches(host, "instagram.com"):
        return "instagram"
    if _host_matches(host, "threads.net") or _host_matches(host, "threads.com"):
        return "threads"
    if (
        _host_matches(host, "facebook.com")
        or _host_matches(host, "fb.com")
        or _host_matches(host, "fb.watch")
        or _host_matches(host, "fb.me")
    ):
        return "facebook"
    if _host_matches(host, "reddit.com") or _host_matches(host, "redd.it"):
        return "reddit"
    if _host_matches(host, "twitter.com") or _host_matches(host, "x.com") or _host_matches(host, "t.co"):
        return "twitter"
    return "other"


def filter_cookies_for_platform(cookies_path: str, platform: str) -> str | None:
    """
    Baca Netscape cookies.txt, tapis domain yang sesuai platform,
    tulis ke fail sementara. Return path fail sementara atau None.

    Penting: baris #HttpOnly_... ialah cookie SAH (bukan komen).
    """
    if not cookies_path or not Path(cookies_path).is_file():
        return None

    # TikTok melalui tikwm → jangan guna cookies sama sekali
    if platform == "tiktok":
        return None

    allowed = PLATFORM_COOKIE_DOMAINS.get(platform)
    if not allowed:
        return None

    try:
        lines_out = [
            "# Netscape HTTP Cookie File",
            "# Filtered for platform: " + platform,
        ]
        kept = 0
        names = []
        with open(cookies_path, "r", encoding="utf-8", errors="ignore") as f:
            for line in f:
                raw = line.strip()
                if not raw:
                    continue
                # Komen biasa skip; #HttpOnly_ kekal
                if raw.startswith("#") and not raw.startswith("#HttpOnly_"):
                    continue
                parts = raw.split("	")
                if len(parts) < 7:
                    continue
                domain = parts[0].replace("#HttpOnly_", "").lstrip(".").lower()
                if any(_host_matches(domain, d) or domain.endswith("." + d) or domain.endswith(d) for d in allowed):
                    lines_out.append(raw)
                    kept += 1
                    names.append(parts[5])

        if kept == 0:
            logger.debug(f"Tiada cookies sesuai untuk platform '{platform}'")
            return None

        tmp = tempfile.NamedTemporaryFile(
            mode="w",
            suffix=f"_{platform}_cookies.txt",
            delete=False,
            encoding="utf-8",
        )
        tmp.write("\n".join(lines_out) + "\n")
        tmp.close()
        logger.info(f"🍪 Cookies {platform}: {kept} entry digunakan ({', '.join(names[:8])}{'…' if len(names)>8 else ''})")
        return tmp.name
    except Exception as e:
        logger.warning(f"Gagal menapis cookies untuk {platform}: {e}")
        return None
