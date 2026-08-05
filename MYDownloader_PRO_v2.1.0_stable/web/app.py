"""
MYDownloader Web UI — Flask API (optimized: background jobs + light UI).
"""
from __future__ import annotations

import os as _os
_os.environ.setdefault("MYD_NONINTERACTIVE", "1")

import shutil
import threading
import time
import traceback
import uuid
from pathlib import Path

from flask import Flask, jsonify, render_template, request

from config.settings import Settings
from utils.platform_detect import detect_platform
from utils.history import HistoryManager
from utils.logger import logger

_WEB_DIR = Path(__file__).resolve().parent

app = Flask(
    __name__,
    template_folder=str(_WEB_DIR / "templates"),
    static_folder=str(_WEB_DIR / "static"),
)

# ---- background job store (in-memory) ----
_jobs: dict[str, dict] = {}
_jobs_lock = threading.Lock()
_MAX_JOBS = 30


def _job_cleanup():
    with _jobs_lock:
        if len(_jobs) <= _MAX_JOBS:
            return
        # drop oldest finished
        finished = sorted(
            ((k, v) for k, v in _jobs.items() if v.get("status") in ("done", "error")),
            key=lambda kv: kv[1].get("updated", 0),
        )
        for k, _ in finished[: max(0, len(_jobs) - _MAX_JOBS)]:
            _jobs.pop(k, None)


def _format_size(n: int) -> str:
    if not n:
        return "0 B"
    x = float(n)
    for u in ("B", "KB", "MB", "GB", "TB"):
        if x < 1024:
            return f"{x:.1f} {u}"
        x /= 1024
    return f"{x:.1f} PB"


def _disk_info() -> dict:
    try:
        total, used, free = shutil.disk_usage(Settings.DOWNLOAD_DIR)
        return {
            "total": _format_size(total),
            "used": _format_size(used),
            "free": _format_size(free),
            "path": Settings.DOWNLOAD_DIR,
        }
    except Exception:
        return {"total": "?", "used": "?", "free": "?", "path": Settings.DOWNLOAD_DIR}


def _parse_urls(raw: str) -> list[str]:
    parts: list[str] = []
    for line in (raw or "").replace(",", "\n").splitlines():
        for token in line.split():
            t = token.strip()
            if t.startswith("http://") or t.startswith("https://"):
                parts.append(t)
    seen, out = set(), []
    for u in parts:
        if u not in seen:
            seen.add(u)
            out.append(u)
    return out


