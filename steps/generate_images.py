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
