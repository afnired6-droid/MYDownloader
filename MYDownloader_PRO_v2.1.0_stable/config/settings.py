"""
Pengurusan Konfigurasi Projek (Environment Variables).
"""
import os
from pathlib import Path
from dotenv import load_dotenv

# Muatkan environment variables dari fail .env
load_dotenv()


class Settings:
    # Telegram API Credentials
    _api_id_raw = os.getenv("API_ID", "").strip()
    _api_hash_raw = os.getenv("API_HASH", "").strip()

    if not _api_id_raw or not _api_id_raw.isdigit():
        API_ID = 0
    else:
        API_ID = int(_api_id_raw)

    API_HASH = _api_hash_raw

    DOWNLOAD_DIR = os.getenv("DOWNLOAD_DIR", "./downloads")
    TEMP_DIR = os.getenv("TEMP_DIR", "./temp")

    MAX_CONCURRENT = int(os.getenv("MAX_CONCURRENT_DOWNLOADS", "3"))
    DEFAULT_QUALITY = os.getenv("DEFAULT_QUALITY", "best")
    FILE_NAME_TEMPLATE = os.getenv("FILE_NAME_TEMPLATE", "{platform}_{author}_{date}_{title}")

    # Cookies support (untuk Instagram Story/Highlight, private content, dll)
    # Letak fail cookies.txt di root folder project atau set path di .env
    COOKIES_FILE = os.getenv("COOKIES_FILE", "cookies.txt")

    @staticmethod
    def get_cookies_path() -> str | None:
        """Return path ke cookies file jika wujud, else None."""
        path = Path(Settings.COOKIES_FILE)
        if path.is_file() and path.stat().st_size > 0:
            return str(path.resolve())
        return None

    @staticmethod
    def validate_telegram_credentials() -> bool:
        """Semak sama ada API_ID dan API_HASH telah diset dengan betul."""
        if Settings.API_ID == 0 or not Settings.API_HASH:
            return False
        return True

    @staticmethod
    def ensure_dirs():
        """Memastikan direktori muat turun dan temp wujud."""
        os.makedirs(Settings.DOWNLOAD_DIR, exist_ok=True)
        os.makedirs(Settings.TEMP_DIR, exist_ok=True)



    @staticmethod
    def set_download_dir(new_dir: str) -> str:
        """Tukar folder download semasa runtime & pastikan wujud."""
        new_dir = (new_dir or "").strip() or "./downloads"
        path = Path(new_dir).expanduser()
        path.mkdir(parents=True, exist_ok=True)
        Settings.DOWNLOAD_DIR = str(path.resolve())
        # Simpan ke config runtime (supaya Web UI / sesi seterusnya boleh baca)
        runtime = Path("config/runtime_dir.txt")
        runtime.parent.mkdir(parents=True, exist_ok=True)
        runtime.write_text(Settings.DOWNLOAD_DIR, encoding="utf-8")
        return Settings.DOWNLOAD_DIR

    @staticmethod
    def load_runtime_dir():
        """Muat folder download dari runtime config jika ada."""
        runtime = Path("config/runtime_dir.txt")
        if runtime.is_file():
            saved = runtime.read_text(encoding="utf-8").strip()
            if saved:
                Path(saved).mkdir(parents=True, exist_ok=True)
                Settings.DOWNLOAD_DIR = saved

Settings.load_runtime_dir()
Settings.ensure_dirs()