def _run_download_job(job_id: str, urls: list[str], quality: str | None = None, audio_only: bool = False):
    from core.downloader import CoreDownloader
    import os

    Settings.load_runtime_dir()
    Settings.ensure_dirs()
    # TikTok quality hint untuk TikTokHandler (hdplay/play/wmplay)
    if quality in ("hdplay", "play", "wmplay", "best"):
        os.environ["MYD_TIKTOK_QUALITY"] = quality if quality != "best" else "hdplay"
    else:
        os.environ.pop("MYD_TIKTOK_QUALITY", None)
    downloader = CoreDownloader()
    results = []

    with _jobs_lock:
        _jobs[job_id]["status"] = "running"
        _jobs[job_id]["total"] = len(urls)
        _jobs[job_id]["done"] = 0
        _jobs[job_id]["updated"] = time.time()

    def _set(job_id, **kw):
        with _jobs_lock:
            _jobs[job_id].update(kw)
            _jobs[job_id]["updated"] = time.time()

    total = len(urls)
    for i, url in enumerate(urls):
        platform = detect_platform(url) or "unknown"
        short = url if len(url) <= 64 else url[:61] + "..."
        base_pct = int(100 * i / max(1, total))
        item = {"url": url, "platform": platform, "ok": False, "message": ""}

        _set(
            job_id,
            current=url,
            current_platform=platform,
            stage="detect",
            progress=base_pct + 2,
            message=f"[{i+1}/{total}] Mengesan platform…",
            detail=f"{platform} · {short}",
        )
        time.sleep(0.05)

        _set(
            job_id,
            stage="download",
            progress=min(95, base_pct + 8),
            message=f"[{i+1}/{total}] Memuat turun {platform}…",
            detail=short,
        )
        try:
            ok = downloader._sync_ytdlp_download(
                url,
                skip_preview=True,
                non_interactive=True,
                quality=quality,
                audio_only=audio_only,
            )
            item["ok"] = bool(ok)
            item["message"] = "OK" if ok else "Failed (format/ffmpeg/network)"
        except Exception as e:
            item["ok"] = False
            item["message"] = str(e)[:300]
            logger.error(f"WebUI job error: {e}\n{traceback.format_exc()}")

        results.append(item)
        done_n = i + 1
        pct = int(100 * done_n / max(1, total))
        icon = "✅" if item["ok"] else "❌"
        _set(
            job_id,
            done=done_n,
            results=list(results),
            progress=pct,
            stage="item_done",
            message=f"[{done_n}/{total}] {icon} {platform}: {item['message']}",
            detail=short,
        )

    success = sum(1 for r in results if r["ok"])
    fail = len(results) - success
    summary = f"{success} OK · {fail} failed"
    with _jobs_lock:
        _jobs[job_id].update(
            {
                "status": "done" if success > 0 or fail == 0 else "done",
                "results": results,
                "summary": summary,
                "message": summary,
                "error": None if success > 0 else (results[-1]["message"] if results else "Failed"),
                "ok": success > 0,
                "progress": 100,
                "download_dir": Settings.DOWNLOAD_DIR,
                "disk": _disk_info(),
                "current": None,
                "updated": time.time(),
            }
        )
    _job_cleanup()


@app.get("/favicon.ico")
def favicon_ico():
    return app.send_static_file("favicon.ico")


@app.get("/favicon.png")
def favicon_png():
    return app.send_static_file("favicon.png")


@app.get("/favicon.svg")
def favicon_svg():
    return app.send_static_file("favicon.svg")



@app.get("/sw.js")
def service_worker():
    """SW di root supaya scope = / (wajib untuk PWA install)."""
    resp = app.send_static_file("sw.js")
    resp.headers["Service-Worker-Allowed"] = "/"
    resp.headers["Cache-Control"] = "no-cache"
    return resp


@app.get("/manifest.webmanifest")
def web_manifest():
    return app.send_static_file("manifest.webmanifest")

@app.get("/")
def index():
    Settings.load_runtime_dir()
    Settings.ensure_dirs()
    stats = HistoryManager.get_stats()
    return render_template(
        "index.html",
        download_dir=Settings.DOWNLOAD_DIR,
        cookies_ok=bool(Settings.get_cookies_path()),
        total_downloads=stats.get("total_downloads", 0),
        disk=_disk_info(),
        version="2.1.0 PRO",
    )


@app.get("/api/status")
def api_status():
    Settings.load_runtime_dir()
    stats = HistoryManager.get_stats()
    recent = []
    try:
        for item in HistoryManager.get_recent(12):
            recent.append({
                "title": (item.get("title") or "—")[:60],
                "platform": item.get("platform") or "?",
                "url": item.get("url") or "",
                "date": (item.get("date") or item.get("timestamp") or "")[:19],
                "size": item.get("size") or item.get("file_size") or 0,
            })
    except Exception:
        pass
    return jsonify(
        {
            "download_dir": Settings.DOWNLOAD_DIR,
            "cookies_ok": bool(Settings.get_cookies_path()),
            "total_downloads": stats.get("total_downloads", 0),
            "disk": _disk_info(),
            "recent": recent,
        }
    )


@app.post("/api/clear-history")
def api_clear_history():
    try:
        n = HistoryManager.clear_history()
        return jsonify({"ok": True, "deleted": n})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


