# MYDownloader PRO

**Universal Social Media & Telegram Downloader**  
Versi **2.1.0 PRO · Stable** · crafted by **afnirwd**

CLI + Web UI + PWA untuk muat turun media dari YouTube, Instagram, Facebook, X (Twitter), TikTok, Reddit, Threads dan Telegram.

---

## Ciri-ciri

| Feature | Keterangan |
|---------|------------|
| Multi-platform | YouTube, Instagram, Facebook, X, TikTok, Reddit, Threads |
| Live quality | Pilih resolusi / HD / watermark **sebelum** download |
| TikTok Slide | Gambar + audio → MP4 (H.264 baseline, mesra Android) |
| Instagram Story | gallery-dl + cookies Netscape (`#HttpOnly_` disokong) |
| Telegram | Story (active/pinned) + Live Saved Messages |
| Cookies | Platform-aware (IG cookies tidak dipakai untuk TikTok, dll.) |
| Smart folder | `downloads/TikTok/Videos`, `Instagram/Stories`, … |
| CLI premium | Menu MS/EN, status disk, history |
| Web UI | Glassmorphism, progress live, set folder |
| PWA | Install ke Home Screen (standalone) |

---

## Keperluan

- **Python 3.10+**
- **FFmpeg** (wajib untuk slide & merge)
- (Pilihan) **aria2** — speed boost download
- (Pilihan) **gallery-dl** — fallback Story IG / gambar

### Termux (Android)

```bash
pkg update && pkg upgrade -y
pkg install python git ffmpeg aria2 -y
pip install -U pip
```

---

## Pemasangan

```bash
# ekstrak zip, kemudian:
cd MYDownloader_PRO_stable

pip install -r requirements.txt
pip install gallery-dl          # disyorkan

cp .env.example .env
# edit .env jika guna Telegram (API_ID / API_HASH)
```

**Telegram API** (Menu 3 sahaja):  
https://my.telegram.org → API development tools → `api_id` + `api_hash` → `.env`

---

## Penggunaan

### CLI

```bash
python main.py
```

1. Muat turun link (YT · IG · FB · X · TikTok · …)  
2. TikTok Slide → Video / gambar / audio  
3. Telegram  
4. Tetapan & statistik (bahasa MS/EN, cookies, history)  
5. Keluar  

### Web UI + PWA

```bash
python webui.py
```

- Local: http://127.0.0.1:8080  
- LAN: http://\<IP-telefon-atau-PC\>:8080  

**Install PWA:** Chrome ⋮ → Install app / Add to Home screen  
iPhone Safari → Share → Add to Home Screen  

> Server (`webui.py`) mesti hidup untuk download. PWA hanya shell UI bila offline.

---

## Cookies (Instagram Story / private)

1. Extension: **Get cookies.txt LOCALLY** (Chrome) / **cookies.txt** (Firefox)  
2. Log masuk Instagram di browser  
3. Export **Netscape** → simpan sebagai `cookies.txt`  
4. Letak di folder project (sama level `main.py`)  

Pastikan `sessionid` ada (baris `#HttpOnly_` **disokong**).  
Cookies **tidak** dihantar ke TikTok/YouTube secara silang — ditapis ikut platform.

---

## Struktur folder download

```
downloads/
├── TikTok/
│   ├── Videos/
│   ├── Slides/
│   └── Images/
├── Instagram/
│   ├── Stories/
│   └── …
├── YouTube/
├── Facebook/
├── Twitter/
├── Reddit/
└── Telegram/
```

---

## Fail penting

```
MYDownloader_PRO_stable/
├── main.py              # CLI
├── webui.py             # Web UI entry
├── requirements.txt
├── .env.example
├── cookies.txt          # anda cipta sendiri (jangan share)
├── config/settings.py
├── core/
│   ├── downloader.py
│   ├── telegram.py
│   └── social/
│       ├── tiktok.py
│       └── converter.py
├── ui/menu.py
├── utils/
└── web/
    ├── app.py
    ├── templates/index.html
    └── static/          # PWA icons + SW
```

---

## Nota keselamatan & etika

- Untuk **kegunaan peribadi** sahaja  
- Hormati hak cipta & ToS platform  
- **Jangan** commit / share: `.env`, `cookies.txt`, `*.session`  
- Tool ini **bukan** untuk pengedaran komersial kandungan orang lain  

---

## Troubleshooting ringkas

| Masalah | Cadangan |
|---------|----------|
| IG Story unreachable | Cookies lengkap + story masih aktif (~24j) |
| TikTok slide hitam | Guna converter terkini; padam fail lama, download semula |
| YouTube bot check | Cookies YouTube / kemas kini yt-dlp |
| Web “No valid URL” | Restart `webui.py`, hard refresh browser |
| PWA tak keluar Install | Buka melalui HTTP host yang betul; Chrome Android |

```bash
pip install -U yt-dlp gallery-dl
```

---

## Kredit

**MYDownloader PRO v2.1.0 Stable**  
crafted by **afnirwd**

CLI · Web UI · PWA — satu core, dua muka.
