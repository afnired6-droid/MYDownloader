"""
Antaramuka Interaktif Konsol - Versi PRO Final (MS / EN).
"""
import shutil
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.prompt import Prompt, Confirm
from rich.text import Text
from rich import box

from utils.helpers import get_clipboard_url
from config.settings import Settings
from utils.history import HistoryManager
from utils.i18n import t, set_language, get_language

console = Console()

VERSION = "2.1.0 PRO"
AUTHOR = "afnirwd"


def _format_size(num_bytes: int) -> str:
    if not num_bytes:
        return "0 B"
    n = float(num_bytes)
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if n < 1024:
            return f"{n:.1f} {unit}"
        n /= 1024
    return f"{n:.1f} PB"


def _get_status_line() -> str:
    parts = []
    cookies = Settings.get_cookies_path()
    if cookies:
        parts.append(f"[green]🍪 {t('cookies_ok')}[/green]")
    else:
        parts.append(f"[dim]🍪 {t('cookies_no')}[/dim]")
    try:
        total, used, free = shutil.disk_usage(Settings.DOWNLOAD_DIR)
        parts.append(f"[cyan]💾 {t('disk_free', size=_format_size(free))}[/cyan]")
    except Exception:
        pass
    try:
        stats = HistoryManager.get_stats()
        parts.append(f"[magenta]📥 {t('history_files', n=stats['total_downloads'])}[/magenta]")
    except Exception:
        pass
    lang = get_language().upper()
    parts.append(f"[white]🌐 {lang}[/white]")
    return "  •  ".join(parts)


def display_header():
    console.clear()

    # —— Banner premium ——
    brand = Text()
    brand.append("  ◆  ", style="bold #FFD700")
    brand.append("MYDownloader", style="bold #00E5FF")
    brand.append("  ", style="")
    brand.append(f"v{VERSION}", style="bold #FFFFFF")
    brand.append("  ◆", style="bold #FFD700")

    subtitle = Text()
    subtitle.append("  ", style="")
    subtitle.append(t("app_title"), style="italic #A0AEC0")

    credit = Text()
    credit.append("  crafted by ", style="dim")
    credit.append(AUTHOR, style="bold #F687B3")
    credit.append("  ·  Universal Social Media Toolkit", style="dim")

    status = _get_status_line()

    body = Text.assemble(
        brand, "\n",
        subtitle, "\n",
        credit, "\n\n",
        Text.from_markup(f"  {status}"),
    )
    console.print(
        Panel(
            body,
            border_style="#6B46C1",
            box=box.DOUBLE_EDGE,
            padding=(1, 2),
            title="[bold #E9D8FD]✦ PREMIUM[/]",
            title_align="left",
        )
    )


def main_menu():
    display_header()

    clip_url = get_clipboard_url()
    if clip_url:
        console.print()
        console.print(Panel(
            f"[bold yellow]🔗 Clipboard[/bold yellow]\n[dim]{clip_url[:80]}{'...' if len(clip_url) > 80 else ''}[/dim]",
            border_style="yellow",
            box=box.ROUNDED,
        ))
        if Confirm.ask("[bold]Download?[/bold]", default=True):
            return "CLIPBOARD", clip_url

    console.print()

    menu = Table(
        show_header=False,
        box=None,
        padding=(0, 1),
        expand=False,
        pad_edge=False,
    )
    # No/Item/Desc — width sesuai skrin Termux (~40–50 col)
    menu.add_column("", style="bold #F6E05E", width=3, justify="right", no_wrap=True)
    menu.add_column("", style="bold #E2E8F0", no_wrap=False)
    menu.add_column("", style="#A0AEC0", no_wrap=False)

    menu.add_row("1", f"[bold #63B3ED]📥  {t('menu_1')}[/]", f"[#718096]{t('menu_1_desc')}[/]")
    menu.add_row("2", f"[bold #9F7AEA]🎞  {t('menu_2')}[/]", f"[#718096]{t('menu_2_desc')}[/]")
    menu.add_row("3", f"[bold #68D391]✈️  {t('menu_3')}[/]", f"[#718096]{t('menu_3_desc')}[/]")
    menu.add_row("4", f"[bold #F6AD55]⚙️  {t('menu_4')}[/]", f"[#718096]{t('menu_4_desc')}[/]")
    menu.add_row("5", f"[bold #FC8181]❌  {t('menu_5')}[/]", "")

    console.print(
        Panel(
            menu,
            title=f"[bold #B794F4]◈  {t('menu_title')}  ◈[/]",
            title_align="center",
            border_style="#805AD5",
            box=box.ROUNDED,
            padding=(0, 1),
        )
    )

    choice = Prompt.ask(
        f"\n[bold #9AE6B4]❯ {t('choose_menu')}[/]",
        choices=["1", "2", "3", "4", "5"],
        default="1",
    )
    return choice, None


