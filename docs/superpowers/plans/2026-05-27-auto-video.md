# Auto Video Pipeline Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a Python CLI that takes a topic string and produces a finished vertical MP4 with AI-generated dialogue, cartoon illustrations, TTS voices, and subtitles.

**Architecture:** Five sequential steps (script → images → audio → segments → final.mp4) where each step saves output files to disk and is skipped on re-run if its outputs already exist. Subtitle text is baked into each image via Pillow before FFmpeg combines image + audio into a video segment.

**Tech Stack:** Python 3.10+, `google-genai` (Gemini + Imagen 3), `google-cloud-texttospeech`, `Pillow`, `ffmpeg` (system binary), `pytest` + `unittest.mock`

---

## File Map

| File | Responsibility |
|------|---------------|
| `requirements.txt` | Python dependencies |
| `.env.example` | Template for API keys |
| `config.py` | All configuration: API keys, voices, video dimensions |
| `steps/__init__.py` | Empty package marker |
| `steps/generate_script.py` | Step 1: call Gemini, parse and save `script.json` |
| `steps/generate_images.py` | Step 2: call Imagen 3, save `round_N.png` |
| `steps/generate_audio.py` | Step 3: call Google TTS, save `line_N_M.mp3` |
| `steps/assemble_video.py` | Steps 4–5: bake subtitles with Pillow, assemble with FFmpeg |
| `make_video.py` | CLI entry point, orchestrates all steps, handles `--redo` |
| `tests/__init__.py` | Empty package marker |
| `tests/test_generate_script.py` | Unit tests for Step 1 |
| `tests/test_generate_images.py` | Unit tests for Step 2 |
| `tests/test_generate_audio.py` | Unit tests for Step 3 |
| `tests/test_assemble_video.py` | Unit tests for Steps 4–5 |

---

## Task 1: Project Scaffold

**Files:**
- Create: `requirements.txt`
- Create: `.env.example`
- Create: `config.py`
- Create: `steps/__init__.py`
- Create: `tests/__init__.py`

- [ ] **Step 1: Create `requirements.txt`**

```
google-genai>=0.8.0
google-cloud-texttospeech>=2.16.0
Pillow>=10.0.0
python-dotenv>=1.0.0
pytest>=8.0.0
```

- [ ] **Step 2: Create `.env.example`**

```
GEMINI_API_KEY=your_gemini_api_key_here
GOOGLE_APPLICATION_CREDENTIALS=/path/to/service-account.json
```

- [ ] **Step 3: Create `config.py`**

```python
import os
from dotenv import load_dotenv

load_dotenv()

GEMINI_API_KEY: str = os.environ["GEMINI_API_KEY"]

# Google Cloud TTS uses Application Default Credentials.
# Set GOOGLE_APPLICATION_CREDENTIALS to a service account JSON path,
# or run `gcloud auth application-default login` once.

VOICE_A = "en-US-Journey-F"   # female
VOICE_B = "en-US-Journey-D"   # male
LANGUAGE_CODE = "en-US"

VIDEO_WIDTH = 1080
VIDEO_HEIGHT = 1920

OUTPUT_DIR = "output"
```

- [ ] **Step 4: Create `.gitignore`**

```
.env
output/
__pycache__/
*.pyc
.pytest_cache/
```

- [ ] **Step 5: Create package markers and install dependencies**

```bash
touch steps/__init__.py tests/__init__.py
pip install -r requirements.txt
```

Expected: all packages install without error.

- [ ] **Step 6: Verify ffmpeg is available**

```bash
ffmpeg -version
```

Expected: version line like `ffmpeg version 7.x ...`
If missing: `brew install ffmpeg`

- [ ] **Step 7: Commit**

```bash
git add requirements.txt .env.example .gitignore config.py steps/__init__.py tests/__init__.py
git commit -m "chore: project scaffold and config"
```

---

## Task 2: Script Generation (Step 1)

**Files:**
- Create: `steps/generate_script.py`
- Create: `tests/test_generate_script.py`

- [ ] **Step 1: Write the failing test**

```python
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
```

- [ ] **Step 2: Run to confirm failure**

```bash
pytest tests/test_generate_script.py -v
```

