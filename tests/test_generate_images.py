# tests/test_generate_images.py
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

from steps.generate_images import generate_images

_SCRIPT = {
    "topic": "test",
    "rounds": [
        {"round": 1, "illustration_prompt": "Office cartoon scene",
         "lines": [{"speaker": "A", "text": "Hello"}, {"speaker": "B", "text": "Hi"}]},
        {"round": 2, "illustration_prompt": "Another office scene",
         "lines": [{"speaker": "A", "text": "Update?"}, {"speaker": "B", "text": "Soon!"}]},
    ],
}


def test_generate_images_saves_one_png_per_round():
    fake_image_bytes = b"\x89PNG\r\n\x1a\n" + b"\x00" * 100

    mock_generated_image = MagicMock()
    mock_generated_image.image.image_bytes = fake_image_bytes
    mock_response = MagicMock()
    mock_response.generated_images = [mock_generated_image]

    with tempfile.TemporaryDirectory() as tmpdir:
        output_dir = Path(tmpdir)
        with patch("steps.generate_images.genai") as mock_genai:
            mock_client = MagicMock()
            mock_genai.Client.return_value = mock_client
            mock_client.models.generate_images.return_value = mock_response
            paths = generate_images(_SCRIPT, output_dir)

        assert len(paths) == 2
        assert mock_client.models.generate_images.call_count == 2
        for path in paths:
            assert path.exists()


def test_generate_images_skips_existing_files():
    with tempfile.TemporaryDirectory() as tmpdir:
        output_dir = Path(tmpdir)
        (output_dir / "round_1.png").write_bytes(b"fake")
        (output_dir / "round_2.png").write_bytes(b"fake")

        with patch("steps.generate_images.genai") as mock_genai:
            mock_client = MagicMock()
            mock_genai.Client.return_value = mock_client
            paths = generate_images(_SCRIPT, output_dir)
            mock_client.models.generate_images.assert_not_called()

        assert len(paths) == 2