@app.post("/api/set-directory")
def api_set_directory():
    data = request.get_json(silent=True) or {}
    new_dir = (data.get("path") or "").strip()
    if not new_dir:
        return jsonify({"ok": False, "error": "Path empty"}), 400
    try:
        resolved = Settings.set_download_dir(new_dir)
        return jsonify({"ok": True, "path": resolved, "disk": _disk_info()})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 400


@app.post("/api/download")
def api_download():
    """Start download in background thread — return job_id immediately.

    Terima:
      { "url": "https://..." }
      { "urls": ["https://...", ...] }
      { "url": "line1\nline2" }  (batch teks)
    """
    data = request.get_json(silent=True) or {}
    urls: list[str] = []

    # Array dari Web UI baru
    raw_list = data.get("urls")
    if isinstance(raw_list, list):
        for item in raw_list:
            if isinstance(item, str) and item.strip().startswith("http"):
                urls.append(item.strip())
            elif isinstance(item, dict):
                u = (item.get("url") or "").strip()
                if u.startswith("http"):
                    urls.append(u)

    # String tunggal / multi-line
    if not urls:
        blob = data.get("url") or data.get("text") or ""
        if isinstance(blob, list):
            blob = "\n".join(str(x) for x in blob)
        urls = _parse_urls(str(blob))

    # Dedup keep order
    seen, uniq = set(), []
    for u in urls:
        if u not in seen:
            seen.add(u)
            uniq.append(u)
    urls = uniq

    if not urls:
        return jsonify({"ok": False, "error": "No valid URL"}), 400

    quality = data.get("quality")  # "best" | "720p" | format string | "audio"
    audio_only = bool(data.get("audio_only"))
    if quality in ("audio", "bestaudio", "bestaudio/best"):
        audio_only = True
        quality = "bestaudio/best"
    elif quality in ("", "best", None) and not audio_only:
        quality = None  # auto best dalam downloader
    elif isinstance(quality, str) and quality.lower().endswith("p") and not audio_only:
        pass  # e.g. 720p / 1080p

    job_id = uuid.uuid4().hex[:12]
    with _jobs_lock:
        _jobs[job_id] = {
            "id": job_id,
            "status": "queued",
            "total": len(urls),
            "done": 0,
            "results": [],
            "summary": "",
            "ok": False,
            "current": None,
            "updated": time.time(),
        }

    th = threading.Thread(
        target=_run_download_job,
        args=(job_id, urls, quality, audio_only),
        daemon=True,
    )
    th.start()

    return jsonify({"ok": True, "job_id": job_id, "total": len(urls)})


