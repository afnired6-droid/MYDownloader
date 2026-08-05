"""
Pengendali API TikTok (tikwm.com) untuk Video dan Photo Slides.
Termasuk Pilihan Overwrite Interaktif jika fail wujud.
"""
import os
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed
from config.settings import Settings
from utils.logger import logger
from core.social.converter import MediaConverter
from rich.console import Console
from rich.prompt import Confirm, Prompt

console = Console()

class TikTokHandler:
    API_URL = "https://www.tikwm.com/api/"

    _session = None

    @classmethod
    def _get_session(cls) -> requests.Session:
        """Session dikongsi (connection reuse = lebih laju)."""
        if cls._session is None:
            s = requests.Session()
            s.headers.update({
                "User-Agent": "Mozilla/5.0 (Linux; Android 13) AppleWebKit/537.36 Chrome/120.0.0.0 Mobile Safari/537.36",
                "Accept": "*/*",
                "Connection": "keep-alive",
            })
            adapter = requests.adapters.HTTPAdapter(
                pool_connections=8,
                pool_maxsize=8,
                max_retries=2,
            )
            s.mount("https://", adapter)
            s.mount("http://", adapter)
            cls._session = s
        return cls._session

    @classmethod
    def _noninteractive(cls) -> bool:
        """True bila Web UI / batch — jangan ever block Confirm di terminal."""
        import os
        if os.environ.get("MYD_NONINTERACTIVE", "").strip() in ("1", "true", "yes"):
            return True
        try:
            import sys
            return not sys.stdin.isatty()
        except Exception:
            return True

    @classmethod
    def _confirm(cls, message: str, default: bool = False) -> bool:
        if cls._noninteractive():
            # Web UI: jangan block — treat as yes
            return True
        return Confirm.ask(message, default=default)


    @classmethod
    def get_info(cls, url: str) -> dict:
        session = cls._get_session()
        try:
            response = session.post(cls.API_URL, data={"url": url, "hd": 1}, timeout=(5, 15))
            data = response.json()
            if data.get("code") == 0:
                return data.get("data", {})
            else:
                logger.error(f"Ralat API TikTok: {data.get('msg')}")
                return {}
        except Exception as e:
            logger.error(f"Gagal menghubungi API TikTok: {e}")
            return {}

    @classmethod
    def _download_single_image(cls, session: requests.Session, img_url: str, save_path: str, index: int) -> tuple[int, bool, float]:
        if img_url.startswith("//"):
            img_url = "https:" + img_url
        try:
            res = session.get(img_url, timeout=10)
            if res.status_code == 200:
                with open(save_path, 'wb') as f:
                    f.write(res.content)
                size_kb = len(res.content) / 1024
                return index, True, size_kb
        except Exception:
            pass
        return index, False, 0.0



    @classmethod
    def _extract_image_urls(cls, data: dict) -> list[str]:
        """Normalisasi senarai URL gambar dari pelbagai bentuk respons tikwm."""
        raw = data.get("images") or []
        urls = []
        for item in raw:
            if isinstance(item, str) and item.strip():
                u = item.strip()
            elif isinstance(item, dict):
                u = (
                    item.get("url")
                    or item.get("image")
                    or item.get("display_image")
                    or item.get("thumb")
                    or ""
                )
                if isinstance(u, list) and u:
                    u = u[0]
                u = (u or "").strip()
            else:
                u = ""
            if not u:
                continue
            if u.startswith("//"):
                u = "https:" + u
            urls.append(u)
        # Buang duplikat kekalkan order
        seen = set()
        out = []
        for u in urls:
            if u not in seen:
                seen.add(u)
                out.append(u)
        return out

    @classmethod
    def download_video(cls, url: str) -> bool:
        """Muat turun video TikTok biasa (bukan slide) melalui tikwm — tanpa cookies IG."""
        data = cls.get_info(url)
        if not data:
            return False

        # Slide → Menu 1 jangan auto-download; arahkan ke Menu 2
        images = cls._extract_image_urls(data)
        if images:
            if cls._noninteractive():
                # Web UI: terus proses sebagai slide video
                author = data.get("author", {}).get("unique_id") or data.get("author", {}).get("nickname") or "tiktok"
                title = (data.get("title") or "slide")[:40]
                safe = "".join(c for c in f"{author}_{title}" if c.isalnum() or c in "._- ")[:80] or "tiktok_slide"
                return bool(cls.download_slide_as_video(data, f"TikTok_{safe}"))
            console.print("\n[bold yellow]🎞  Ini TikTok SLIDE (gambar), bukan video biasa.[/bold yellow]")
            console.print("   Sila guna [bold cyan]Menu 2[/bold cyan] → pilih MP4 / Images / Audio.\n")
            logger.info("Slide dikesan di Menu 1 — diarahkan ke Menu 2 (tiada download).")
            return False

        def _fmt_size(n):
            try:
                n = float(n or 0)
            except (TypeError, ValueError):
                return "N/A"
            if n <= 0:
                return "N/A"
            for u in ("B", "KB", "MB", "GB"):
                if n < 1024:
                    return f"{n:.1f} {u}"
                n /= 1024
            return f"{n:.1f} TB"

        # Metadata live dari tikwm (hanya yang benar-benar ada)
        w = data.get("width") or data.get("origin_width")
        h = data.get("height") or data.get("origin_height")
        ratio = data.get("ratio") or (f"{w}x{h}" if w and h else None)
        duration = data.get("duration")
        dur_str = f"{int(duration)}s" if duration else "?"

        candidates = []
        # (url_key, url, full_label, size_str)
        for url_key, size_key, label in (
            ("hdplay", "hd_size", "HD · tanpa watermark"),
            ("play", "size", "Standard · tanpa watermark"),
            ("wmplay", "wm_size", "Dengan watermark"),
        ):
            u = data.get(url_key)
            if not u:
                continue
            size_str = _fmt_size(data.get(size_key))
            res_bit = f"{ratio}" if ratio else ""
            detail = " · ".join(x for x in (res_bit, size_str, dur_str) if x and x != "N/A")
            full_label = f"{label}" + (f"  ({detail})" if detail else "")
            candidates.append((url_key, u, full_label, size_str))

        if not candidates:
            logger.error("Tiada URL video dari tikwm.")
            return False

        if cls._noninteractive():
            # Web UI: hormati MYD_TIKTOK_QUALITY=hdplay|play|wmplay
            pref = (os.environ.get("MYD_TIKTOK_QUALITY") or "hdplay").strip().lower()
            chosen = next((c for c in candidates if c[0] == pref), None) or candidates[0]
            video_url = chosen[1]
            qlabel = chosen[2]
            logger.info(f"TikTok Web quality: {pref} → {qlabel}")
        else:
            from rich.table import Table
            table = Table(
                title="[bold cyan]📊 Kualiti TikTok LIVE (tikwm)[/bold cyan]",
                border_style="cyan",
            )
            table.add_column("No", style="bold yellow", justify="center")
            table.add_column("Pilihan tersedia", style="bold green")
            table.add_column("Saiz", style="magenta")
            quality_opts = []
            for i, (url_key, u, label, size_str) in enumerate(candidates, 1):
                num = str(i)
                quality_opts.append((num, label, u))
                table.add_row(num, label, size_str)
            console.print("\n", table)
            choices = [o[0] for o in quality_opts]
            sel = Prompt.ask(
                "\n[bold green]Pilih kualiti yang tersedia[/bold green]",
                choices=choices,
                default=choices[0],
            )
            video_url = next(o[2] for o in quality_opts if o[0] == sel)
            qlabel = next(o[1] for o in quality_opts if o[0] == sel)
            console.print(f"[dim]Dipilih: {qlabel}[/dim]")

        if video_url.startswith("//"):
            video_url = "https:" + video_url

        author = data.get("author", {}).get("unique_id") or data.get("author", {}).get("nickname") or "tiktok"
        title = (data.get("title") or data.get("id") or "video")[:60]
        safe = "".join(c for c in f"{author}_{title}" if c.isalnum() or c in "._- ")[:80] or "tiktok_video"
        out_path = os.path.join(Settings.DOWNLOAD_DIR, "TikTok", "Videos", f"TikTok_{safe}.mp4")
        os.makedirs(os.path.dirname(out_path), exist_ok=True)

        if os.path.exists(out_path):
            if cls._noninteractive():
                # Web UI: overwrite terus, jangan tanya Confirm (elak stuck)
                logger.info(f"♻️  Fail wujud — overwrite: {out_path}")
                try:
                    os.remove(out_path)
                except Exception:
                    pass
            else:
                console.print(f"\n[bold yellow]⚠️  Fail sudah wujud:[/bold yellow] [dim]{out_path}[/dim]")
                if not cls._confirm("[bold cyan]Tindih (overwrite)?[/bold cyan]", default=False):
                    return False

        session = cls._get_session()
        try:
            console.print("\n[bold yellow]⚡ Memuat turun video TikTok (tikwm, no watermark)...[/bold yellow]")
            # timeout=(connect, read) — elak hang lama
            res = session.get(video_url, timeout=(8, 120), stream=True)
            res.raise_for_status()
            total = 0
            with open(out_path, "wb") as f:
                for chunk in res.iter_content(chunk_size=1024 * 1024):  # 1MB chunks
                    if chunk:
                        f.write(chunk)
                        total += len(chunk)
            size_mb = total / (1024 * 1024)
            console.print(f"[bold green]🎉 Berjaya:[/bold green] {out_path} ({size_mb:.2f} MB)")
            return True
        except Exception as e:
            logger.error(f"Gagal muat turun video TikTok: {e}")
            return False

    @classmethod
    def download_images_only(cls, data: dict, output_name: str):
        folder = os.path.join(Settings.DOWNLOAD_DIR, "TikTok", "Images", output_name)
        if os.path.exists(folder) and os.listdir(folder):
            console.print(f"\n[bold yellow]⚠️  AMARAN:[/bold yellow] Folder gambar ini sudah wujud:")
            console.print(f"[dim]{folder}[/dim]")
            if not cls._confirm("[bold cyan]Adakah anda ingin memuat turun semula & MENINDIH gambar lama?[/bold cyan]", default=False):
                logger.info("Dibatalkan oleh pengguna.")
                return

        images = cls._extract_image_urls(data)
        if not images:
            logger.error("Tiada data gambar dijumpai.")
            return

        os.makedirs(folder, exist_ok=True)
        console.print(f"\n[bold yellow]⚡ Memuat turun {len(images)} gambar asli secara PANTAS...[/bold yellow]")
        
        session = cls._get_session()
        results = [None] * len(images)
        
        with ThreadPoolExecutor(max_workers=min(10, len(images))) as executor:
            futures = []
            for i, img_url in enumerate(images):
                path = os.path.join(folder, f"slide_{i+1:02d}.jpg")
                futures.append(executor.submit(cls._download_single_image, session, img_url, path, i))
            
            for future in as_completed(futures):
                idx, success, size_kb = future.result()
                results[idx] = (success, size_kb)

        for i, res in enumerate(results):
            if res and res[0]:
                console.print(f"  [green]Gambar {i+1} ✅[/green] [cyan](Saiz: {res[1]:.2f} KB)[/cyan]")
            else:
                console.print(f"  [red]Gambar {i+1} ❌ Gagal[/red]")
                
        console.print(f"\n[bold green]🎉 Semua gambar berjaya disimpan dalam folder: {folder}[/bold green]")

    @classmethod
    def download_audio_only(cls, data: dict, output_name: str):
        path = os.path.join(Settings.DOWNLOAD_DIR, "TikTok", "Audio", f"{output_name}_audio.mp3")
        os.makedirs(os.path.dirname(path), exist_ok=True)
        if os.path.exists(path):
            console.print(f"\n[bold yellow]⚠️  AMARAN:[/bold yellow] Fail audio ini sudah wujud:")
            console.print(f"[dim]{path}[/dim]")
            if not cls._confirm("[bold cyan]Adakah anda ingin memuat turun semula & MENINDIH audio lama?[/bold cyan]", default=False):
                logger.info("Dibatalkan oleh pengguna.")
                return

        audio_url = data.get("music_info", {}).get("play")
        if not audio_url:
            logger.error("Tiada audio/muzik dijumpai.")
            return

        if audio_url.startswith("//"):
            audio_url = "https:" + audio_url
            
        session = cls._get_session()
        try:
            console.print("\n[bold yellow]⚡ Memuat turun audio latar...[/bold yellow]")
            res = session.get(audio_url, timeout=15)
            if res.status_code == 200:
                size_mb = len(res.content) / (1024 * 1024)
                with open(path, 'wb') as f:
                    f.write(res.content)
                console.print(f"  [green]Audio Latar ✅[/green] [cyan](Saiz: {size_mb:.2f} MB)[/cyan]")
                console.print(f"\n[bold green]🎉 Audio berjaya disimpan di: {path}[/bold green]")
        except Exception as e:
            console.print(f"  [red]Audio ❌ Gagal dimuat turun: {e}[/red]")

    @classmethod
    def download_slide_as_video(cls, data: dict, output_name: str):
        output_path = os.path.join(Settings.DOWNLOAD_DIR, "TikTok", "Slides", f"{output_name}.mp4")
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        if os.path.exists(output_path):
            console.print(f"\n[bold yellow]⚠️  AMARAN:[/bold yellow] Fail video ini sudah wujud:")
            console.print(f"[dim]{output_path}[/dim]")
            if not cls._confirm("[bold cyan]Adakah anda ingin membina semula & MENINDIH video lama?[/bold cyan]", default=False):
                logger.info("Dibatalkan oleh pengguna.")
                return

        images = cls._extract_image_urls(data)
        audio_url = data.get("music_info", {}).get("play")
        
        if not images:
            logger.error("Tiada data gambar dijumpai untuk slide ini.")
            return

        logger.info(f"🖼️  {len(images)} gambar dikesan dari tikwm")

        console.print(f"\n[bold yellow]⚡ Memuat turun {len(images)} bahan secara SELENTAR...[/bold yellow]")
        
        session = cls._get_session()
        temp_images_dict = {}
        
        with ThreadPoolExecutor(max_workers=min(10, len(images))) as executor:
            futures = []
            for i, img_url in enumerate(images):
                img_path = os.path.join(Settings.TEMP_DIR, f"{output_name}_{i:03d}.jpg")
                futures.append(executor.submit(cls._download_single_image, session, img_url, img_path, i))
            
            for future in as_completed(futures):
                idx, success, size_kb = future.result()
                if success:
                    img_path = os.path.join(Settings.TEMP_DIR, f"{output_name}_{idx:03d}.jpg")
                    temp_images_dict[idx] = (img_path, size_kb)

        ordered_indices = sorted(temp_images_dict.keys())
        temp_images = [temp_images_dict[idx][0] for idx in ordered_indices]

        for idx in range(len(images)):
            if idx in temp_images_dict:
                size_kb = temp_images_dict[idx][1]
                console.print(f"  [green]Gambar {idx+1} ✅[/green] [cyan](Saiz: {size_kb:.2f} KB)[/cyan]")
            else:
                console.print(f"  [red]Gambar {idx+1} ❌ Gagal[/red]")

        if not temp_images:
            logger.error("Kesemua gambar gagal dimuat turun.")
            return

        audio_path = None
        if audio_url:
            if audio_url.startswith("//"):
                audio_url = "https:" + audio_url
            try:
                audio_path = os.path.join(Settings.TEMP_DIR, f"{output_name}.mp3")
                audio_res = session.get(audio_url, timeout=10)
                if audio_res.status_code == 200:
                    size_mb = len(audio_res.content) / (1024 * 1024)
                    with open(audio_path, 'wb') as f:
                        f.write(audio_res.content)
                    console.print(f"  [green]Audio MP3 ✅[/green] [cyan](Saiz: {size_mb:.2f} MB)[/cyan]")
                else:
                    audio_path = None
            except Exception:
                audio_path = None

        console.print("\n[bold yellow]⚙️ Menyatukan Gambar & Audio menjadi Video MP4...[/bold yellow]")
        success = MediaConverter.images_to_video(temp_images, audio_path, output_path)

        for img in temp_images:
            if os.path.exists(img):
                os.remove(img)
        if audio_path and os.path.exists(audio_path):
            os.remove(audio_path)

        if success:
            console.print(f"  [green]Video MP4 ✅[/green] [cyan]Berjaya dicipta! (1080p Auto)[/cyan]")
            console.print(f"\n[bold green]🎉 Disimpan di: {output_path}[/bold green]")