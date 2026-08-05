#!/usr/bin/env python3
"""
MYDownloader PRO — Web UI entry point.

  python webui.py

Buka browser:
  http://127.0.0.1:8080
"""
import os
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

os.chdir(ROOT)
os.environ["MYD_NONINTERACTIVE"] = "1"

from config.settings import Settings

Settings.load_runtime_dir()
Settings.ensure_dirs()


def main():
    host = os.getenv("WEBUI_HOST", "0.0.0.0")
    port = int(os.getenv("WEBUI_PORT", "8080"))

    print("=" * 52)
    print("  MYDownloader PRO — Web UI")
    print("  crafted by afnirwd")
    print("=" * 52)
    print(f"  Download folder : {Settings.DOWNLOAD_DIR}")
    print(f"  Cookies         : {Settings.get_cookies_path() or 'none'}")
    print(f"  Local URL       : http://127.0.0.1:{port}")
    print(f"  LAN URL         : http://<phone-ip>:{port}")
    print("  Stop            : Ctrl+C")
    print("=" * 52)

    from web.app import app

    app.run(host=host, port=port, debug=False, threaded=True, use_reloader=False)


if __name__ == "__main__":
    main()
