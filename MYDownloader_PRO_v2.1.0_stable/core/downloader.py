"""
Orchestrator utama yang menghubungkan yt-dlp, UI Preview, Live Format Extraction, Progress Bar, dan History.
Dilengkapi dengan Soalan Overwrite (Tindih) Interaktif dan Speed Boost.
"""
import yt_dlp
import asyncio
import shutil
import subprocess
import importlib
import sys
import os
from pathlib import Path
import threading
from concurrent.futures import ThreadPoolExecutor
from rich.console import Console
from rich.prompt import Prompt, Confirm
from rich.table import Table

from config.settings import Settings
from utils.logger import logger
from utils.helpers import check_disk_space
from ui.preview import show_preview, format_size
from ui.progress import ProgressManager
from utils.history import HistoryManager
from utils.file_manager import FileManager
from utils.url_utils import normalize_url
from utils.platform_detect import detect_platform, filter_cookies_for_platform
from core.social.tiktok import TikTokHandler

console = Console()

class CoreDownloader:
    def __init__(self):
        self.executor = ThreadPoolExecutor(max_workers=Settings.MAX_CONCURRENT)
        self.has_aria2c = shutil.which("aria2c") is not None
        self.cookies_path = Settings.get_cookies_path()
        self._cancel_event = threading.Event()
        if self.cookies_path:
            logger.info(f"🍪 Cookies dijumpai: {self.cookies_path}")

    def request_cancel(self):
        """Isyarat untuk hentikan muat turun semasa."""
        self._cancel_event.set()

    def clear_cancel(self):
        self._cancel_event.clear()

    def _apply_cookies(self, opts: dict, platform: str | None = None) -> dict:
        """Tambah cookies YANG SESUAI PLATFORM sahaja (IG ≠ TikTok ≠ X)."""
        if not self.cookies_path:
            return opts
        if not platform or platform in ("tiktok", "other"):
            # TikTok & unknown: jangan attach cookies IG/lain
            return opts
        filtered = filter_cookies_for_platform(self.cookies_path, platform)
        if filtered:
            opts["cookiefile"] = filtered
            opts["_filtered_cookies_path"] = filtered  # untuk cleanup nanti
            logger.info(f"🍪 cookiefile aktif: {filtered}")
        elif platform == "youtube":
            # Fallback: guna full cookies.txt jika filter kosong
            opts["cookiefile"] = str(Path(self.cookies_path).resolve())
            logger.info(f"🍪 YouTube guna full cookies: {opts['cookiefile']}")
        return opts

    def _youtube_opts(self, opts: dict, clients: list | None = None) -> dict:
        """YouTube clients — android dulu, web sebagai fallback bila perlu."""
        opts = dict(opts)
        opts["extractor_args"] = {
            "youtube": {
                "player_client": clients or ["android_sdkless", "android", "ios"],
            }
        }
        opts["nocheckcertificate"] = True
        return opts


    def _try_gallery_dl(self, url: str, platform: str) -> bool:
        """Fallback gallery-dl untuk Instagram/Reddit gambar bila yt-dlp gagal."""
        if platform not in ("instagram", "reddit", "twitter"):
            return False
        if not shutil.which("gallery-dl"):
            logger.info("gallery-dl tidak dipasang — langkau fallback gambar.")
            return False
        try:
            logger.info("🖼️  Mencuba gallery-dl sebagai fallback...")
            # Folder kemas: Instagram/Stories, Instagram/Posts, dll.
            from utils.file_manager import FileManager
            ctype = FileManager.detect_content_type(url, platform)
            out_dir = FileManager.get_dir(platform, ctype)
            os.makedirs(out_dir, exist_ok=True)
            logger.info(f"📁 Simpan ke: {out_dir}")
            # Bersihkan URL IG sebelum hantar
            clean_url = normalize_url(url) if platform == "instagram" else url
            cmd = [
                "gallery-dl",
                "-d", out_dir,
                "--no-mtime",
                "--quiet",
            ]
            # Cookies platform-aware
            filtered = None
            if self.cookies_path and platform != "tiktok":
                filtered = filter_cookies_for_platform(self.cookies_path, platform)
                if filtered:
                    cmd.extend(["--cookies", filtered])
            if platform == "instagram":
                # API rest kadang lebih stabil untuk story
                cmd.extend([
                    "-o", "extractor.instagram.api=rest",
                    "-o", "extractor.instagram.include=stories,highlights,posts,reels",
                ])
            cmd.append(clean_url)
            logger.info(f"gallery-dl cmd url: {clean_url}")
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=180)
            if filtered and os.path.exists(filtered):
                try:
                    os.remove(filtered)
                except Exception:
                    pass
            if result.returncode == 0:
                logger.info("✅ gallery-dl berjaya.")
                return True
            logger.warning(f"gallery-dl gagal: {(result.stderr or result.stdout or '')[:200]}")
            return False
        except Exception as e:
            logger.warning(f"gallery-dl error: {e}")
            return False



    def _make_progress_hook(self, progress_manager):
        def hook(d):
            if self._cancel_event.is_set():
                raise KeyboardInterrupt("Download dibatalkan oleh pengguna")
            progress_manager.ytdlp_hook(d)
        return hook

    def _ask_resume_or_cancel(self, non_interactive: bool = False) -> str:
        """
        Tanya user selepas Ctrl+C.
        Return: 'resume' | 'cancel'
        """
        if non_interactive:
            return "cancel"
        console.print("\n[bold yellow]⏸️  Muat turun dihentikan (Ctrl+C)[/bold yellow]")
        console.print("  [cyan]1.[/cyan] Resume — sambung semula dari fail separuh")
        console.print("  [cyan]2.[/cyan] Cancel — batalkan muat turun ini")
        choice = Prompt.ask(
            "[bold green]Pilih[/bold green]",
            choices=["1", "2"],
            default="1",
        )
        return "resume" if choice == "1" else "cancel"

    def _is_extractor_error(self, err_msg: str) -> bool:
        """Ralat yang mungkin diselesaikan dengan update yt-dlp."""
        keywords = [
            "unable to extract",
            "rehydration",
            "unsupported url",
            "no video formats",
            "extractorerror",
            "failed to parse json",
            "unable to download webpage",
            "http error 4",
            "confirm you are on the latest version",
        ]
        low = err_msg.lower()
        return any(k in low for k in keywords)

    def _silent_update_ytdlp(self) -> bool:
        """Cuba update yt-dlp secara senyap. Return True jika berjaya."""
        try:
            logger.info("🔄 Mengemaskini yt-dlp secara automatik...")
            result = subprocess.run(
                [sys.executable, "-m", "pip", "install", "-U", "yt-dlp", "-q"],
                capture_output=True,
                text=True,
                timeout=120,
            )
            if result.returncode == 0:
                importlib.reload(yt_dlp)
                logger.info("✅ yt-dlp berjaya dikemaskini. Mencuba semula...")
                return True
            logger.warning("Update yt-dlp tidak berjaya (pip return non-zero).")
            return False
        except Exception as e:
            logger.warning(f"Gagal auto-update yt-dlp: {e}")
            return False

    def _show_download_error_tips(self, err_msg: str, url: str):
        """Paparkan tips mesra pengguna selepas gagal (termasuk selepas retry)."""
        low = err_msg.lower()
        if "unreachable" in low or ("cookies" in low and "instagram" in url.lower()):
            console.print("\n[bold yellow]💡 Instagram Story / private content:[/bold yellow]")
            console.print("   • Export cookies IG yang masih login (sessionid + ds_user_id)")
            console.print("   • Story mungkin expired (24 jam) atau Close Friends")
            console.print("   • Cuba: pip install -U gallery-dl yt-dlp")
            console.print("   • Pastikan akaun dalam cookies boleh VIEW story tersebut")
        if "unsupported url" in low and "instagram.com" in url.lower():
            console.print("\n[bold yellow]💡 Tips Instagram Story/Highlight:[/bold yellow]")
            console.print("   • Format share link (/s/...) sudah cuba ditukar automatik.")
            console.print("   • Cuba buka link dalam browser → copy URL sebenar")
            console.print("     (biasanya /stories/highlights/xxxxx atau /stories/username/xxxxx)")
            console.print("   • Pastikan fail [bold]cookies.txt[/bold] masih valid.")
        elif "no video formats" in low:
            console.print("\n[bold yellow]💡 Tiada format video dijumpai.[/bold yellow]")
            console.print("   • Post ni mungkin [bold]gambar sahaja[/bold] (bukan video/reel).")
            console.print("   • Pastikan cookies.txt masih valid (export semula jika perlu).")
        elif "rehydration" in low or ("tiktok" in low and "unable to extract" in low):
            console.print("\n[bold yellow]💡 TikTok extractor gagal.[/bold yellow]")
            console.print("   • yt-dlp sudah dicuba update automatik, tetapi masih gagal.")
            console.print("   • Cuba guna URL penuh (www.tiktok.com/@user/video/...) bukan vt.tiktok.com")
            console.print("   • Atau update manual: [bold]pip install -U yt-dlp[/bold]")
        elif "login required" in low or "private" in low or "rate-limit" in low:
            console.print("\n[bold yellow]💡 Kandungan ini memerlukan cookies / login.[/bold yellow]")
            if not self.cookies_path:
                console.print("   • Export cookies dari browser → letak sebagai [bold]cookies.txt[/bold]")
            else:
                console.print("   • Cookies dijumpai tapi mungkin expired. Export semula.")
        else:
            console.print("\n[bold yellow]💡 Muat turun gagal selepas dicuba semula.[/bold yellow]")
            console.print(f"   • Detail: {err_msg[:200]}")


    def _get_dynamic_qualities(self, formats: list) -> tuple[list[dict], dict]:
        """Ekstrak format video dan audio secara live daripada metadata yt-dlp."""
        video_dict = {}
        best_audio = {'abr': 0, 'size': 0}

        for fmt in formats or []:
            vcodec = fmt.get('vcodec', 'none')
            acodec = fmt.get('acodec', 'none')
            height = fmt.get('height')
            fps = fmt.get('fps')
            tbr = fmt.get('tbr') or 0
            abr = fmt.get('abr') or 0
            filesize = fmt.get('filesize') or fmt.get('filesize_approx') or 0

            if vcodec != 'none' and height:
                key = height
                fps_val = int(fps) if fps else 30
                tbr_val = int(tbr)
                
                if key not in video_dict:
                    video_dict[key] = {
                        'height': height,
                        'fps': fps_val,
                        'tbr': tbr_val,
                        'size': filesize
                    }
                else:
                    if fps_val > video_dict[key]['fps'] or (fps_val == video_dict[key]['fps'] and tbr_val > video_dict[key]['tbr']):
                        video_dict[key]['fps'] = fps_val
                        video_dict[key]['tbr'] = tbr_val
                    if filesize > video_dict[key]['size']:
                        video_dict[key]['size'] = filesize

            if vcodec == 'none' and acodec != 'none':
                if int(abr) > best_audio['abr']:
                    best_audio['abr'] = int(abr)
                if filesize > best_audio['size']:
                    best_audio['size'] = filesize

        sorted_videos = sorted(video_dict.values(), key=lambda x: x['height'], reverse=True)
        return sorted_videos, best_audio

    def _prompt_quality_choice(self, formats: list) -> tuple[str, bool]:
        """Papar jadual pilihan kualiti LIVE mengikut kandungan sebenar video."""
        videos, audio = self._get_dynamic_qualities(formats)

        if not videos:
            console.print("\n[yellow]Format terperinci tidak ditemui, menggunakan tetapan auto-best.[/yellow]")
            return "best", False

        table = Table(title="[bold cyan]📊 Kualiti Tersedia Secara Live (Masa Nyata)[/bold cyan]", border_style="cyan")
        table.add_column("No", style="bold yellow", justify="center")
        table.add_column("Resolusi / Format", style="bold green")
        table.add_column("Detail (FPS / Bitrate)", style="white")
        table.add_column("Anggaran Saiz", style="magenta")

        options_map = {}
        choices = []
        idx = 1

        table.add_row(str(idx), "Auto Best (Kualiti Asal Terbaik)", "Auto Selection", "Max Quality")
        options_map[str(idx)] = ("best", False)
        choices.append(str(idx))
        idx += 1

        for vid in videos:
            h = vid['height']
            fps = vid['fps']
            size_str = format_size(vid['size']) if vid['size'] else "N/A"
            bitrate_str = f"{vid['tbr']} kbps" if vid['tbr'] else "Variable"
            
            table.add_row(
                str(idx),
                f"Video {h}p",
                f"{fps} fps ({bitrate_str})",
                size_str
            )
            options_map[str(idx)] = (f"{h}p", False)
            choices.append(str(idx))
            idx += 1

        audio_bitrate = f"{audio['abr']} kbps" if audio['abr'] else "Best Quality (~128-320 kbps)"
        audio_size = format_size(audio['size']) if audio['size'] else "N/A"
        table.add_row(
            str(idx),
            "Audio Sahaja (Convert MP3)",
            audio_bitrate,
            audio_size
        )
        options_map[str(idx)] = ("best", True)
        choices.append(str(idx))

        console.print("\n", table)
        selected = Prompt.ask("\n[bold green]Sila pilih kualiti pilihan anda[/bold green]", choices=choices, default="1")
        
        return options_map[selected]

    def _sync_ytdlp_download(self, url: str, skip_preview: bool = False, _retried: bool = False, non_interactive: bool = False, quality: str | None = None, audio_only: bool = False):
        """Muat turun mengikut platform: YT=yt-dlp, TT=tikwm, IG/FB/X/Reddit/Threads=yt-dlp(+cookies platform)."""
        # 0. Normalkan URL (khususnya Instagram Share Link /s/...)
        self.clear_cancel()
        original_url = url
        url = normalize_url(url)
        platform = detect_platform(url)
        logger.info(f"📌 Platform dikesan: {platform}")

        # 0b. TikTok → tikwm sahaja (TANPA cookies Instagram)
        if platform == "tiktok":
            logger.info("🎵 TikTok → menggunakan tikwm.com (tanpa cookies IG)")
            try:
                ok = TikTokHandler.download_video(url)
                if ok:
                    HistoryManager.add_record(url, "TikTok", url, 0)
                return ok
            except Exception as e:
                logger.error(f"Ralat TikTok/tikwm: {e}")
                return False

        # 0c. Instagram Story / Highlight → gallery-dl dulu (yt-dlp kerap "unreachable")
        u_low = url.lower()
        if platform == "instagram" and (
            "/stories/" in u_low
            or "/s/" in u_low
            or "story_media_id" in u_low
            or "/highlights/" in u_low
        ):
            logger.info("📖 Instagram Story/Highlight → cuba gallery-dl dulu...")
            if self._try_gallery_dl(url, "instagram"):
                HistoryManager.add_record(url, "instagram", url, 0)
                return True
            logger.warning("gallery-dl gagal/tidak ada — teruskan yt-dlp...")

        # 1. Semak jika URL wujud dalam sejarah dan MINTA PENGESAHAN OVERWRITE
        # (Langkau semasa retry automatik selepas update yt-dlp)
        if not _retried and (HistoryManager.is_downloaded(url) or HistoryManager.is_downloaded(original_url)):
            if non_interactive:
                # Web UI: overwrite terus tanpa Confirm (elak stuck di terminal)
                logger.info("♻️  URL pernah dimuat turun — overwrite (Web UI).")
            else:
                console.print(f"\n[bold yellow]⚠️  AMARAN:[/bold yellow] Link ini pernah dimuat turun sebelum ini:")
                console.print(f"[dim]{url}[/dim]")
                overwrite = Confirm.ask("[bold cyan]Adakah anda ingin memuat turun semula & MENINDIH (overwrite) fail ini?[/bold cyan]", default=False)
                if not overwrite:
                    logger.info("Muat turun dibatalkan oleh pengguna (tidak menindih fail lama).")
                    return False

        progress_manager = ProgressManager()
        info_opts = {'quiet': True, 'no_warnings': True, 'extract_flat': False}
        info_opts = self._apply_cookies(info_opts, platform=platform)
        if platform == "youtube":
            info_opts = self._youtube_opts(info_opts)
        
        try:
            with yt_dlp.YoutubeDL(info_opts) as ydl:
                logger.info(f"Mengambil metadata dari {url}...")
                try:
                    info = ydl.extract_info(url, download=False)
                except Exception as meta_err:
                    # Instagram photo post kadang raise "No video formats found" semasa extract
                    if "no video formats" in str(meta_err).lower():
                        logger.info("📸 Metadata terhad (mungkin gambar). Cuba extract semula dengan format longgar...")
                        loose_opts = dict(info_opts)
                        loose_opts["format"] = "best"
                        loose_opts["ignore_no_formats_error"] = True
                        with yt_dlp.YoutubeDL(loose_opts) as ydl2:
                            info = ydl2.extract_info(url, download=False)
                        if not info:
                            raise meta_err
                    else:
                        raise
                
            filesize = info.get('filesize_approx') or info.get('filesize', 0)
            if filesize and not check_disk_space(Settings.DOWNLOAD_DIR, filesize + (100 * 1024 * 1024)):
                logger.error("Ruang storan tidak mencukupi!")
                return False

            if not skip_preview and not show_preview(info):
                logger.info("Muat turun dibatalkan oleh pengguna.")
                return False

            if quality is not None:
                pass  # guna quality + audio_only dari caller (Web UI)
            elif non_interactive or skip_preview:
                quality, audio_only = "best", False
            else:
                quality, audio_only = self._prompt_quality_choice(info.get('formats', []))

            platform = info.get('extractor_key', 'Unknown')
            author = info.get('uploader', 'Unknown')
            title = info.get('title', 'Media')
            
            ext = 'mp3' if audio_only else 'mp4'
            out_tmpl = FileManager.get_smart_path(platform, author, title, ext, url=url)
            
            dl_opts = {
                'outtmpl': out_tmpl,
                'quiet': True,
                'no_warnings': True,
                'progress_hooks': [self._make_progress_hook(progress_manager)],
                'nocheckcertificate': True,
                'concurrent_fragment_downloads': 8,
                'buffersize': 1024 * 1024,
                'http_chunk_size': 10485760,
                'retries': 10,
                'fragment_retries': 10,
                'continuedl': True,   # sokong resume fail .part
                'nopart': False,
            }
            dl_opts = self._apply_cookies(dl_opts, platform=platform)
            if platform == "youtube":
                dl_opts = self._youtube_opts(dl_opts)

            if self.has_aria2c:
                dl_opts.update({
                    'external_downloader': 'aria2c',
                    'external_downloader_args': ['-x16', '-s16', '-k1M', '--min-split-size=1M']
                })

            # Semak sama ada kandungan ada video atau gambar sahaja
            formats = info.get("formats") or []
            has_video = any(
                (f.get("vcodec") not in (None, "none"))
                for f in formats
            )
            # Instagram / FB kadang letak gambar tanpa vcodec yang jelas
            is_instagram = "instagram" in (platform or "").lower() or "instagram.com" in url.lower()

            if audio_only:
                logger.info("Mod Audio Sahaja dipilih. Memproses ke format MP3...")
                dl_opts.update({
                    'format': 'bestaudio/best',
                    'postprocessors': [{
                        'key': 'FFmpegExtractAudio',
                        'preferredcodec': 'mp3',
                        'preferredquality': '192',
                    }],
                })
            elif not has_video:
                # Gambar / carousel / photo post
                logger.info("📸 Kandungan dikesan sebagai gambar (bukan video).")
                ext = "jpg"
                out_tmpl = FileManager.get_smart_path(platform, author, title, ext, url=url)
                dl_opts["outtmpl"] = out_tmpl
                dl_opts.update({
                    "format": "best",
                    "writethumbnail": False,
                })
            else:
                q = (quality or "best")
                is_yt = (platform or "").lower() in ("youtube", "youtu")
                # YouTube android client: jangan paksa bestvideo+bestaudio / avc1
                if is_yt:
                    height = None
                    if isinstance(q, str) and q.lower().endswith("p") and q[:-1].isdigit():
                        height = q[:-1]
                    elif isinstance(q, str) and q.isdigit():
                        height = q
                    if height:
                        quality_str = f"best[height<={height}]/best"
                    else:
                        quality_str = "best"
                elif q == "best":
                    quality_str = (
                        "best[vcodec^=avc1][ext=mp4]/"
                        "best[ext=mp4]/"
                        "bestvideo+bestaudio/best"
                    )
                elif isinstance(q, str) and any(c in q for c in "[]+/"):
                    quality_str = q if "/best" in q else (q + "/best")
                else:
                    height = str(q).lower().replace("p", "").strip()
                    if height.isdigit():
                        quality_str = (
                            f"best[height<={height}][ext=mp4]/"
                            f"best[height<={height}]/"
                            f"bestvideo[height<={height}]+bestaudio/best"
                        )
                    else:
                        quality_str = "best"

                logger.info(f"🎞️  Format dipilih: {quality_str}")
                dl_opts["format"] = quality_str
                if not is_yt:
                    dl_opts["merge_output_format"] = "mp4"

            try:
                with yt_dlp.YoutubeDL(dl_opts) as ydl:
                    ydl.download([url])
            except Exception as dl_err:
                err_low = str(dl_err).lower()
                if "requested format is not available" in err_low or "no video formats" in err_low:
                    logger.info("🔄 Retry YouTube/format: best + client android/web ...")
                    retry_opts = dict(dl_opts)
                    retry_opts["format"] = "best"
                    retry_opts.pop("merge_output_format", None)
                    if (platform or "").lower() in ("youtube", "youtu"):
                        retry_opts = self._youtube_opts(
                            retry_opts,
                            clients=["android", "ios", "mweb", "web"],
                        )
                    try:
                        with yt_dlp.YoutubeDL(retry_opts) as ydl:
                            ydl.download([url])
                    except Exception as dl_err2:
                        err2 = str(dl_err2).lower()
                        if "no video formats" in err2:
                            logger.info("🔄 Fallback gambar...")
                            img_opts = dict(retry_opts)
                            img_opts.pop("postprocessors", None)
                            img_opts["format"] = "best"
                            img_opts["outtmpl"] = FileManager.get_smart_path(
                                platform, author, title, "jpg", url=url
                            )
                            with yt_dlp.YoutubeDL(img_opts) as ydl:
                                ydl.download([url])
                        else:
                            raise dl_err2
                else:
                    raise
                
            HistoryManager.add_record(url, platform, title, filesize)
            FileManager.clean_temp_files()
            return True

        except KeyboardInterrupt:
            action = self._ask_resume_or_cancel(non_interactive=non_interactive)
            if action == "resume":
                logger.info("▶️  Resume muat turun...")
                # Jangan guna aria2c semasa resume (lebih stabil dengan native yt-dlp)
                return self._sync_ytdlp_download(
                    url,
                    skip_preview=True,
                    _retried=_retried,
                    non_interactive=non_interactive,
                )
            logger.info("🛑 Muat turun dibatalkan oleh pengguna.")
            return False

        except Exception as e:
            err_msg = str(e)

            # Auto-update yt-dlp + retry sekali untuk ralat extractor
            if (not _retried) and self._is_extractor_error(err_msg):
                logger.warning(f"Ralat extractor dikesan. Cuba update yt-dlp & muat turun semula...")
                if self._silent_update_ytdlp():
                    # Cuba semula (skip history prompt kali kedua — guna skip_preview True untuk elak tanya berulang)
                    return self._sync_ytdlp_download(url, skip_preview=True, _retried=True, non_interactive=non_interactive, quality=quality, audio_only=audio_only)
                # Jika update gagal, terus tunjuk error

            # Fallback gallery-dl untuk IG Story/Highlight & gambar
            plat = detect_platform(url)
            low_err = err_msg.lower()
            ig_auth_fail = (
                "unreachable" in low_err
                or "cookies" in low_err
                or "authentication" in low_err
                or "login required" in low_err
                or "rate-limit" in low_err
            )
            if plat in ("instagram", "reddit", "twitter") and (
                "no video formats" in low_err
                or "unsupported url" in low_err
                or ig_auth_fail
                or self._is_extractor_error(err_msg)
                or "instagram.com/stories" in url.lower()
                or "instagram.com/s/" in url.lower()
            ):
                logger.info("🖼️  Cuba gallery-dl (sesuai untuk IG Story)...")
                if self._try_gallery_dl(url, plat):
                    HistoryManager.add_record(url, plat, url, 0)
                    return True

            logger.error(f"Ralat sewaktu muat turun: {err_msg}")
            self._show_download_error_tips(err_msg, url)
            return False

    async def download_batch(self, urls: list, skip_preview: bool = False, non_interactive: bool = False):
        """Memuat turun senarai URL secara asynchronous/concurrently."""
        loop = asyncio.get_running_loop()

        # Mode interaktif + 1 URL: jalan segerak supaya Ctrl+C terus ditangkap
        if not non_interactive and len(urls) == 1:
            try:
                await loop.run_in_executor(
                    None,  # default executor, still thread but we also trap below
                    lambda: self._sync_ytdlp_download(
                        urls[0], skip_preview=skip_preview, non_interactive=non_interactive
                    ),
                )
            except KeyboardInterrupt:
                self.request_cancel()
                action = self._ask_resume_or_cancel(non_interactive=False)
                if action == "resume":
                    logger.info("▶️  Resume muat turun...")
                    await loop.run_in_executor(
                        None,
                        lambda: self._sync_ytdlp_download(
                            urls[0], skip_preview=True, non_interactive=False
                        ),
                    )
                else:
                    logger.info("🛑 Muat turun dibatalkan oleh pengguna.")
            logger.info("✅ Semua proses batch selesai!")
            return

        tasks = []
        for url in urls:
            task = loop.run_in_executor(
                self.executor,
                lambda u=url: self._sync_ytdlp_download(
                    u, skip_preview=skip_preview, non_interactive=non_interactive
                ),
            )
            tasks.append(task)

        if tasks:
            try:
                await asyncio.gather(*tasks)
            except KeyboardInterrupt:
                self.request_cancel()
                logger.info("🛑 Batch dihentikan (Ctrl+C).")
            logger.info("✅ Semua proses batch selesai!")
