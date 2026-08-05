from hydrogram import Client
from config.settings import Settings

# workers & max_concurrent_transmissions percepatkan transfer fail
_kwargs = dict(
    name="downloader_session",
    api_id=Settings.API_ID,
    api_hash=Settings.API_HASH,
    workdir="config",
    workers=8,
)

# Hydrogram/Pyrogram: concurrent file transfers (jika parameter wujud)
try:
    import inspect
    sig = inspect.signature(Client.__init__)
    if "max_concurrent_transmissions" in sig.parameters:
        _kwargs["max_concurrent_transmissions"] = 6
except Exception:
    pass

app = Client(**_kwargs)
