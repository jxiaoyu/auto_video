# tests/test_export_bilingual.py
import tempfile
from pathlib import Path

from steps.export_bilingual import export_bilingual

_SCRIPT = {
    "topic": "职场催进度",
    "characters": {
        "A": {"name": "Emily", "appearance": "woman in navy blazer"},
        "B": {"name": "Kevin", "appearance": "man in light blue shirt"},
    },
    "rounds": [
        {
            "round": 1,
            "illustration_prompt": "Emily walks up to Kevin's desk",
            "lines": [
                {"speaker": "A", "text": "Hey Kevin, got a minute?", "translation": "嘿凯文，有空吗？"},
                {"speaker": "B", "text": "Sure, what's up?", "translation": "当然，怎么了？"},
            ],
        }
    ],
}


def test_export_bilingual_creates_file():
    with tempfile.TemporaryDirectory() as tmpdir:
        out = export_bilingual(_SCRIPT, Path(tmpdir))
        assert out.exists()
        assert out.name == "bilingual.txt"


def test_export_bilingual_contains_names_and_translations():
    with tempfile.TemporaryDirectory() as tmpdir:
        out = export_bilingual(_SCRIPT, Path(tmpdir))
        text = out.read_text(encoding="utf-8")

        assert "Emily" in text
        assert "Kevin" in text
        assert "Hey Kevin, got a minute?" in text
        assert "嘿凯文，有空吗？" in text
        assert "Sure, what's up?" in text
        assert "当然，怎么了？" in text


def test_export_bilingual_skips_existing_file():
    with tempfile.TemporaryDirectory() as tmpdir:
        out_path = Path(tmpdir) / "bilingual.txt"
        out_path.write_text("existing content", encoding="utf-8")

        export_bilingual(_SCRIPT, Path(tmpdir))

        # File should not have been overwritten
        assert out_path.read_text(encoding="utf-8") == "existing content"
