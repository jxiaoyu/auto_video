# steps/generate_audio.py
from pathlib import Path

from google.cloud import texttospeech

import config


def generate_audio(script: dict, output_dir: Path) -> list[Path]:
    """Synthesize TTS audio for every dialogue line.

    Speaker A → config.VOICE_A, Speaker B → config.VOICE_B.
    Skips lines whose MP3 already exists.
    Returns list of paths in script order: [line_1_1.mp3, line_1_2.mp3, line_2_1.mp3, ...]
    """
    client = texttospeech.TextToSpeechClient()
    audio_paths: list[Path] = []

    for round_data in script["rounds"]:
        round_num = round_data["round"]
        for line_idx, line in enumerate(round_data["lines"], start=1):
            audio_path = output_dir / f"line_{round_num}_{line_idx}.mp3"

            if audio_path.exists():
                print(f"  [skip] line_{round_num}_{line_idx}.mp3 already exists")
                audio_paths.append(audio_path)
                continue

            voice_name = config.VOICE_A if line["speaker"] == "A" else config.VOICE_B

            response = client.synthesize_speech(
                input=texttospeech.SynthesisInput(text=line["text"]),
                voice=texttospeech.VoiceSelectionParams(
                    language_code=config.LANGUAGE_CODE,
                    name=voice_name,
                ),
                audio_config=texttospeech.AudioConfig(
                    audio_encoding=texttospeech.AudioEncoding.MP3,
                ),
            )

            try:
                audio_path.write_bytes(response.audio_content)
            except Exception:
                audio_path.unlink(missing_ok=True)
                raise
            print(
                f"  [done] line_{round_num}_{line_idx}.mp3"
                f" ({line['speaker']}: {line['text'][:50]})"
            )
            audio_paths.append(audio_path)

    return audio_paths
