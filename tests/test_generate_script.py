# tests/test_generate_script.py
import json
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

from steps.generate_script import generate_script


def _make_mock_script(topic="test topic"):
    return {
        "topic": topic,
        "rounds": [
            {
                "round": 1,
                "illustration_prompt": "Office scene, cartoon style",
                "lines": [
                    {"speaker": "A", "text": "Hey, quick update?"},
                    {"speaker": "B", "text": "On it... mostly."},
                ],
            }
        ],
    }


def test_generate_script_calls_gemini_and_saves_json():
    mock_response = MagicMock()
    mock_response.text = json.dumps(_make_mock_script())

    with tempfile.TemporaryDirectory() as tmpdir:
        output_dir = Path(tmpdir)

        with patch("steps.generate_script.genai") as mock_genai:
            mock_client = MagicMock()
            mock_genai.Client.return_value = mock_client
            mock_client.models.generate_content.return_value = mock_response

            result = generate_script("test topic", output_dir)

        assert result["topic"] == "test topic"
        assert len(result["rounds"]) == 1
        assert result["rounds"][0]["lines"][0]["speaker"] == "A"
        assert (output_dir / "script.json").exists()


def test_generate_script_skips_if_json_exists():
    with tempfile.TemporaryDirectory() as tmpdir:
        output_dir = Path(tmpdir)
        existing = _make_mock_script("cached topic")
        (output_dir / "script.json").write_text(json.dumps(existing))

        with patch("steps.generate_script.genai") as mock_genai:
            result = generate_script("cached topic", output_dir)
            mock_genai.Client.assert_not_called()

        assert result["topic"] == "cached topic"


def test_generate_script_strips_markdown_fences():
    raw = "```json\n" + json.dumps(_make_mock_script()) + "\n```"
    mock_response = MagicMock()
    mock_response.text = raw

    with tempfile.TemporaryDirectory() as tmpdir:
        output_dir = Path(tmpdir)

        with patch("steps.generate_script.genai") as mock_genai:
            mock_client = MagicMock()
            mock_genai.Client.return_value = mock_client
            mock_client.models.generate_content.return_value = mock_response

            result = generate_script("test topic", output_dir)

        assert result["topic"] == "test topic"
