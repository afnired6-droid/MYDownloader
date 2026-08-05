"""
Sokongan dwibahasa: Bahasa Malaysia (ms) & English (en).
"""
from pathlib import Path

_LANG_FILE = Path("config/language.txt")
_current = "ms"

TEXTS = {
    "ms": {'app_title': 'Universal Social Media & Telegram Downloader', 'menu_title': 'Menu Utama', 'menu_1': 'Muat Turun Link', 'menu_1_desc': 'YT · IG · FB · X · TikTok', 'menu_2': 'TikTok Slide → Video', 'menu_2_desc': 'Gambar + Audio → MP4', 'menu_3': 'Telegram', 'menu_3_desc': 'Story + Saved Messages Live', 'menu_4': 'Tetapan & Statistik', 'menu_4_desc': 'History · Cookies · Disk · Bahasa', 'menu_5': 'Keluar', 'choose_menu': 'Pilih menu', 'press_enter': 'Tekan Enter untuk kembali ke menu utama...', 'goodbye': '👋 Terima kasih menggunakan MYDownloader PRO!', 'stopped': 'Berhenti dengan selamat...', 'enter_url': 'Masukkan URL (Sokong batch, Video & Story IG/FB/TikTok)', 'url_empty': 'URL tidak boleh kosong.', 'processing': 'Memproses {n} pautan untuk dimuat turun...', 'tt_slide_url': 'Masukkan URL TikTok Slide', 'tt_empty': 'URL TikTok tidak boleh kosong.', 'tg_tip': 'Kosongkan input & tekan Enter untuk Mod Live, ATAU taip @username untuk Story.', 'tg_prompt': 'Taip Username (atau tekan Enter untuk mode Live)', 'tg_live_listen': '📡 Mod Live Saved Messages sedang mendengar...', 'tg_live_hint': 'Forward media ke Saved Messages untuk auto-download.', 'tg_live_exit': 'Tekan Enter untuk keluar dari mod Live... ', 'tg_ready': '✅ Telegram client bersedia!', 'tg_connecting': 'Menyambung ke Telegram melalui Hydrogram...', 'lang_set': 'Bahasa ditukar ke Bahasa Malaysia.', 'lang_choose': 'Pilih bahasa / Choose language', 'settings_title': 'Tetapan & Statistik', 'cookies_ok': 'Cookies OK', 'cookies_no': 'Tiada Cookies', 'disk_free': '{size} bebas', 'history_files': '{n} fail', 'no_clipboard': 'Tiada URL sah dalam clipboard.', 'batch_done': '✅ Semua proses batch selesai!', 'tg_menu3': '📡 [TELEGRAM] Mod Menu 3 diaktifkan.', 'tg_tip1': '💡 Tip: Kosongkan input & tekan Enter untuk Mod Live,', 'tg_tip2': '   ATAU taip @username untuk muat turun Story Telegram.', 'tg_story_type': 'Jenis Story:', 'tg_story_1': '1. Active Stories (sedang hidup ~24 jam)', 'tg_story_2': '2. Pinned Stories (yang di-pin di profil)', 'tg_story_3': '3. Kedua-duanya (Active + Pinned)', 'tg_story_choose': 'Pilih', 'tg_fetch_active': '🔍 Mengambil Active Stories untuk @{user}...', 'tg_fetch_pinned': '📌 Mengambil Pinned Stories untuk @{user}...', 'tg_no_active': '❌ Tiada Active Story dijumpai untuk @{user}.', 'tg_no_pinned': '❌ Tiada Pinned Story dijumpai untuk @{user}.', 'tg_total_dl': '✅ Jumlah berjaya dimuat turun: {n}', 'tg_poller_start': '🔄 Poller Saved Messages dimulakan (setiap 2s)...', 'tg_poller_stop': '🔄 Poller dihentikan.', 'tg_live_detect': '📥 [LIVE] Media dikesan ({kind}){name} — memuat turun...', 'tg_live_done': '✔️ [LIVE] Selesai: {path}', 'enter_tt': 'Masukkan URL TikTok Slide', 'processing_n': '🔍 Memproses {n} pautan untuk dimuat turun...', 'clip_process': 'Memproses link dari clipboard...', 'tt_mode_choose': 'Sila pilih mod muat turun'},
    "en": {'app_title': 'Universal Social Media & Telegram Downloader', 'menu_title': 'Main Menu', 'menu_1': 'Download Link', 'menu_1_desc': 'YT · IG · FB · X · TikTok', 'menu_2': 'TikTok Slide → Video', 'menu_2_desc': 'Images + Audio → MP4', 'menu_3': 'Telegram', 'menu_3_desc': 'Story + Saved Messages Live', 'menu_4': 'Settings & Stats', 'menu_4_desc': 'History · Cookies · Disk · Language', 'menu_5': 'Exit', 'choose_menu': 'Choose menu', 'press_enter': 'Press Enter to return to main menu...', 'goodbye': '👋 Thank you for using MYDownloader PRO!', 'stopped': 'Stopped safely...', 'enter_url': 'Enter URL (batch supported, Video & Story IG/FB/TikTok)', 'url_empty': 'URL cannot be empty.', 'processing': 'Processing {n} link(s) for download...', 'tt_slide_url': 'Enter TikTok Slide URL', 'tt_empty': 'TikTok URL cannot be empty.', 'tg_tip': 'Leave empty & press Enter for Live mode, OR type @username for Story.', 'tg_prompt': 'Type Username (or press Enter for Live mode)', 'tg_live_listen': '📡 Live Saved Messages mode listening...', 'tg_live_hint': 'Forward media to Saved Messages for auto-download.', 'tg_live_exit': 'Press Enter to exit Live mode... ', 'tg_ready': '✅ Telegram client ready!', 'tg_connecting': 'Connecting to Telegram via Hydrogram...', 'lang_set': 'Language switched to English.', 'lang_choose': 'Pilih bahasa / Choose language', 'settings_title': 'Settings & Stats', 'cookies_ok': 'Cookies OK', 'cookies_no': 'No Cookies', 'disk_free': '{size} free', 'history_files': '{n} files', 'no_clipboard': 'No valid URL in clipboard.', 'batch_done': '✅ All batch processes finished!', 'tg_menu3': '📡 [TELEGRAM] Menu 3 mode activated.', 'tg_tip1': '💡 Tip: Leave empty & press Enter for Live mode,', 'tg_tip2': '   OR type @username to download Telegram Stories.', 'tg_story_type': 'Story type:', 'tg_story_1': '1. Active Stories (live ~24 hours)', 'tg_story_2': '2. Pinned Stories (pinned on profile)', 'tg_story_3': '3. Both (Active + Pinned)', 'tg_story_choose': 'Choose', 'tg_fetch_active': '🔍 Fetching Active Stories for @{user}...', 'tg_fetch_pinned': '📌 Fetching Pinned Stories for @{user}...', 'tg_no_active': '❌ No Active Story found for @{user}.', 'tg_no_pinned': '❌ No Pinned Story found for @{user}.', 'tg_total_dl': '✅ Total downloaded successfully: {n}', 'tg_poller_start': '🔄 Saved Messages poller started (every 2s)...', 'tg_poller_stop': '🔄 Poller stopped.', 'tg_live_detect': '📥 [LIVE] Media detected ({kind}){name} — downloading...', 'tg_live_done': '✔️ [LIVE] Done: {path}', 'enter_tt': 'Enter TikTok Slide URL', 'processing_n': '🔍 Processing {n} link(s) for download...', 'clip_process': 'Processing clipboard link...', 'tt_mode_choose': 'Choose download mode'},
}


def load_language() -> str:
    global _current
    try:
        if _LANG_FILE.is_file():
            val = _LANG_FILE.read_text(encoding="utf-8").strip().lower()
            if val in ("ms", "en"):
                _current = val
    except Exception:
        pass
    return _current


def set_language(lang: str) -> str:
    global _current
    lang = (lang or "ms").lower()
    if lang not in ("ms", "en"):
        lang = "ms"
    _current = lang
    try:
        _LANG_FILE.parent.mkdir(parents=True, exist_ok=True)
        _LANG_FILE.write_text(lang, encoding="utf-8")
    except Exception:
        pass
    return _current


def get_language() -> str:
    return _current


def t(key: str, **kwargs) -> str:
    """Ambil teks mengikut bahasa semasa."""
    table = TEXTS.get(_current) or TEXTS["ms"]
    text = table.get(key) or TEXTS["ms"].get(key) or key
    if kwargs:
        try:
            return text.format(**kwargs)
        except Exception:
            return text
    return text


load_language()
