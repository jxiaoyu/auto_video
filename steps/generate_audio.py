# steps/generate_audio.py
import asyncio
from pathlib import Path

import edge_tts

import config


async def _synthesize(text: str, voice: str, output_path: Path) -> None:
    """Async helper: synthesize one line and save to output_path.

    Retries up to 3 times with exponential backoff to handle transient
    503 errors from the Edge TTS service.
    """
    last_exc: Exception | None = None
    for attempt in range(3):
        try:
            communicate = edge_tts.Communicate(text, voice)
            await communicate.save(str(output_path))
            return
        except Exception as exc:
            last_exc = exc
            wait = 2 ** attempt  # 1 s, 2 s, 4 s
            print(f"  [warn] TTS attempt {attempt + 1} failed ({exc}), retrying in {wait}s...")
            await asyncio.sleep(wait)
    raise last_exc


def _voice_for_speaker(speaker_key: str, characters: dict) -> str:
    """Return the correct Edge TTS voice for a speaker based on their gender.

    Falls back to VOICE_FEMALE if gender is missing or unrecognised.
    """
    char = characters.get(speaker_key, {})
    gender = (char.get("gender", "") if isinstance(char, dict) else "").lower()
    return config.VOICE_MALE if gender == "male" else config.VOICE_FEMALE


def generate_audio(script: dict, output_dir: Path) -> list[Path]:
    """Synthesize TTS audio for every dialogue line via Edge TTS.

    Voice is chosen by the character's gender field, not their A/B label,
    so male characters always get the male voice and vice-versa.
    Skips lines whose MP3 already exists.
    Returns list of paths in script order: [line_1_1.mp3, line_1_2.mp3, ...]
    """
    audio_paths: list[Path] = []
    characters = script.get("characters", {})

    for round_data in script["rounds"]:
        round_num = round_data["round"]
        for line_idx, line in enumerate(round_data["lines"], start=1):
            audio_path = output_dir / f"line_{round_num}_{line_idx}.mp3"

            if audio_path.exists():
                print(f"  [skip] line_{round_num}_{line_idx}.mp3 already exists")
                audio_paths.append(audio_path)
                continue

            voice = _voice_for_speaker(line["speaker"], characters)

            try:
                asyncio.run(_synthesize(line["text"], voice, audio_path))
            except Exception:
                audio_path.unlink(missing_ok=True)
                raise

            # Brief pause between requests to avoid triggering rate limits
            asyncio.run(asyncio.sleep(0.5))

            print(
                f"  [done] line_{round_num}_{line_idx}.mp3"
                f" ({line['speaker']}: {line['text'][:50]})"
            )
            audio_paths.append(audio_path)

    return audio_paths
