"""
MYDownloader PRO - Universal Social Media & Telegram Downloader
Versi: 2.1.0 PRO Final
"""
import asyncio
import sys
import re
import os
from core.client import app
from hydrogram import filters, raw
from hydrogram.raw.functions.stories import GetPeerStories, GetPinnedStories
from hydrogram.types import Photo, Document
from ui.menu import main_menu, console, show_settings_menu, VERSION
from core.social.tiktok import TikTokHandler
from core.telegram import TelegramDownloader
from core.downloader import CoreDownloader
from utils.logger import logger
from utils.helpers import termux_notify
from config.settings import Settings
from utils.i18n import t, load_language
from rich.prompt import Prompt
from rich.table import Table

# Status kawalan: Telegram Live hanya aktif apabila berada di Menu 3
telegram_live_active = False


# --- FUNGSI PANTAUAN MASA NYATA (LIVE) TELEGRAM ---
_live_seen_ids: set[int] = set()

def _msg_has_media(message) -> bool:
    return bool(
        getattr(message, "document", None)
        or getattr(message, "audio", None)
        or getattr(message, "video", None)
        or getattr(message, "photo", None)
        or getattr(message, "voice", None)
        or getattr(message, "animation", None)
        or getattr(message, "video_note", None)
    )

async def _live_download_message(message):
    kind = (
        "document" if message.document else
        "audio" if message.audio else
        "video" if message.video else
        "photo" if message.photo else
        "voice" if message.voice else
        "media"
    )
    name = None
    if message.document and message.document.file_name:
        name = message.document.file_name
    elif message.audio and (message.audio.file_name or message.audio.title):
        name = message.audio.file_name or message.audio.title

    logger.info("\n" + t("tg_live_detect", kind=kind, name=(f": {name}" if name else "")))
    try:
        path = await TelegramDownloader.download_media(message)
        if path:
            termux_notify("Telegram Live", f"Berjaya: {name or kind}")
            logger.info(t("tg_live_done", path=path))
        else:
            logger.warning("⚠️ [LIVE] Download pulangkan kosong.")
    except Exception as e:
        logger.error(f"Gagal memuat turun media live: {e}")

# Handler push (backup) — longgar: semua incoming private
@app.on_message(filters.incoming & filters.private)
async def auto_download_live(client, message):
    if not telegram_live_active:
        return
    # Saved Messages = chat dengan diri sendiri
    try:
        me = await client.get_me()
        if not message.chat or message.chat.id != me.id:
            return
    except Exception:
        return
    if not _msg_has_media(message):
        return
    if message.id in _live_seen_ids:
        return
    _live_seen_ids.add(message.id)
    await _live_download_message(message)

async def _live_poll_saved_messages(stop_event: asyncio.Event):
    """Poll Saved Messages setiap 2 saat — lebih stabil dari handler sahaja."""
    global _live_seen_ids
    logger.info(t("tg_poller_start"))
    # Seed: tandakan mesej sedia ada supaya tak auto-download yang lama
    try:
        async for msg in app.get_chat_history("me", limit=15):
            _live_seen_ids.add(msg.id)
    except Exception as e:
        logger.warning(f"Gagal seed history: {e}")

    while not stop_event.is_set():
        try:
            async for msg in app.get_chat_history("me", limit=10):
                if msg.id in _live_seen_ids:
                    continue
                _live_seen_ids.add(msg.id)
                if _msg_has_media(msg):
                    await _live_download_message(msg)
        except Exception as e:
            # Jangan spam — connection drop sementara biasa di Termux
            msg = str(e).lower()
            if "socket" in msg or "disconnect" in msg or "connection" in msg:
                pass
            else:
                logger.debug(f"Poll error: {e}")
        try:
            await asyncio.wait_for(stop_event.wait(), timeout=2.0)
        except asyncio.TimeoutError:
            pass
    logger.info(t("tg_poller_stop"))
# ---------------------------------------------------