def show_settings_menu():
    while True:
        display_header()
        console.print()
        stats = HistoryManager.get_stats()
        cookies_path = Settings.get_cookies_path()

        info = Table(show_header=False, box=None, padding=(0, 1))
        info.add_column(style="dim", width=18)
        info.add_column()
        info.add_row("📁 Download", Settings.DOWNLOAD_DIR)
        info.add_row("🍪 Cookies", cookies_path or t("cookies_no"))
        info.add_row("📥 History", str(stats.get("total_downloads", 0)))
        info.add_row("🌐 Language", "Bahasa Malaysia" if get_language() == "ms" else "English")
        console.print(Panel(info, title=f"[bold]{t('settings_title')}[/bold]", border_style="blue", box=box.ROUNDED))

        recent = HistoryManager.get_recent(8)
        if recent:
            recent_table = Table(show_header=True, box=box.SIMPLE, padding=(0, 1))
            recent_table.add_column("#", width=3)
            recent_table.add_column("Platform", width=12)
            recent_table.add_column("Title", width=36)
            for i, item in enumerate(recent, 1):
                title = (item.get("title") or "—")[:36]
                recent_table.add_row(str(i), item.get("platform", "—"), title)
            console.print(recent_table)

        console.print()
        console.print("  1. 🗑️  Clear history")
        console.print("  2. 🍪  Cookies status")
        console.print("  3. 🌐  Language / Bahasa")
        console.print("  4. ↩️  Back")

        choice = Prompt.ask("\n[bold green]→[/bold green]", choices=["1", "2", "3", "4"], default="4")

        if choice == "1":
            if stats["total_downloads"] == 0:
                console.print("[yellow]Empty.[/yellow]")
            elif Confirm.ask(f"[bold red]Delete {stats['total_downloads']} records?[/bold red]", default=False):
                deleted = HistoryManager.clear_history()
                console.print(f"[green]✅ {deleted} deleted.[/green]")
            console.input(f"\n[dim]{t('press_enter')}[/dim]")

        elif choice == "2":
            if cookies_path:
                console.print(Panel(f"[green]✅ {cookies_path}[/green]", border_style="green", box=box.ROUNDED))
            else:
                console.print(Panel(
                    "[yellow]cookies.txt not found[/yellow]\nPut Netscape cookies.txt in project folder.",
                    border_style="yellow",
                    box=box.ROUNDED,
                ))
            console.input(f"\n[dim]{t('press_enter')}[/dim]")

        elif choice == "3":
            console.print()
            console.print(f"[bold]{t('lang_choose')}[/bold]")
            console.print("  1. Bahasa Malaysia")
            console.print("  2. English")
            lang_choice = Prompt.ask("→", choices=["1", "2"], default="1" if get_language() == "ms" else "2")
            set_language("ms" if lang_choice == "1" else "en")
            console.print(f"[green]{t('lang_set')}[/green]")
            console.input(f"\n[dim]{t('press_enter')}[/dim]")

        else:
            break
