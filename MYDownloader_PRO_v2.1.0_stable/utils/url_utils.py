"""
Utiliti untuk membersihkan dan menormalkan URL media sosial.
"""
import re
import base64
from urllib.parse import urlparse, parse_qs
from utils.logger import logger


def normalize_url(url: str) -> str:
    """
    Bersihkan dan tukar URL kepada format yang lebih disokong oleh yt-dlp.
    Khususnya menangani Instagram Share Link (/s/...) untuk Highlight/Story.
    """
    url = url.strip()

    # --- Instagram Share Link (/s/...) ---
    # Contoh: https://www.instagram.com/s/aGlnaGxpZ2h0OjE3OTk3MzU2ODA3ODcyOTYx?story_media_id=...
    if "instagram.com/s/" in url:
        try:
            # Ambil bahagian base64 selepas /s/
            match = re.search(r"instagram\.com/s/([A-Za-z0-9+/=]+)", url)
            if match:
                b64 = match.group(1)
                # Pad base64 jika perlu
                pad = 4 - len(b64) % 4
                if pad != 4:
                    b64 += "=" * pad

                decoded = base64.b64decode(b64).decode("utf-8", errors="ignore")
                # decoded biasanya: "highlight:17997356807872961" atau "media:xxxx"

                if decoded.startswith("highlight:"):
                    highlight_id = decoded.split(":", 1)[1]
                    new_url = f"https://www.instagram.com/stories/highlights/{highlight_id}/"
                    logger.info(f"🔄 Instagram Share Link dikesan → ditukar ke Highlight URL:")
                    logger.info(f"   {new_url}")
                    return new_url

                elif decoded.startswith("media:"):
                    # Media share — cuba extract story_media_id dari query
                    qs = parse_qs(urlparse(url).query)
                    media_id = qs.get("story_media_id", [None])[0]
                    if media_id:
                        # Format story_media_id biasanya: {media_pk}_{user_id}
                        media_pk = media_id.split("_")[0]
                        logger.info(f"🔄 Instagram media share dikesan (media_id={media_pk})")
                        # yt-dlp lebih suka URL story penuh, tapi kita biarkan dulu
                        return url

        except Exception as e:
            logger.warning(f"Gagal menormalkan Instagram share URL: {e}")

    # Instagram Story/Reel/Post — buang tracking params (utm, igsh, dll)
    if "instagram.com" in url:
        try:
            parsed = urlparse(url)
            # Kekalkan hanya parameter penting
            qs = parse_qs(parsed.query)
            keep = {}
            for k in ("story_media_id",):
                if k in qs:
                    keep[k] = qs[k]
            # bina semula tanpa junk
            path = parsed.path.rstrip("/") + "/"
            if keep:
                from urllib.parse import urlencode
                flat = {k: v[0] for k, v in keep.items()}
                url = f"{parsed.scheme}://{parsed.netloc}{path}?{urlencode(flat)}"
            else:
                url = f"{parsed.scheme}://{parsed.netloc}{path}"
            logger.info(f"🧹 URL IG dibersihkan: {url}")
        except Exception as e:
            logger.debug(f"IG URL clean skip: {e}")

    return url