@app.post("/api/formats")
def api_formats():
    """Senarai kualiti LIVE untuk URL (yt-dlp). TikTok → fixed options."""
    data = request.get_json(silent=True) or {}
    url = (data.get("url") or "").strip()
    if not url.startswith("http"):
        return jsonify({"ok": False, "error": "Invalid URL"}), 400

    platform = detect_platform(url)
    if platform == "tiktok":
        try:
            from core.social.tiktok import TikTokHandler
            info = TikTokHandler.get_info(url) or {}
            def _sz(n):
                try:
                    n = float(n or 0)
                except Exception:
                    return ""
                if n <= 0:
                    return ""
                for u in ("B", "KB", "MB", "GB"):
                    if n < 1024:
                        return f"{n:.1f} {u}"
                    n /= 1024
                return f"{n:.1f} TB"
            qualities = []
            w = info.get("width") or ""
            h = info.get("height") or ""
            ratio = info.get("ratio") or (f"{w}x{h}" if w and h else "")
            dur = info.get("duration")
            dur_s = f"{int(dur)}s" if dur else ""
            for key, size_key, label in (
                ("hdplay", "hd_size", "HD · tanpa watermark"),
                ("play", "size", "Standard · tanpa watermark"),
                ("wmplay", "wm_size", "Dengan watermark"),
            ):
                if not info.get(key):
                    continue
                note = " · ".join(x for x in (ratio, _sz(info.get(size_key)), dur_s) if x)
                qualities.append({
                    "id": key,  # hdplay / play / wmplay — dihormati job
                    "label": label + (f" ({note})" if note else ""),
                    "note": _sz(info.get(size_key)) or "tikwm",
                })
            if not qualities:
                qualities = [{"id": "best", "label": "Best (no watermark)", "note": "tikwm"}]
            if info.get("music_info", {}).get("play") or info.get("music"):
                qualities.append({"id": "audio", "label": "Audio only (MP3)", "note": "music", "audio_only": True})
            title = (info.get("title") or info.get("id") or "TikTok")[:80]
            return jsonify({"ok": True, "platform": "tiktok", "title": title, "qualities": qualities})
        except Exception as e:
            logger.warning(f"tiktok formats fallback: {e}")
            return jsonify({
                "ok": True,
                "platform": "tiktok",
                "title": "TikTok",
                "qualities": [
                    {"id": "best", "label": "Best (no watermark)", "note": "tikwm"},
                    {"id": "audio", "label": "Audio only", "note": "mp3", "audio_only": True},
                ],
            })

    try:
        import yt_dlp
        from core.downloader import CoreDownloader

        dl = CoreDownloader()
        opts = {"quiet": True, "no_warnings": True, "extract_flat": False}
        opts = dl._apply_cookies(opts, platform=platform)
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(url, download=False)
        if not info:
            return jsonify({"ok": False, "error": "No metadata"}), 400

        videos, audio = dl._get_dynamic_qualities(info.get("formats") or [])
        qualities = []
        qualities.append({"id": "best", "label": "Best available", "note": "auto"})
        for v in videos:
            h = int(v["height"])
            fps = v.get("fps") or 30
            size = v.get("size") or 0
            size_mb = f"{size/1024/1024:.1f} MB" if size else ""
            # id ringkas — downloader akan bina format string
            fmt_id = f"{h}p"
            label = f"{h}p" + (f" · {int(fps)}fps" if fps and fps > 30 else "")
            qualities.append({
                "id": fmt_id,
                "label": label,
                "note": size_mb,
                "height": h,
            })
        if audio and (audio.get("abr") or True):
            abr = audio.get("abr") or 128
            qualities.append({
                "id": "audio",
                "label": f"Audio only ({abr} kbps)",
                "note": "mp3",
                "audio_only": True,
            })
        return jsonify({
            "ok": True,
            "platform": platform,
            "title": (info.get("title") or "")[:80],
            "qualities": qualities,
        })
    except Exception as e:
        logger.error(f"formats error: {e}\n{traceback.format_exc()}")
        return jsonify({"ok": False, "error": str(e)[:300]}), 500


@app.get("/api/job/<job_id>")
def api_job(job_id: str):
    with _jobs_lock:
        job = _jobs.get(job_id)
        if not job:
            return jsonify({"ok": False, "error": "Job not found"}), 404
        return jsonify(job)


@app.post("/api/tiktok-slide")
def api_tiktok_slide():
    data = request.get_json(silent=True) or {}
    url = (data.get("url") or "").strip()
    mode = (data.get("mode") or "video").strip().lower()
    if not url:
        return jsonify({"ok": False, "error": "URL empty"}), 400
    Settings.load_runtime_dir()
    Settings.ensure_dirs()
    try:
        from core.social.tiktok import TikTokHandler

        info = TikTokHandler.get_info(url)
        if not info:
            return jsonify({"ok": False, "error": "Failed to fetch TikTok info"}), 400
        aweme = str(info.get("id") or info.get("aweme_id") or "tiktok_slide")
        output_name = f"slide_{aweme}"
        if mode == "images":
            ok = bool(TikTokHandler.download_images_only(info, output_name))
        elif mode == "audio":
            ok = bool(TikTokHandler.download_audio_only(info, output_name))
        else:
            ok = bool(TikTokHandler.download_slide_as_video(info, output_name))
        return jsonify({"ok": ok, "mode": mode, "message": "OK" if ok else "Failed"})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)[:300]}), 500
