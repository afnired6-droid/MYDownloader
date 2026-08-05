"""
Sistem Logging menggunakan Rich untuk paparan console yang profesional.
"""
import logging
from rich.logging import RichHandler

FORMAT = "%(message)s"
_rich_handler = RichHandler(rich_tracebacks=True)

logging.basicConfig(
    level="INFO",
    format=FORMAT,
    datefmt="[%X]",
    handlers=[_rich_handler],
)

logger = logging.getLogger("rich")

# Senyapkan logger bising dari library
for noisy in ("hydrogram", "pyrogram", "aiohttp", "asyncio", "asyncio.selector_events"):
    logging.getLogger(noisy).setLevel(logging.CRITICAL)

# Senyapkan amaran socket.send() yang bising tapi tak berbahaya
logging.getLogger("asyncio").setLevel(logging.CRITICAL)


def set_debug_mode(enabled: bool):
    """Tukar tahap logging antara INFO dan DEBUG."""
    logger.setLevel(logging.DEBUG if enabled else logging.INFO)


def silence_logging():
    """Tanggalkan handler Rich sebelum shutdown — elak ImportError sys.meta_path."""
    root = logging.getLogger()
    for h in list(root.handlers):
        try:
            h.close()
        except Exception:
            pass
        try:
            root.removeHandler(h)
        except Exception:
            pass
    # Ganti dengan NullHandler supaya emit tak crash
    root.addHandler(logging.NullHandler())
    logging.getLogger("rich").handlers.clear()
    logging.getLogger("rich").addHandler(logging.NullHandler())
