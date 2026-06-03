# tests/test_generate_audio.py
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

from steps.generate_audio import generate_audio

# Female A, Male B
_SCRIPT = {
    "topic": "test",
    "characters": {
        "A": {"name": "Emily", "gender": "female", "appearance": "..."},
        "B": {"name": "Kevin", "gender": "male",   "appearance": "..."},
    },
    "rounds": [
        {
            "round": 1,
            "illustration_prompt": "scene",
            "lines": [
                {"speaker": "A", "text": "Hey, quick update?", "translation": "嘿，有进展吗？"},
                {"speaker": "B", "text": "On it... mostly.",   "translation": "在做了... 差不多。"},
            ],
        }
    ],
}

# Male A, Female B — voices must flip accordingly
_SCRIPT_REVERSED_GENDERS = {
    "topic": "test",
    "characters": {
        "A": {"name": "Kevin", "gender": "male",   "appearance": "..."},
        "B": {"name": "Emily", "gender": "female", "appearance": "..."},
    },
    "rounds": [
        {
            "round": 1,
            "illustration_prompt": "scene",
            "lines": [
                {"speaker": "A", "text": "Hey, quick update?", "translation": "..."},
                {"speaker": "B", "text": "On it... mostly.",   "translation": "..."},
            ],
        }
    ],
}


def _fake_communicate():
    async def fake_save(path):
        Path(path).write_bytes(b"ID3" + b"\x00" * 100)

    mock_instance = MagicMock()
    mock_instance.save = fake_save
    return mock_instance


def test_generate_audio_creates_one_mp3_per_line():
    with tempfile.TemporaryDirectory() as tmpdir:
        output_dir = Path(tmpdir)

        with patch("steps.generate_audio.edge_tts.Communicate") as mock_communicate:
            mock_communicate.return_value = _fake_communicate()
            paths = generate_audio(_SCRIPT, output_dir)

        assert len(paths) == 2
        assert mock_communicate.call_count == 2
        for path in paths:
            assert path.exists()


def test_generate_audio_voice_matches_gender():
    """Female character gets VOICE_FEMALE, male gets VOICE_MALE — regardless of A/B slot."""
    with tempfile.TemporaryDirectory() as tmpdir:
        output_dir = Path(tmpdir)

        with patch("steps.generate_audio.edge_tts.Communicate") as mock_communicate, \
             patch("steps.generate_audio.config") as mock_config:

            mock_config.VOICE_FEMALE = "en-US-JennyNeural"
            mock_config.VOICE_MALE   = "en-US-GuyNeural"
            mock_communicate.return_value = _fake_communicate()

            generate_audio(_SCRIPT, output_dir)

        calls = mock_communicate.call_args_list
        assert calls[0].args[1] == "en-US-JennyNeural"  # A is female → female voice
        assert calls[1].args[1] == "en-US-GuyNeural"    # B is male   → male voice


def test_generate_audio_voice_matches_gender_reversed():
    """When male is A and female is B, voices must still match gender, not slot."""
    with tempfile.TemporaryDirectory() as tmpdir:
        output_dir = Path(tmpdir)

        with patch("steps.generate_audio.edge_tts.Communicate") as mock_communicate, \
             patch("steps.generate_audio.config") as mock_config:

            mock_config.VOICE_FEMALE = "en-US-JennyNeural"
            mock_config.VOICE_MALE   = "en-US-GuyNeural"
            mock_communicate.return_value = _fake_communicate()

            generate_audio(_SCRIPT_REVERSED_GENDERS, output_dir)

        calls = mock_communicate.call_args_list
        assert calls[0].args[1] == "en-US-GuyNeural"    # A is male   → male voice
        assert calls[1].args[1] == "en-US-JennyNeural"  # B is female → female voice


def test_generate_audio_skips_existing_files():
    with tempfile.TemporaryDirectory() as tmpdir:
        output_dir = Path(tmpdir)
        (output_dir / "line_1_1.mp3").write_bytes(b"audio")
        (output_dir / "line_1_2.mp3").write_bytes(b"audio")

        with patch("steps.generate_audio.edge_tts.Communicate") as mock_communicate:
            generate_audio(_SCRIPT, output_dir)
            mock_communicate.assert_not_called()