async def _download_stories_media(stories_list, username: str, label: str = "Story") -> int:
    """Muat turun senarai story (active / pinned) secara SELARI (max 3)."""
    if not stories_list:
        return 0

    logger.info(f"✅ Ditemui {len(stories_list)} {label}! Memulakan muat turun (parallel)...")
    tg_dir = os.path.join(Settings.DOWNLOAD_DIR, "Telegram")
    os.makedirs(tg_dir, exist_ok=True)
    sem = asyncio.Semaphore(3)

    async def _one(s):
        ext = ".jpg"
        media_file_id = None

        if not hasattr(s, "media") or not s.media:
            logger.warning(f"⚠️ {label} ID {s.id} tiada fail media (Teks sahaja / Dilindungi).")
            return 0

        if hasattr(s.media, "photo") and s.media.photo:
            try:
                parsed = Photo._parse(app, s.media.photo)
                if parsed:
                    media_file_id = parsed.file_id
                    ext = ".jpg"
            except Exception as e:
                logger.error(f"Ralat mengekstrak Photo ID {s.id}: {e}")

        elif hasattr(s.media, "document") and s.media.document:
            try:
                doc = s.media.document
                file_name = None
                if hasattr(doc, "attributes") and doc.attributes:
                    for attr in doc.attributes:
                        if isinstance(attr, raw.types.DocumentAttributeFilename):
                            file_name = attr.file_name
                            break

                parsed = Document._parse(app, doc, file_name)
                if parsed:
                    media_file_id = parsed.file_id
                    if file_name and "." in file_name:
                        ext = os.path.splitext(file_name)[1].lower()
                    else:
                        mime = getattr(doc, "mime_type", "") or ""
                        if "video" in mime:
                            ext = ".mp4"
                        elif "image" in mime or "jpeg" in mime or "png" in mime:
                            ext = ".jpg"
                        elif "gif" in mime:
                            ext = ".gif"
                        else:
                            ext = ".mp4"
            except Exception as e:
                logger.error(f"Ralat mengekstrak Document ID {s.id}: {e}")

        if not media_file_id:
            logger.warning(f"⚠️ {label} ID {s.id} tidak dapat diproses (Gagal mendapatkan file_id).")
            return 0

        async with sem:
            try:
                prefix = "Pinned" if "Pinned" in label else "Story"
                file_path = await app.download_media(
                    media_file_id,
                    file_name=os.path.join(tg_dir, f"{prefix}_Telegram_{username}_{s.id}{ext}"),
                )
                if file_path:
                    logger.info(f"✔️ Berjaya simpan: {file_path}")
                    return 1
            except Exception as dl_e:
                logger.error(f"Ralat semasa memuat turun media ID {s.id}: {dl_e}")
        return 0

    results = await asyncio.gather(*[_one(s) for s in stories_list], return_exceptions=True)
    return sum(r for r in results if isinstance(r, int))


async def _fetch_pinned_stories(peer, limit_per_page: int = 100):
    """Ambil semua pinned stories (dengan pagination)."""
    all_stories = []
    offset_id = 0

    while True:
        result = await app.invoke(
            GetPinnedStories(peer=peer, offset_id=offset_id, limit=limit_per_page)
        )
        batch = getattr(result, "stories", None) or []
        if not batch:
            break

        all_stories.extend(batch)

        # Pagination: guna id story terakhir sebagai offset
        last_id = getattr(batch[-1], "id", None)
        if not last_id or last_id == offset_id or len(batch) < limit_per_page:
            break
        offset_id = last_id

    return all_stories


