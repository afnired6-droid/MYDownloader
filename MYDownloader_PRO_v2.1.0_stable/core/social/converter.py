"""
Penyukar media — output MAX mesra Android Gallery.
Canvas tetap 1080x1920, H.264 baseline, no B-frames, yuv420p, faststart.
"""
from __future__ import annotations

import os
import subprocess
from utils.logger import logger


def _ffprobe_duration(path: str) -> float:
    try:
        r = subprocess.run(
            [
                "ffprobe", "-v", "error",
                "-show_entries", "format=duration",
                "-of", "default=noprint_wrappers=1:nokey=1",
                path,
            ],
            capture_output=True,
            text=True,
            timeout=30,
        )
        return float((r.stdout or "").strip() or 0)
    except Exception:
        return 0.0


class MediaConverter:
    # Canvas tetap — elak player Android hitam bila resolusi berubah
    WIDTH = 1080
    HEIGHT = 1920

    @staticmethod
    def images_to_video(
        image_paths: list,
        audio_path: str | None,
        output_path: str,
        fps: int = 30,
        min_seconds_per_image: float = 3.0,
    ) -> bool:
        if not image_paths:
            return False

        try:
            os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
            image_paths = [p for p in image_paths if p and os.path.isfile(p)]
            if not image_paths:
                logger.error("Tiada fail gambar sah.")
                return False

            audio_dur = (
                _ffprobe_duration(audio_path)
                if audio_path and os.path.exists(audio_path)
                else 0.0
            )
            n = len(image_paths)

            if audio_dur > 0:
                slots = max(n, int(audio_dur / min_seconds_per_image + 0.999))
                sec_each = max(0.5, audio_dur / slots)
                sequence = [image_paths[i % n] for i in range(slots)]
                target_dur = audio_dur
            else:
                sec_each = min_seconds_per_image
                sequence = list(image_paths)
                target_dur = sec_each * len(sequence)

            logger.info(
                f"🎞️  Encode slide: {n} gambar → {len(sequence)} slot × {sec_each:.2f}s "
                f"({MediaConverter.WIDTH}x{MediaConverter.HEIGHT})"
            )

            w, h = MediaConverter.WIDTH, MediaConverter.HEIGHT
            # Fit dalam canvas + pad hitam tipis tepi jika ratio berbeza
            scale_pad = (
                f"scale={w}:{h}:force_original_aspect_ratio=decrease,"
                f"pad={w}:{h}:(ow-iw)/2:(oh-ih)/2:black,"
                f"setsar=1,fps={fps},format=yuv420p"
            )

            cmd = ["ffmpeg", "-y", "-hide_banner", "-loglevel", "error"]
            for img in sequence:
                cmd.extend(["-loop", "1", "-t", f"{sec_each:.4f}", "-i", img])

            has_audio = bool(audio_path and os.path.exists(audio_path))
            if has_audio:
                cmd.extend(["-i", audio_path])

            n_in = len(sequence)
            parts = []
            for i in range(n_in):
                parts.append(f"[{i}:v]{scale_pad}[v{i}]")
            concat_in = "".join(f"[v{i}]" for i in range(n_in))
            parts.append(f"{concat_in}concat=n={n_in}:v=1:a=0[vout]")
            filter_complex = ";".join(parts)

            cmd.extend(["-filter_complex", filter_complex, "-map", "[vout]"])

            if has_audio:
                cmd.extend([
                    "-map", f"{n_in}:a:0?",
                    "-c:a", "aac",
                    "-b:a", "128k",
                    "-ar", "44100",
                    "-ac", "2",
                    "-shortest",
                ])
            else:
                cmd.extend(["-t", f"{target_dur:.3f}"])

            # Paling mesra Android/iOS stock player
            cmd.extend([
                "-c:v", "libx264",
                "-profile:v", "baseline",
                "-level", "3.0",
                "-preset", "veryfast",
                "-tune", "stillimage",
                "-pix_fmt", "yuv420p",
                "-bf", "0",
                "-refs", "1",
                "-g", str(fps * 2),
                "-movflags", "+faststart",
                "-brand", "mp42",
                "-threads", "0",
                output_path,
            ])

            result = subprocess.run(cmd, capture_output=True, text=True, timeout=900)
            if result.returncode != 0:
                err = (result.stderr or result.stdout or "")[-1200:]
                logger.error(f"FFmpeg gagal: {err}")
                return False

            if not os.path.exists(output_path) or os.path.getsize(output_path) < 2000:
                logger.error("Output video kosong.")
                return False

            # Verify ada video stream
            probe = subprocess.run(
                [
                    "ffprobe", "-v", "error", "-select_streams", "v:0",
                    "-show_entries", "stream=codec_name,width,height",
                    "-of", "csv=p=0", output_path,
                ],
                capture_output=True, text=True, timeout=20,
            )
            logger.info(
                f"✅ Slide OK: {output_path} | "
                f"{_ffprobe_duration(output_path):.1f}s | stream={(probe.stdout or '').strip()}"
            )
            return True
        except Exception as e:
            logger.error(f"Gagal menukar gambar ke video: {e}")
            return False
