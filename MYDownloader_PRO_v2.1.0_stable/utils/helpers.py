"""
Fungsi pembantu (helpers) seperti notifikasi Termux dan pengesanan clipboard.
"""
import os
import subprocess
import pyperclip
import shutil
from typing import Optional

def check_disk_space(path: str, required_bytes: int) -> bool:
    """Periksa jika ruang storan mencukupi."""
    total, used, free = shutil.disk_usage(path)
    return free > required_bytes

def get_clipboard_url() -> Optional[str]:
    """Dapatkan URL dari clipboard (jika wujud)."""
    try:
        content = pyperclip.paste()
        if content.startswith("http://") or content.startswith("https://"):
            return content
    except Exception:
        pass
    return None

def termux_notify(title: str, content: str):
    """Hantar notifikasi jika dijalankan di dalam environment Termux."""
    if "PREFIX" in os.environ and "termux" in os.environ["PREFIX"]:
        try:
            subprocess.run(["termux-notification", "-t", title, "-c", content], check=False)
        except FileNotFoundError:
            pass
