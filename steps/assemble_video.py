# steps/assemble_video.py
import subprocess
import textwrap
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

import config


# ── Font helpers ─────────────────────────────────────────────────────────────

def _get_font(size: int):
    """Return a TrueType font at `size`, falling back to Pillow's default.

    Preference order: rounded/bold fonts first for a cartoon-style look.
    """
    candidates = [
        "/System/Library/Fonts/Supplemental/Arial Rounded Bold.ttf",  # macOS
        "/System/Library/Fonts/SFNSRounded.ttf",                      # macOS (SF Rounded)
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",       # Linux
        "/System/Library/Fonts/Helvetica.ttc",                        # macOS fallback
        "C:/Windows/Fonts/arial.ttf",                                  # Windows
    ]
    for path in candidates:
        try:
            return ImageFont.truetype(path, size)
        except OSError:
            continue
    return ImageFont.load_default()


# ── Subtitle rendering ────────────────────────────────────────────────────────

def _render_subtitle(image_path: Path, text: str, dest_path: Path) -> None:
    """Overlay subtitle text on the bottom of an image and save to dest_path."""
    img = Image.open(image_path).convert("RGB")
    img = img.resize((config.VIDEO_WIDTH, config.VIDEO_HEIGHT), Image.LANCZOS)

    font = _get_font(52)
    wrapped = textwrap.fill(text, width=30)

    # Measure wrapped text
    tmp_draw = ImageDraw.Draw(img)
    bbox = tmp_draw.multiline_textbbox((0, 0), wrapped, font=font, align="center")
    text_w = bbox[2] - bbox[0]
    text_h = bbox[3] - bbox[1]

    x = (config.VIDEO_WIDTH - text_w) // 2
    y = config.VIDEO_HEIGHT - text_h - 80

    # Semi-transparent dark box behind text
    padding = 14
    overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
    overlay_draw = ImageDraw.Draw(overlay)
    overlay_draw.rectangle(
        [x - padding, y - padding, x + text_w + padding, y + text_h + padding],
        fill=(0, 0, 0, 160),
    )
    img = Image.alpha_composite(img.convert("RGBA"), overlay).convert("RGB")

    # Black outline, then white text
    draw = ImageDraw.Draw(img)
    for dx, dy in [(-3, -3), (3, -3), (-3, 3), (3, 3), (-3, 0), (3, 0), (0, -3), (0, 3)]:
        draw.multiline_text((x + dx, y + dy), wrapped, font=font, fill="black", align="center")
    draw.multiline_text((x, y), wrapped, font=font, fill="white", align="center")

    img.save(str(dest_path))


# ── Audio helpers ─────────────────────────────────────────────────────────────

def _get_audio_duration(audio_path: Path) -> float:
    """Return the duration in seconds of an MP3 file via ffprobe."""
    result = subprocess.run(
        [
            "ffprobe", "-v", "error",
            "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1",
            str(audio_path),
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    return float(result.stdout.strip())


# ── Video assembly ────────────────────────────────────────────────────────────

def assemble_video(script: dict, output_dir: Path) -> Path:
    """Combine images, audio, and subtitle text into a final MP4.

    Skips entirely if final.mp4 already exists.
    Returns path to final.mp4.
    """
    final_path = output_dir / "final.mp4"
    if final_path.exists():
        print("  [skip] final.mp4 already exists")
        return final_path

    segments_dir = output_dir / "segments"
    segments_dir.mkdir(exist_ok=True)

    segment_paths: list[Path] = []

    for round_data in script["rounds"]:
        round_num = round_data["round"]
        round_image = output_dir / f"round_{round_num}.png"

        for line_idx, line in enumerate(round_data["lines"], start=1):
            audio_path = output_dir / f"line_{round_num}_{line_idx}.mp3"
            segment_path = segments_dir / f"seg_{round_num}_{line_idx}.mp4"

            # Bake subtitle into a temporary frame image
            frame_path = segments_dir / f"frame_{round_num}_{line_idx}.png"
            _render_subtitle(round_image, line["text"], frame_path)

            duration = _get_audio_duration(audio_path)

            subprocess.run(
                [
                    "ffmpeg", "-y",
                    "-loop", "1",
                    "-i", str(frame_path),
                    "-i", str(audio_path),
                    "-c:v", "libx264",
                    "-tune", "stillimage",
                    "-c:a", "aac",
                    "-b:a", "192k",
                    "-pix_fmt", "yuv420p",
                    "-t", str(duration),
                    str(segment_path),
                ],
                check=True,
                capture_output=True,
            )
            print(f"  [done] segment {round_num}_{line_idx}")
            segment_paths.append(segment_path)

    # Write concat list
    concat_path = segments_dir / "concat.txt"
    concat_path.write_text(
        "\n".join(f"file '{p.name}'" for p in segment_paths)
    )

    subprocess.run(
        [
            "ffmpeg", "-y",
            "-f", "concat",
            "-safe", "0",
            "-i", str(concat_path),
            "-c", "copy",
            str(final_path),
        ],
        check=True,
        capture_output=True,
    )
    print("  [done] final.mp4")
    return final_path
