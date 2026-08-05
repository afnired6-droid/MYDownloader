"""
Pembalut (Wrapper) yt-dlp untuk YouTube, IG, FB, X(Twitter).
"""
import yt_dlp
from config.settings import Settings
from utils.logger import logger

class YTDLHandler:
    @staticmethod
    def download(url: str, audio_only: bool = False):
        """Muat turun menggunakan yt-dlp dengan tetapan terbaik."""
        ydl_opts = {
            'outtmpl': f'{Settings.DOWNLOAD_DIR}/%(extractor)s_%(uploader)s_%(title)s.%(ext)s',
            'quiet': True,
            'no_warnings': True,
        }

        if audio_only:
            ydl_opts.update({
                'format': 'bestaudio/best',
                'postprocessors': [{
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': 'mp3',
                    'preferredquality': '192',
                }],
            })
        else:
            ydl_opts.update({
                'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
            })

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                logger.info(f"Memuat turun dari {url}...")
                ydl.download([url])
                logger.info("Muat turun selesai!")
        except Exception as e:
            logger.error(f"Ralat yt-dlp: {e}")
