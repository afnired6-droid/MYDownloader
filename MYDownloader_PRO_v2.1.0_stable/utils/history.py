"""
Rakaman sejarah muat turun dan statistik.
"""
import json
import os
from datetime import datetime
from utils.logger import logger

HISTORY_FILE = "config/history.json"


class HistoryManager:
    @staticmethod
    def _load_history() -> dict:
        if not os.path.exists(HISTORY_FILE):
            return {"downloads": [], "stats": {"total_size_bytes": 0, "platforms": {}}}
        try:
            with open(HISTORY_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            return {"downloads": [], "stats": {"total_size_bytes": 0, "platforms": {}}}

    @staticmethod
    def _save_history(data: dict):
        os.makedirs(os.path.dirname(HISTORY_FILE), exist_ok=True)
        with open(HISTORY_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4, ensure_ascii=False)

    @classmethod
    def add_record(cls, url: str, platform: str, title: str, file_size: int = 0):
        """Tambah rekod muat turun baharu dan kemas kini statistik."""
        data = cls._load_history()

        record = {
            "url": url,
            "platform": platform,
            "title": title,
            "size": file_size,
            "date": datetime.now().isoformat()
        }
        data["downloads"].append(record)

        data["stats"]["total_size_bytes"] += file_size
        platforms = data["stats"]["platforms"]
        platforms[platform] = platforms.get(platform, 0) + 1

        cls._save_history(data)
        logger.debug(f"Rekod disimpan ke sejarah: {title}")

    @classmethod
    def is_downloaded(cls, url: str) -> bool:
        """Semak jika URL telah dimuat turun sebelumnya."""
        data = cls._load_history()
        return any(item.get("url") == url for item in data["downloads"])

    @classmethod
    def get_stats(cls) -> dict:
        """Ambil statistik keseluruhan."""
        data = cls._load_history()
        downloads = data.get("downloads", [])
        stats = data.get("stats", {"total_size_bytes": 0, "platforms": {}})
        return {
            "total_downloads": len(downloads),
            "total_size_bytes": stats.get("total_size_bytes", 0),
            "platforms": stats.get("platforms", {}),
            "recent": downloads[-10:][::-1] if downloads else [],
        }

    @classmethod
    def clear_history(cls) -> int:
        """Padam semua sejarah. Return bilangan rekod yang dipadam."""
        data = cls._load_history()
        count = len(data.get("downloads", []))
        cls._save_history({"downloads": [], "stats": {"total_size_bytes": 0, "platforms": {}}})
        return count

    @classmethod
    def get_recent(cls, limit: int = 15) -> list:
        """Ambil rekod terbaru."""
        data = cls._load_history()
        downloads = data.get("downloads", [])
        return downloads[-limit:][::-1]
