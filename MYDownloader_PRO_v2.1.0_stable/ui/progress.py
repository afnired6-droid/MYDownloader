"""
Pengurus Progress Bar berpusat untuk yt-dlp dan Pyrogram.
"""
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, DownloadColumn, TransferSpeedColumn, TimeRemainingColumn
from utils.logger import logger

class ProgressManager:
    def __init__(self):
        # Setup UI Progress Bar
        self.progress = Progress(
            SpinnerColumn(),
            TextColumn("[bold blue]{task.description}"),
            BarColumn(bar_width=40),
            "[progress.percentage]{task.percentage:>3.1f}%",
            "•",
            DownloadColumn(),
            "•",
            TransferSpeedColumn(),
            "•",
            TimeRemainingColumn(),
        )
        self.task_id = None

    def ytdlp_hook(self, d):
        """Hook khusus untuk dipasangkan pada yt-dlp."""
        if d['status'] == 'downloading':
            if self.task_id is None:
                self.progress.start()
                title = d.get('info_dict', {}).get('title', 'Memuat turun...')
                # Pendekkan tajuk jika terlalu panjang
                short_title = title[:20] + "..." if len(title) > 20 else title
                
                total = d.get('total_bytes') or d.get('total_bytes_estimate', 0)
                self.task_id = self.progress.add_task(f"📥 {short_title}", total=total)
            
            downloaded = d.get('downloaded_bytes', 0)
            self.progress.update(self.task_id, completed=downloaded)
            
        elif d['status'] == 'finished':
            if self.task_id is not None:
                self.progress.update(self.task_id, completed=d.get('total_bytes', 100))
                self.progress.stop()
                self.task_id = None
                logger.info("Muat turun media selesai, memproses fail...")

    async def pyrogram_progress(self, current, total, file_name="Media"):
        """Callback khusus untuk Pyrogram (Telegram download)."""
        if self.task_id is None:
            self.progress.start()
            self.task_id = self.progress.add_task(f"📨 Telegram: {file_name[:15]}...", total=total)
            
        self.progress.update(self.task_id, completed=current)
        
        if current >= total:
            self.progress.stop()
            self.task_id = None