async def run_downloader():
    load_language()
    # Elak spam "socket.send() raised exception" pada console
    def _quiet_asyncio_handler(loop, context):
        msg = context.get("message") or ""
        exc = context.get("exception")
        text = f"{msg} {exc}".lower()
        if "socket.send" in text or "connection reset" in text:
            return
        # Lain-lain: biar default
        loop.default_exception_handler(context)

    try:
        asyncio.get_running_loop().set_exception_handler(_quiet_asyncio_handler)
    except Exception:
        pass

    global telegram_live_active
    telegram_client_started = False

    try:
        while True:
            pilihan, link_clipboard = main_menu()
            
            if pilihan == "CLIPBOARD":
                if link_clipboard:
                    logger.info(t("clip_process"))
                    try:
                        downloader = CoreDownloader()
                        await downloader.download_batch([link_clipboard.strip()], skip_preview=False)
                        termux_notify("Muat Turun Selesai", "Fail dari clipboard telah diproses.")
                    except Exception as e:
                        logger.error(f"Ralat memproses clipboard: {e}")
                else:
                    logger.warning("Clipboard kosong atau tiada pautan sah.")
                    
            elif pilihan == "1":
                url_input = console.input(f"\n[bold]{t('enter_url')}: [/bold]")
                urls = [u.strip().strip("'\"") for u in url_input.split(",") if u.strip()]
                
                if urls:
                    logger.info(t("processing_n", n=len(urls)))
                    try:
                        downloader = CoreDownloader()
                        await downloader.download_batch(urls, skip_preview=False)
                        termux_notify("Menu 1 Selesai", "Semua pautan berjaya diproses.")
                    except Exception as e:
                        logger.error(f"Ralat memproses pautan Menu 1: {e}")
                else:
                    logger.warning("Tiada URL dimasukkan.")
                            
            elif pilihan == "2":
                url = console.input(f"\n[bold]{t('enter_tt')}: [/bold]").strip()
                if not url:
                    logger.warning("URL TikTok tidak boleh kosong.")
                    continue
                    
                try:
                    info = TikTokHandler.get_info(url)
                    images = info.get("images", []) if info else []
                    
                    if info and images:
                        author = info.get("author", {}).get("unique_id", "Unknown")
                        title = info.get("title", "slide")[:20]
                        safe_name = f"TikTok_{author}_{title}"
                        
                        img_count = len(images)
                        music = info.get("music_info", {})
                        music_title = music.get("title", "Audio Latar")
                        music_author = music.get("author", "Tidak diketahui")
                        
                        table = Table(title="[bold cyan]📊 Pilihan TikTok Slide Secara Live[/bold cyan]", border_style="cyan")
                        table.add_column("No", style="bold yellow", justify="center")
                        table.add_column("Mod Muat Turun", style="bold green")
                        table.add_column("Detail Live (Masa Nyata)", style="white")

                        table.add_row("1", "Koleksi Gambar Sahaja (JPG)", f"Ada {img_count} keping gambar")
                        table.add_row("2", "Audio Sahaja (MP3)", f"{music_title[:30]} (Artis: {music_author[:20]})")
                        table.add_row("3", "Video Automatik (Slideshow)", f"Gabung {img_count} Gambar + Audio jadi MP4")
                        
                        console.print("\n", table)
                        choice = Prompt.ask(f"\n[bold green]{t('tt_mode_choose')}[/bold green]", choices=["1", "2", "3"], default="3")
                        
                        if choice == "1":
                            TikTokHandler.download_images_only(info, safe_name)
                        elif choice == "2":
                            TikTokHandler.download_audio_only(info, safe_name)
                        elif choice == "3":
                            TikTokHandler.download_slide_as_video(info, safe_name)
                    else:
                        logger.error("Tiada slide gambar ditemui pada URL ini. (Guna Menu 1 untuk video biasa).")
                except Exception as e:
                    logger.error(f"Ralat memproses TikTok Slide: {e}")
                        
            elif pilihan == "3":
                # Start Hydrogram client only when needed (lazy start)
                if not telegram_client_started:
                    if not Settings.validate_telegram_credentials():
                        logger.error("❌ API_ID atau API_HASH belum diset dengan betul di fail .env")
                        logger.error("   Sila edit fail .env dan masukkan API_ID + API_HASH dari https://my.telegram.org")
                        console.input(f"\n[dim]{t('press_enter')}[/dim]")
                        continue

                    logger.info(t("tg_connecting"))
                    app.loop = asyncio.get_running_loop()
                    await app.start()
                    telegram_client_started = True
                    logger.info(t("tg_ready"))

                logger.info("\n" + t("tg_menu3"))
                logger.info(t("tg_tip1"))
                logger.info(t("tg_tip2"))
                
                telegram_live_active = True
                
                try:
                    tg_input = console.input(f"\n[bold]{t('tg_prompt')}: [/bold]").strip()
                    
                    if tg_input:
                        username = tg_input.replace("@", "").replace("https://t.me/", "").strip()

                        # Pilih jenis Story
                        console.print(f"\n[bold]{t('tg_story_type')}[/bold]")
                        console.print(f"  {t('tg_story_1')}")
                        console.print(f"  {t('tg_story_2')}")
                        console.print(f"  {t('tg_story_3')}")
                        story_choice = Prompt.ask(
                            "\n[bold green]Pilih jenis[/bold green]",
                            choices=["1", "2", "3"],
                            default="1"
                        )

                        try:
                            peer = await app.resolve_peer(username)
                            total_downloaded = 0

                            # --- Active Stories ---
                            if story_choice in ("1", "3"):
                                logger.info(t("tg_fetch_active", user=username))
                                result = await app.invoke(GetPeerStories(peer=peer))
                                active_list = []
                                if hasattr(result, "stories") and hasattr(result.stories, "stories"):
                                    active_list = result.stories.stories or []

                                if not active_list:
                                    logger.info(t("tg_no_active", user=username))
                                else:
                                    count = await _download_stories_media(active_list, username, label="Active Story")
                                    total_downloaded += count

                            # --- Pinned Stories ---
                            if story_choice in ("2", "3"):
                                logger.info(t("tg_fetch_pinned", user=username))
                                try:
                                    pinned_list = await _fetch_pinned_stories(peer)
                                    if not pinned_list:
                                        logger.info(t("tg_no_pinned", user=username))
                                    else:
                                        count = await _download_stories_media(pinned_list, username, label="Pinned Story")
                                        total_downloaded += count
                                except Exception as pin_e:
                                    logger.error(f"Gagal mengambil Pinned Stories: {pin_e}")

                            # Laporan akhir
                            if total_downloaded > 0:
                                termux_notify("Story Selesai", f"{total_downloaded} Story @{username} berjaya disimpan.")
                                logger.info(t("tg_total_dl", n=total_downloaded))
                            else:
                                logger.warning(f"❌ Tiada media Story yang boleh dimuat turun untuk @{username}.")

                        except Exception as sub_e:
                            logger.error(f"Gagal mengambil maklumat story @{username}: {sub_e}")
                    else:
                        logger.info(t("tg_live_listen"))
                        logger.info("   " + t("tg_live_hint"))
                        stop_event = asyncio.Event()
                        poll_task = asyncio.create_task(_live_poll_saved_messages(stop_event))
                        try:
                            await asyncio.to_thread(
                                input,
                                t("tg_live_exit")
                            )
                        finally:
                            stop_event.set()
                            try:
                                await asyncio.wait_for(poll_task, timeout=5)
                            except Exception:
                                poll_task.cancel()

                finally:
                    telegram_live_active = False
                        
            elif pilihan == "4":
                show_settings_menu()
                continue  # skip the "Tekan Enter" at the bottom
                        
            elif pilihan == "5":
                console.print(f"\n[bold cyan]{t('goodbye')}[/bold cyan]")
                break

            if pilihan != "5":
                console.input(f"\n[dim]{t('press_enter')}[/dim]")

    except KeyboardInterrupt:
        console.print(f"\n[cyan]{t('stopped')}[/cyan]")
    except Exception as e:
        logger.error(f"Ralat sistem: {e}")
    finally:
        telegram_live_active = False
        if telegram_client_started:
            try:
                if getattr(app, "is_connected", False):
                    # Timeout — elak hang bila keluar
                    await asyncio.wait_for(app.stop(), timeout=2.0)
            except Exception:
                pass
            try:
                await asyncio.sleep(0.1)
            except Exception:
                pass
        try:
            from utils.logger import silence_logging
            silence_logging()
        except Exception:
            pass


if __name__ == "__main__":
    import subprocess
    import warnings
    import sys
    import logging

    warnings.filterwarnings("ignore", category=RuntimeWarning)
    warnings.filterwarnings("ignore", message=".*never awaited.*")
    warnings.filterwarnings("ignore", message=".*sys.meta_path.*")
    warnings.filterwarnings("ignore", message=".*socket.send.*")

    # Senyapkan spam "socket.send() raised exception"
    logging.getLogger("asyncio").setLevel(logging.CRITICAL)

    try:
        subprocess.run(
            ["ffmpeg", "-version"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    except FileNotFoundError:
        logger.error("FFMPEG tidak dijumpai di sistem anda! Muat turun video/audio mungkin terjejas.")

    try:
        asyncio.run(run_downloader())
    except (KeyboardInterrupt, SystemExit):
        pass
    except Exception:
        pass
    finally:
        try:
            from utils.logger import silence_logging
            silence_logging()
        except Exception:
            pass
        try:
            logging.shutdown()
        except Exception:
            pass
        # Force return ke shell — elak hang selepas "Terima kasih"
        try:
            import os
            os._exit(0)
        except Exception:
            pass