# tests/test_assemble_video.py
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch
from PIL import Image

from steps.assemble_video import (
    _get_font,
    _render_subtitle,
    _get_audio_duration,
    assemble_video,
)

_SCRIPT = {
    "topic": "test",
    "rounds": [
        {
            "round": 1,
            "illustration_prompt": "scene",
            "lines": [
                {"speaker": "A", "text": "Hey, quick update on the project?"},
                {"speaker": "B", "text": "Almost done, I swear!"},
            ],
        }
    ],
}


def _make_test_image(path: Path, size=(1080, 1920)):
    img = Image.new("RGB", size, color=(200, 180, 160))
    img.save(str(path))


def test_get_font_returns_font_object():
    font = _get_font(44)
    assert font is not None


def test_render_subtitle_creates_output_image():
    with tempfile.TemporaryDirectory() as tmpdir:
        src = Path(tmpdir) / "round_1.png"
        dst = Path(tmpdir) / "frame.png"
        _make_test_image(src)

        _render_subtitle(src, "Hello world, this is a subtitle!", dst)

        assert dst.exists()
        img = Image.open(dst)
        assert img.size == (1080, 1920)


def test_get_audio_duration_calls_ffprobe():
    with patch("steps.assemble_video.subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(stdout="3.45\n", returncode=0)
        duration = _get_audio_duration(Path("dummy.mp3"))
        assert duration == 3.45
        assert "ffprobe" in mock_run.call_args[0][0]


def test_assemble_video_calls_ffmpeg_for_each_line():
    with tempfile.TemporaryDirectory() as tmpdir:
        output_dir = Path(tmpdir)
        segments_dir = output_dir / "segments"
        segments_dir.mkdir()

        _make_test_image(output_dir / "round_1.png")
        (output_dir / "line_1_1.mp3").write_bytes(b"audio1")
        (output_dir / "line_1_2.mp3").write_bytes(b"audio2")

        with patch("steps.assemble_video.subprocess.run") as mock_run, \
             patch("steps.assemble_video._get_audio_duration") as mock_dur:
            mock_run.return_value = MagicMock(returncode=0)
            mock_dur.return_value = 2.5

            final = assemble_video(_SCRIPT, output_dir)

        # ffmpeg called twice for segments + once for concat = 3 times
        assert mock_run.call_count == 3
        assert final == output_dir / "final.mp4"


def test_assemble_video_skips_if_final_exists():
    with tempfile.TemporaryDirectory() as tmpdir:
        output_dir = Path(tmpdir)
        (output_dir / "final.mp4").write_bytes(b"video")

        with patch("steps.assemble_video.subprocess.run") as mock_run:
            final = assemble_video(_SCRIPT, output_dir)
            mock_run.assert_not_called()

        assert final == output_dir / "final.mp4"
