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
