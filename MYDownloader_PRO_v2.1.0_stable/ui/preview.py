"""
Pratonton maklumat media menggunakan Rich Table.
"""
from rich.console import Console
from rich.table import Table
from rich.prompt import Confirm
from utils.logger import logger

console = Console()

def format_size(bytes_size) -> str:
    try:
        bytes_size = float(bytes_size or 0)
    except (TypeError, ValueError):
        return "Tidak diketahui"
    if bytes_size <= 0:
        return "Tidak diketahui"
    for unit in ["B", "KB", "MB", "GB"]:
        if bytes_size < 1024.0:
            return f"{bytes_size:.2f} {unit}"
        bytes_size /= 1024.0
    return f"{bytes_size:.2f} TB"

def show_preview(info_dict: dict) -> bool:
    """
    Papar table maklumat media dan tanya pengesahan pengguna.
    
    Args:
        info_dict (dict): Dictionary mengandungi title, uploader, duration, dll.
        
    Returns:
        bool: True jika pengguna tekan 'Y', False jika 'N'.
    """
    if not info_dict:
        logger.error("Tiada maklumat untuk dipaparkan.")
        return False
        
    table = Table(title="[bold cyan]Pratonton Media[/bold cyan]", show_header=False, border_style="cyan")
    table.add_column("Key", style="bold yellow")
    table.add_column("Value", style="white")

    # Format durasi dari saat ke MM:SS (IG kadang bagi float)
    duration_raw = info_dict.get("duration") or 0
    try:
        duration = int(float(duration_raw))
    except (TypeError, ValueError):
        duration = 0
    dur_str = f"{duration // 60}:{duration % 60:02d}" if duration else "Tidak diketahui"

    # Anggaran Saiz
    filesize = info_dict.get("filesize_approx") or info_dict.get("filesize") or 0
    try:
        filesize = int(float(filesize))
    except (TypeError, ValueError):
        filesize = 0

    table.add_row("📝 Tajuk", info_dict.get('title', 'Unknown'))
    table.add_row("👤 Uploader", info_dict.get('uploader', 'Unknown'))
    table.add_row("🌍 Platform", info_dict.get('extractor_key', 'Unknown'))
    table.add_row("⏱️ Durasi", dur_str)
    table.add_row("💾 Saiz Anggaran", format_size(filesize))
    
    console.print("\n")
    console.print(table)
    
    # Tanya pengesahan
    return Confirm.ask("[bold green]Teruskan muat turun?[/bold green]")
