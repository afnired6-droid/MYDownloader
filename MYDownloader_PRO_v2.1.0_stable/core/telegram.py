"""
Pengendalian Muat Turun Telegram (Saved Messages, Channels, Stories).
Progress bar premium (Rich) — bukan spam log %.
"""
import os
import time
import asyncio
from utils.logger import logger
from config.settings import Settings
from core.client import app
from rich.progress import (
    Progress,
    SpinnerColumn,
    TextColumn,
    BarColumn,
    DownloadColumn,
    TransferSpeedColumn,
    TimeRemainingColumn,
)
from rich.console import Console

try:
    from hydrogram.errors import FloodWait
except ImportError:
    try:
        from pyrogram.errors import FloodWait
    except ImportError:
        FloodWait = Exception

_TG_SEM = asyncio.Semaphore(3)
_console = Console()


class TelegramDownloader:
    @staticmethod
    def _has_downloadable(message) -> bool:
        return bool(
            getattr(message, "document", None)
            or getattr(message, "audio", None)
            or getattr(message, "video", None)
            or getattr(message, "photo", None)
            or getattr(message, "voice", None)
            or getattr(message, "animation", None)
            or getattr(message, "video_note", None)
            or getattr(message, "sticker", None)
            or getattr(message, "media", None)
        )

    @staticmethod
    async def download_media(message, progress_callback=None):
        """Muat turun media Telegram dengan progress bar premium."""
        if not TelegramDownloader._has_downloadable(message):
            logger.warning("Mesej ini tiada media yang boleh dimuat turun.")
            return None

        async with _TG_SEM:
            try:
                preferred = None
                if message.document and message.document.file_name:
                    preferred = message.document.file_name
                elif message.audio and message.audio.file_name:
                    preferred = message.audio.file_name
                elif message.audio and message.audio.title:
                    preferred = f"{message.audio.title}.mp3"

                out_dir = os.path.join(Settings.DOWNLOAD_DIR, "Telegram")
                os.makedirs(out_dir, exist_ok=True)
                file_name = os.path.join(out_dir, preferred) if preferred else os.path.join(out_dir, "")

                label = (preferred or "Telegram media")[:40]

                # Jika caller bagi callback sendiri, guna itu
                if progress_callback is not None:
                    logger.info(f"⚡ Memuat turun... → {label}")
                    t0 = time.time()
                    file_path = await message.download(
                        file_name=file_name,
                        progress=progress_callback,
                    )
                else:
                    # Progress bar Rich (satu bar kemas)
                    with Progress(
                        SpinnerColumn(style="cyan"),
                        TextColumn("[bold cyan]{task.description}"),
                        BarColumn(
                            bar_width=28,
                            complete_style="green",
                            finished_style="bold green",
                            pulse_style="cyan",
                        ),
                        TextColumn("[bold white]{task.percentage:>5.1f}%"),
                        "•",
                        DownloadColumn(),
                        "•",
                        TransferSpeedColumn(),
                        "•",
                        TimeRemainingColumn(),
                        console=_console,
                        transient=False,
                    ) as progress:
                        task_id = progress.add_task(f"📥 {label}", total=None)

                        def _hook(current, total):
                            if total and total > 0:
                                progress.update(task_id, total=total, completed=current)
                            else:
                                progress.update(task_id, completed=current)

                        t0 = time.time()
                        file_path = await message.download(
                            file_name=file_name,
                            progress=_hook,
                        )
                        # Pastikan bar 100%
                        try:
                            final_size = os.path.getsize(file_path) if file_path else 0
                            if final_size:
                                progress.update(task_id, total=final_size, completed=final_size)
                        except Exception:
                            pass

                dt = max(time.time() - t0, 0.001)
                size = 0
                try:
                    size = os.path.getsize(file_path) if file_path else 0
                except Exception:
                    pass
                speed = size / dt
                if speed > 1024 * 1024:
                    spd = f"{speed / 1024 / 1024:.1f} MB/s"
                else:
                    spd = f"{speed / 1024:.0f} KB/s"
                logger.info(f"✅ Selesai ({spd}): {file_path}")
                return file_path

            except FloodWait as e:
                wait = getattr(e, "value", 5)
                logger.warning(f"Terkena FloodWait. Menunggu {wait} saat...")
                await asyncio.sleep(wait)
                return await TelegramDownloader.download_media(message, progress_callback)
            except Exception as e:
                logger.error(f"Ralat memuat turun dari Telegram: {e}")
                return None

    @staticmethod
    async def download_many(messages: list) -> list:
        """Muat turun beberapa mesej secara selari (max 3)."""
        tasks = [TelegramDownloader.download_media(m) for m in messages]
        return await asyncio.gather(*tasks, return_exceptions=True)

    @staticmethod
    async def get_saved_messages(limit: int = 10):
        """Ambil mesej bermedia dari Saved Messages."""
        messages = []
        async for msg in app.get_chat_history("me", limit=limit):
            if TelegramDownloader._has_downloadable(msg):
                messages.append(msg)
        return messages
