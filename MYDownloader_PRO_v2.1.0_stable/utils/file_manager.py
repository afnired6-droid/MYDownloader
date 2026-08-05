"""
Pengurus Fail: Susunan folder ikut platform + jenis kandungan.
"""
from __future__ import annotations

import os
import re
from datetime import datetime
from config.settings import Settings
from utils.logger import logger


# Nama folder platform yang kemas
PLATFORM_FOLDERS = {
    "youtube": "YouTube",
    "youtu": "YouTube",
    "instagram": "Instagram",
    "instagramstory": "Instagram",
    "tiktok": "TikTok",
    "facebook": "Facebook",
    "twitter": "Twitter",
    "x": "Twitter",
    "reddit": "Reddit",
    "threads": "Threads",
    "telegram": "Telegram",
}


def _safe(name: str, fallback: str = "Unknown") -> str:
    s = "".join(c for c in (name or "") if c.isalnum() or c in "._- ").strip()
    return s[:80] or fallback


class FileManager:
    @staticmethod
    def platform_folder(platform: str) -> str:
        key = (platform or "Other").lower().replace(" ", "")
        return PLATFORM_FOLDERS.get(key, _safe(platform, "Other"))

    @staticmethod
    def detect_content_type(url: str = "", platform: str = "", title: str = "") -> str:
        """Stories / Reels / Highlights / Posts / Videos."""
        u = (url or "").lower()
        p = (platform or "").lower()
        t = (title or "").lower()

        if "stories/highlights" in u or "/highlights/" in u:
            return "Highlights"
        if "/stories/" in u or "instagramstory" in p or "story by" in t:
            return "Stories"
        if "/reel/" in u or "/reels/" in u:
            return "Reels"
        if "/p/" in u:
            return "Posts"
        if "tiktok" in p:
            return "Videos"
        return "Videos"

    @staticmethod
    def get_dir(platform: str, content_type: str | None = None, author: str | None = None) -> str:
        """
        downloads/
          Instagram/Stories/
          Instagram/Reels/
          YouTube/Videos/
          TikTok/Videos/
          ...
        """
        root = Settings.DOWNLOAD_DIR
        plat = FileManager.platform_folder(platform)
        parts = [root, plat]
        if content_type:
            parts.append(content_type)
        if author:
            parts.append(_safe(author))
        path = os.path.join(*parts)
        os.makedirs(path, exist_ok=True)
        return path

    @staticmethod
    def get_smart_path(
        platform: str,
        author: str,
        title: str,
        ext: str,
        url: str = "",
        content_type: str | None = None,
    ) -> str:
        """
        Contoh:
          downloads/Instagram/Stories/user/IG_user_20260805_title.jpg
          downloads/YouTube/Videos/Author/YT_Author_20260805_title.mp4
        """
        now = datetime.now()
        if not content_type:
            content_type = FileManager.detect_content_type(url, platform, title)

        safe_author = _safe(author)
        safe_title = _safe(title, "Media")
        folder = FileManager.get_dir(platform, content_type, safe_author)

        plat_short = FileManager.platform_folder(platform)[:2].upper()
        try:
            file_name = Settings.FILE_NAME_TEMPLATE.format(
                platform=plat_short,
                author=safe_author,
                date=now.strftime("%Y%m%d"),
                title=safe_title,
            )
        except Exception:
            file_name = f"{plat_short}_{safe_author}_{now.strftime('%Y%m%d')}_{safe_title}"

        file_name = re.sub(r"\s+", "_", file_name).strip("._")
        if len(file_name) > 180:
            file_name = file_name[:180]

        return os.path.join(folder, f"{file_name}.{ext}")

    @staticmethod
    def clean_temp_files():
        try:
            for filename in os.listdir(Settings.TEMP_DIR):
                file_path = os.path.join(Settings.TEMP_DIR, filename)
                if os.path.isfile(file_path):
                    os.remove(file_path)
            logger.debug("Fail sementara (temp files) telah dibersihkan.")
        except Exception as e:
            logger.error(f"Gagal membersihkan fail temp: {e}")
