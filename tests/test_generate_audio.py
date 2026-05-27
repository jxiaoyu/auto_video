# tests/test_generate_audio.py
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch, call

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
    fake_audio = b"ID3" + b"\x00" * 100  # fake MP3 bytes

    mock_response = MagicMock()
    mock_response.audio_content = fake_audio

    with tempfile.TemporaryDirectory() as tmpdir:
        output_dir = Path(tmpdir)

        with patch("steps.generate_audio.texttospeech") as mock_tts:
            mock_client = MagicMock()
            mock_tts.TextToSpeechClient.return_value = mock_client
            mock_client.synthesize_speech.return_value = mock_response
            mock_tts.AudioEncoding.MP3 = "MP3"

            paths = generate_audio(_SCRIPT, output_dir)

        assert len(paths) == 2
        assert mock_client.synthesize_speech.call_count == 2

        for path in paths:
            assert path.exists()
            assert path.read_bytes() == fake_audio


def test_generate_audio_uses_correct_voices():
    mock_response = MagicMock()
    mock_response.audio_content = b"audio"

    with tempfile.TemporaryDirectory() as tmpdir:
        output_dir = Path(tmpdir)

        with patch("steps.generate_audio.texttospeech") as mock_tts, \
             patch("steps.generate_audio.config") as mock_config:

            mock_config.VOICE_A = "en-US-Journey-F"
            mock_config.VOICE_B = "en-US-Journey-D"
            mock_config.LANGUAGE_CODE = "en-US"
            mock_tts.AudioEncoding.MP3 = "MP3"

            mock_client = MagicMock()
            mock_tts.TextToSpeechClient.return_value = mock_client
            mock_client.synthesize_speech.return_value = mock_response

            generate_audio(_SCRIPT, output_dir)

        # Check the name= argument passed to VoiceSelectionParams for each call
        vsp_calls = mock_tts.VoiceSelectionParams.call_args_list
        assert vsp_calls[0].kwargs["name"] == "en-US-Journey-F"  # Speaker A
        assert vsp_calls[1].kwargs["name"] == "en-US-Journey-D"  # Speaker B


def test_generate_audio_skips_existing_files():
    with tempfile.TemporaryDirectory() as tmpdir:
        output_dir = Path(tmpdir)
        (output_dir / "line_1_1.mp3").write_bytes(b"audio")
        (output_dir / "line_1_2.mp3").write_bytes(b"audio")

        with patch("steps.generate_audio.texttospeech") as mock_tts:
            mock_client = MagicMock()
            mock_tts.TextToSpeechClient.return_value = mock_client

            generate_audio(_SCRIPT, output_dir)
            mock_client.synthesize_speech.assert_not_called()
