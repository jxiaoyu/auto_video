# steps/generate_images.py
from pathlib import Path

from google import genai
from google.genai import types

import config


def generate_images(script: dict, output_dir: Path) -> list[Path]:
    """Generate one cartoon illustration per round via Gemini image generation.

    Requests 9:16 aspect ratio directly via ImageConfig so no post-processing
    is needed. Skips rounds whose PNG already exists.
    Returns list of paths to all round PNG files (in round order).
    """
    client = genai.Client(api_key=config.GEMINI_API_KEY)
    image_paths: list[Path] = []

    # Build a shared character block so every image uses the same appearances.
    # characters[X] may be a plain string (legacy) or {"name": ..., "appearance": ...}
    characters = script.get("characters", {})
    char_block = ""
    if characters:
        def _char_desc(c) -> str:
            if isinstance(c, dict):
                name = c.get("name", "")
                appearance = c.get("appearance", "")
                return f"{name} — {appearance}" if name else appearance
            return str(c)

        char_a = _char_desc(characters.get("A", ""))
        char_b = _char_desc(characters.get("B", ""))
        char_block = (
            f"Character A: {char_a}. "
            f"Character B: {char_b}. "
            "Keep these character designs exactly consistent across all images. "
        )

    for round_data in script["rounds"]:
        round_num = round_data["round"]
        image_path = output_dir / f"round_{round_num}.png"

        if image_path.exists():
            print(f"  [skip] round_{round_num}.png already exists")
            image_paths.append(image_path)
            continue

        prompt = (
            char_block
            + round_data["illustration_prompt"]
            + ", cartoon illustration, clean art style, warm pastel colors, no text"
        )

        response = client.models.generate_content(
            model=config.GEMINI_IMAGE_MODEL,
            contents=prompt,
            config=types.GenerateContentConfig(
                response_modalities=["IMAGE"],
                image_config=types.ImageConfig(
                    aspect_ratio="9:16",
                ),
            ),
        )

        # Extract image bytes from response parts (data is already raw bytes)
        image_bytes = None
        for part in response.candidates[0].content.parts:
            if part.inline_data is not None:
                image_bytes = part.inline_data.data
                break

        if image_bytes is None:
            raise RuntimeError(f"No image returned for round {round_num}")

        try:
            image_path.write_bytes(image_bytes)
        except Exception:
            image_path.unlink(missing_ok=True)
            raise

        print(f"  [done] round_{round_num}.png")
        image_paths.append(image_path)

    return image_paths
