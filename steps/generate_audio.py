# steps/generate_audio.py
import asyncio
from pathlib import Path

import edge_tts

import config


async def _synthesize(text: str, voice: str, output_path: Path) -> None:
    """Async helper: synthesize one line and save to output_path."""
    communicate = edge_tts.Communicate(text, voice)
    await communicate.save(str(output_path))


def generate_audio(script: dict, output_dir: Path) -> list[Path]:
    """Synthesize TTS audio for every dialogue line via Edge TTS.

    Speaker A → config.VOICE_A, Speaker B → config.VOICE_B.
    Skips lines whose MP3 already exists.
    Returns list of paths in script order: [line_1_1.mp3, line_1_2.mp3, ...]
    """
    audio_paths: list[Path] = []

    for round_data in script["rounds"]:
        round_num = round_data["round"]
        for line_idx, line in enumerate(round_data["lines"], start=1):
            audio_path = output_dir / f"line_{round_num}_{line_idx}.mp3"

            if audio_path.exists():
                print(f"  [skip] line_{round_num}_{line_idx}.mp3 already exists")
                audio_paths.append(audio_path)
                continue

            voice = config.VOICE_A if line["speaker"] == "A" else config.VOICE_B

            try:
                asyncio.run(_synthesize(line["text"], voice, audio_path))
            except Exception:
                audio_path.unlink(missing_ok=True)
                raise

            print(
                f"  [done] line_{round_num}_{line_idx}.mp3"
                f" ({line['speaker']}: {line['text'][:50]})"
            )
            audio_paths.append(audio_path)

    return audio_paths