Expected: `ImportError` or `ModuleNotFoundError` (file doesn't exist yet).

- [ ] **Step 3: Implement `steps/generate_script.py`**

```python
# steps/generate_script.py
import json
import re
from pathlib import Path

from google import genai

import config

_PROMPT_TEMPLATE = """Create a funny, engaging English workplace dialogue about: {topic}

Requirements:
- 3 to 5 rounds (one round = Speaker A says something, Speaker B responds)
- Total dialogue under 60 seconds when spoken aloud (keep each line short)
- Witty, relatable workplace humor
- illustration_prompt must describe a cartoon scene showing both characters and their emotions

Return ONLY valid JSON — no markdown fences, no extra text:
{{
  "topic": "{topic}",
  "rounds": [
    {{
      "round": 1,
      "illustration_prompt": "Office scene, [describe both characters + emotions/actions], cartoon style, warm pastel colors, clean lines, vertical 9:16 composition",
      "lines": [
        {{"speaker": "A", "text": "..."}},
        {{"speaker": "B", "text": "..."}}
      ]
    }}
  ]
}}"""


def generate_script(topic: str, output_dir: Path) -> dict:
    """Generate dialogue script via Gemini and save to script.json.

    Skips the API call if script.json already exists.
    Returns the parsed script dict.
    """
    script_path = output_dir / "script.json"

    if script_path.exists():
        print("  [skip] script.json already exists")
        return json.loads(script_path.read_text(encoding="utf-8"))

    client = genai.Client(api_key=config.GEMINI_API_KEY)
    prompt = _PROMPT_TEMPLATE.format(topic=topic)

    response = client.models.generate_content(
        model="gemini-2.0-flash",
        contents=prompt,
    )

    text = response.text.strip()
    # Strip markdown code fences if Gemini wraps output anyway
    text = re.sub(r"^```(?:json)?\n?", "", text)
    text = re.sub(r"\n?```$", "", text)

    script = json.loads(text)

    output_dir.mkdir(parents=True, exist_ok=True)
    try:
        script_path.write_text(
            json.dumps(script, ensure_ascii=False, indent=2), encoding="utf-8"
        )
    except Exception:
        script_path.unlink(missing_ok=True)  # remove partial file on error
        raise

    print(f"  [done] script.json — {len(script['rounds'])} rounds")
    return script
```

- [ ] **Step 4: Run tests to confirm they pass**

```bash
pytest tests/test_generate_script.py -v
```

Expected: 3 tests PASSED.

- [ ] **Step 5: Commit**

```bash
git add steps/generate_script.py tests/test_generate_script.py
git commit -m "feat: Step 1 — Gemini dialogue generation"
```

---

## Task 3: Image Generation (Step 2)

**Files:**
- Create: `steps/generate_images.py`
- Create: `tests/test_generate_images.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_generate_images.py
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

from steps.generate_images import generate_images

_SCRIPT = {
    "topic": "test",
    "rounds": [
        {
            "round": 1,
            "illustration_prompt": "Office cartoon scene",
            "lines": [
                {"speaker": "A", "text": "Hello"},
                {"speaker": "B", "text": "Hi"},
            ],
        },
        {
            "round": 2,
            "illustration_prompt": "Another office scene",
            "lines": [
                {"speaker": "A", "text": "Update?"},
                {"speaker": "B", "text": "Soon!"},
            ],
        },
    ],
}


def test_generate_images_saves_one_png_per_round():
    fake_image_bytes = b"\x89PNG\r\n\x1a\n" + b"\x00" * 100  # minimal PNG header

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
        # Pre-create both round files
        (output_dir / "round_1.png").write_bytes(b"fake")
        (output_dir / "round_2.png").write_bytes(b"fake")

        with patch("steps.generate_images.genai") as mock_genai:
            mock_client = MagicMock()
            mock_genai.Client.return_value = mock_client

            paths = generate_images(_SCRIPT, output_dir)
            mock_client.models.generate_images.assert_not_called()

        assert len(paths) == 2
```

- [ ] **Step 2: Run to confirm failure**

```bash
pytest tests/test_generate_images.py -v
```

Expected: `ImportError` (file doesn't exist yet).

- [ ] **Step 3: Implement `steps/generate_images.py`**

```python
# steps/generate_images.py
from pathlib import Path

from google import genai
from google.genai import types

import config


def generate_images(script: dict, output_dir: Path) -> list[Path]:
    """Generate one cartoon illustration per round via Imagen 3.

    Skips rounds whose PNG already exists.
    Returns list of paths to all round PNG files (in round order).
    """
    client = genai.Client(api_key=config.GEMINI_API_KEY)
    image_paths: list[Path] = []

    for round_data in script["rounds"]:
        round_num = round_data["round"]
        image_path = output_dir / f"round_{round_num}.png"

        if image_path.exists():
            print(f"  [skip] round_{round_num}.png already exists")
            image_paths.append(image_path)
            continue

        prompt = (
            round_data["illustration_prompt"]
            + ", cartoon illustration, clean art style, vertical format"
        )

        response = client.models.generate_images(
            model="imagen-3.0-generate-001",
            prompt=prompt,
            config=types.GenerateImagesConfig(
                number_of_images=1,
                aspect_ratio="9:16",
            ),
        )

        image_bytes = response.generated_images[0].image.image_bytes
        try:
            image_path.write_bytes(image_bytes)
        except Exception:
            image_path.unlink(missing_ok=True)
            raise

        print(f"  [done] round_{round_num}.png")
        image_paths.append(image_path)

    return image_paths
```

- [ ] **Step 4: Run tests to confirm they pass**

```bash
pytest tests/test_generate_images.py -v
```

Expected: 2 tests PASSED.

- [ ] **Step 5: Commit**

```bash
git add steps/generate_images.py tests/test_generate_images.py
git commit -m "feat: Step 2 — Imagen 3 illustration generation"
```

---

## Task 4: Audio Generation (Step 3)

**Files:**
- Create: `steps/generate_audio.py`
- Create: `tests/test_generate_audio.py`

- [ ] **Step 1: Write the failing test**

```python
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

            # Attach enum values used in the implementation
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
```

- [ ] **Step 2: Run to confirm failure**

```bash
pytest tests/test_generate_audio.py -v
```

Expected: `ImportError` (file doesn't exist yet).

- [ ] **Step 3: Implement `steps/generate_audio.py`**

```python
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
```

- [ ] **Step 4: Run tests to confirm they pass**

```bash
pytest tests/test_generate_audio.py -v
```

Expected: 3 tests PASSED.

- [ ] **Step 5: Commit**

```bash
git add steps/generate_audio.py tests/test_generate_audio.py
git commit -m "feat: Step 3 — Google Cloud TTS audio generation"
```

---

## Task 5: Video Assembly (Steps 4–5)

**Files:**
- Create: `steps/assemble_video.py`
- Create: `tests/test_assemble_video.py`

Note: Subtitle text is baked into the image via Pillow (rather than FFmpeg `drawtext`) for reliable cross-platform font rendering.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_assemble_video.py
import json
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch, call
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

        # Create fake round image and audio files
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
```

- [ ] **Step 2: Run to confirm failure**

```bash
pytest tests/test_assemble_video.py -v
```

Expected: `ImportError` (file doesn't exist yet).

- [ ] **Step 3: Implement `steps/assemble_video.py`**

```python
# steps/assemble_video.py
import subprocess
import textwrap
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

import config


# ── Font helpers ─────────────────────────────────────────────────────────────

def _get_font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    """Return a TrueType font at `size`, falling back to Pillow's default."""
    candidates = [
        "/System/Library/Fonts/Helvetica.ttc",                        # macOS
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",       # Linux
        "C:/Windows/Fonts/arial.ttf",                                  # Windows
    ]
    for path in candidates:
        try:
            return ImageFont.truetype(path, size)
        except OSError:
            continue
    return ImageFont.load_default()


# ── Subtitle rendering ────────────────────────────────────────────────────────

def _render_subtitle(image_path: Path, text: str, dest_path: Path) -> None:
    """Overlay subtitle text on the bottom of an image and save to dest_path."""
    img = Image.open(image_path).convert("RGB")
    img = img.resize((config.VIDEO_WIDTH, config.VIDEO_HEIGHT), Image.LANCZOS)

    font = _get_font(44)
    wrapped = textwrap.fill(text, width=35)

    # Measure wrapped text
    tmp_draw = ImageDraw.Draw(img)
    bbox = tmp_draw.multiline_textbbox((0, 0), wrapped, font=font, align="center")
    text_w = bbox[2] - bbox[0]
    text_h = bbox[3] - bbox[1]

    x = (config.VIDEO_WIDTH - text_w) // 2
    y = config.VIDEO_HEIGHT - text_h - 80

    # Semi-transparent dark box behind text
    padding = 14
    overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
    overlay_draw = ImageDraw.Draw(overlay)
    overlay_draw.rectangle(
        [x - padding, y - padding, x + text_w + padding, y + text_h + padding],
        fill=(0, 0, 0, 160),
    )
    img = Image.alpha_composite(img.convert("RGBA"), overlay).convert("RGB")

    # Black outline, then white text
    draw = ImageDraw.Draw(img)
    for dx, dy in [(-2, -2), (2, -2), (-2, 2), (2, 2)]:
        draw.multiline_text((x + dx, y + dy), wrapped, font=font, fill="black", align="center")
    draw.multiline_text((x, y), wrapped, font=font, fill="white", align="center")

    img.save(str(dest_path))


# ── Audio helpers ─────────────────────────────────────────────────────────────

def _get_audio_duration(audio_path: Path) -> float:
    """Return the duration in seconds of an MP3 file via ffprobe."""
    result = subprocess.run(
        [
            "ffprobe", "-v", "error",
            "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1",
            str(audio_path),
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    return float(result.stdout.strip())


# ── Video assembly ────────────────────────────────────────────────────────────

def assemble_video(script: dict, output_dir: Path) -> Path:
    """Combine images, audio, and subtitle text into a final MP4.

    Skips entirely if final.mp4 already exists.
    Returns path to final.mp4.
    """
    final_path = output_dir / "final.mp4"
    if final_path.exists():
        print("  [skip] final.mp4 already exists")
        return final_path

    segments_dir = output_dir / "segments"
    segments_dir.mkdir(exist_ok=True)

    segment_paths: list[Path] = []

    for round_data in script["rounds"]:
        round_num = round_data["round"]
        round_image = output_dir / f"round_{round_num}.png"

        for line_idx, line in enumerate(round_data["lines"], start=1):
            audio_path = output_dir / f"line_{round_num}_{line_idx}.mp3"
            segment_path = segments_dir / f"seg_{round_num}_{line_idx}.mp4"

            # Bake subtitle into a temporary frame image
            frame_path = segments_dir / f"frame_{round_num}_{line_idx}.png"
            _render_subtitle(round_image, line["text"], frame_path)

            duration = _get_audio_duration(audio_path)

            subprocess.run(
                [
                    "ffmpeg", "-y",
                    "-loop", "1",
                    "-i", str(frame_path),
                    "-i", str(audio_path),
                    "-c:v", "libx264",
                    "-tune", "stillimage",
                    "-c:a", "aac",
                    "-b:a", "192k",
                    "-pix_fmt", "yuv420p",
                    "-t", str(duration),
                    str(segment_path),
                ],
                check=True,
                capture_output=True,
            )
            print(f"  [done] segment {round_num}_{line_idx}")
            segment_paths.append(segment_path)

    # Write concat list
    concat_path = segments_dir / "concat.txt"
    concat_path.write_text(
        "\n".join(f"file '{p.resolve()}'" for p in segment_paths)
    )

    subprocess.run(
        [
            "ffmpeg", "-y",
            "-f", "concat",
            "-safe", "0",
            "-i", str(concat_path),
            "-c", "copy",
            str(final_path),
        ],
        check=True,
        capture_output=True,
    )
    print(f"  [done] final.mp4")
    return final_path
```

- [ ] **Step 4: Run tests to confirm they pass**

```bash
pytest tests/test_assemble_video.py -v
```

Expected: 5 tests PASSED.

- [ ] **Step 5: Commit**

```bash
git add steps/assemble_video.py tests/test_assemble_video.py
git commit -m "feat: Steps 4-5 — subtitle rendering and FFmpeg video assembly"
```

---

## Task 6: Main Orchestrator

**Files:**
- Create: `make_video.py`

- [ ] **Step 1: Implement `make_video.py`**

```python
# make_video.py
import argparse
import glob
import shutil
import subprocess
import sys
from pathlib import Path

import config
from steps.generate_script import generate_script
from steps.generate_images import generate_images
from steps.generate_audio import generate_audio
from steps.assemble_video import assemble_video


def _check_ffmpeg() -> None:
    if shutil.which("ffmpeg") is None:
        print("ERROR: ffmpeg not found.")
        print("Install with:  brew install ffmpeg")
        sys.exit(1)


def _clear_step(output_dir: Path, step: str) -> None:
    """Delete output files for `step` and all downstream steps."""
    all_steps = ["script", "images", "audio", "video"]
    idx = all_steps.index(step)
    patterns = {
        "script": ["script.json"],
        "images": ["round_*.png"],
        "audio":  ["line_*.mp3"],
        "video":  ["segments/", "final.mp4"],
    }
    for s in all_steps[idx:]:
        for pattern in patterns[s]:
            target = output_dir / pattern
            if target.is_dir():
                shutil.rmtree(target)
                print(f"  [redo] removed {pattern}")
            else:
                for match in output_dir.glob(pattern):
                    match.unlink()
                    print(f"  [redo] removed {match.name}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate an English conversation video from a topic."
    )
    parser.add_argument("--topic", required=True, help="Video topic, e.g. '职场催进度'")
    parser.add_argument(
        "--redo",
        choices=["script", "images", "audio", "video"],
        help="Re-run from this step onward, deleting its existing output first.",
    )
    args = parser.parse_args()

    _check_ffmpeg()

    output_dir = Path(config.OUTPUT_DIR) / args.topic
    output_dir.mkdir(parents=True, exist_ok=True)

    if args.redo:
        print(f"Clearing outputs from step '{args.redo}' onward...")
        _clear_step(output_dir, args.redo)

    print("\nStep 1: Generating dialogue script...")
    script = generate_script(args.topic, output_dir)

    print("\nStep 2: Generating illustrations...")
    generate_images(script, output_dir)

    print("\nStep 3: Generating audio...")
    generate_audio(script, output_dir)

    print("\nSteps 4-5: Assembling video...")
    final_path = assemble_video(script, output_dir)

    print(f"\n✓ Done! Video saved to: {final_path}")


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Run the full test suite to ensure nothing is broken**

```bash
pytest tests/ -v
```

Expected: all tests PASSED.

- [ ] **Step 3: Commit**

```bash
git add make_video.py
git commit -m "feat: main orchestrator with --redo support"
```

---

## Task 7: End-to-End Smoke Test

- [ ] **Step 1: Copy `.env.example` to `.env` and fill in keys**

```bash
cp .env.example .env
# Edit .env:
#   GEMINI_API_KEY=<your key from Google AI Studio>
#   GOOGLE_APPLICATION_CREDENTIALS=<path to service account JSON>
#   (or run: gcloud auth application-default login)
```

- [ ] **Step 2: Run the pipeline with a test topic**

```bash
python make_video.py --topic "职场催进度"
```

Expected output:
```
Step 1: Generating dialogue script...
  [done] script.json — 4 rounds
Step 2: Generating illustrations...
  [done] round_1.png
  ...
Step 3: Generating audio...
  [done] line_1_1.mp3 (A: ...)
  ...
Steps 4-5: Assembling video...
  [done] segment 1_1
  ...
  [done] final.mp4

✓ Done! Video saved to: output/职场催进度/final.mp4
```

- [ ] **Step 3: Open and verify the video**

```bash
open output/职场催进度/final.mp4
```

Check:
- [ ] Vertical format, ~1 minute
- [ ] Cartoon illustration changes each round
- [ ] Two distinct voices alternate
- [ ] Subtitle text visible at bottom of each line

- [ ] **Step 4: Test the --redo flag**

```bash
python make_video.py --topic "职场催进度" --redo images
```

Expected: `script.json` is skipped; images are re-generated; audio and video are re-built.

- [ ] **Step 5: Final commit**

```bash
git add .env.example
git commit -m "chore: add .env.example and complete smoke test"
```
