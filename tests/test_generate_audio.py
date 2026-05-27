# tests/test_generate_audio.py
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

from steps.generate_audio import generate_audio

_SCRIPT = {
    "topic": "test",
    "rounds": [
        {
            "round": 1,
            "illustration_prompt": "scene",
            "lines": [
                {"speaker": "A", "text": "Hey, quick update?"},
                {"speaker": "B", "text": "On it... mostly."},
            ],
        }
    ],
}


def test_generate_audio_creates_one_mp3_per_line():
    with tempfile.TemporaryDirectory() as tmpdir:
        output_dir = Path(tmpdir)

        with patch("steps.generate_audio.edge_tts.Communicate") as mock_communicate:
            async def fake_save(path):
                Path(path).write_bytes(b"ID3" + b"\x00" * 100)

            mock_instance = MagicMock()
            mock_instance.save = fake_save
            mock_communicate.return_value = mock_instance

            paths = generate_audio(_SCRIPT, output_dir)

        assert len(paths) == 2
        assert mock_communicate.call_count == 2
        for path in paths:
            assert path.exists()


def test_generate_audio_uses_correct_voices():
    with tempfile.TemporaryDirectory() as tmpdir:
        output_dir = Path(tmpdir)

        with patch("steps.generate_audio.edge_tts.Communicate") as mock_communicate, \
             patch("steps.generate_audio.config") as mock_config:

            mock_config.VOICE_A = "en-US-JennyNeural"
            mock_config.VOICE_B = "en-US-GuyNeural"

            async def fake_save(path):
                Path(path).write_bytes(b"audio")

            mock_instance = MagicMock()
            mock_instance.save = fake_save
            mock_communicate.return_value = mock_instance

            generate_audio(_SCRIPT, output_dir)

        calls = mock_communicate.call_args_list
        # edge_tts.Communicate(text, voice) — second positional arg is the voice
        assert calls[0].args[1] == "en-US-JennyNeural"   # Speaker A
        assert calls[1].args[1] == "en-US-GuyNeural"     # Speaker B


def test_generate_audio_skips_existing_files():
    with tempfile.TemporaryDirectory() as tmpdir:
        output_dir = Path(tmpdir)
        (output_dir / "line_1_1.mp3").write_bytes(b"audio")
        (output_dir / "line_1_2.mp3").write_bytes(b"audio")

        with patch("steps.generate_audio.edge_tts.Communicate") as mock_communicate:
            generate_audio(_SCRIPT, output_dir)
            mock_communicate.assert_not_called()
