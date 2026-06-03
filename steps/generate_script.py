# steps/generate_script.py
import json
import re
from pathlib import Path

from google import genai

import config

_PROMPT_TEMPLATE = """我是一位小红书博主，致力于帮助中文母语用户提升英语的听说能力，帮我写一段职场场景对话，主题实用且吸睛，围绕的主题是： {topic}

Requirements:
- 3 to 5 rounds (one round = Speaker A says something, Speaker B responds)
- The dialogue must be ONE continuous conversation — each round flows naturally from the previous, building toward a resolution or punchline at the end
- Total dialogue under 60 seconds when spoken aloud (keep each line short)
- Witty, relatable workplace humor
- Give each character a real first name (common English names). When characters address each other in dialogue, always use their names — never call them "A" or "B".
- Define their specific, consistent visual appearances (clothing, hair, accessories). These same descriptions will be reused in every illustration.
- Each illustration_prompt should describe only the scene/action/emotion for that round, referring to characters by name — appearance is handled separately

Return ONLY valid JSON — no markdown fences, no extra text:
{{
  "topic": "{topic}",
  "characters": {{
    "A": {{
      "name": "[real first name]",
      "appearance": "[detailed appearance: gender, clothing, hair, accessories — be specific so a cartoon artist can draw consistently]"
    }},
    "B": {{
      "name": "[real first name]",
      "appearance": "[detailed appearance: gender, clothing, hair, accessories — be specific so a cartoon artist can draw consistently]"
    }}
  }},
  "rounds": [
    {{
      "round": 1,
      "illustration_prompt": "[scene/action/emotion for this round only, referring to characters by name, e.g. 'Emily walks up to Kevin's desk holding a coffee, Kevin looks up from laptop nervously']",
      "lines": [
        {{"speaker": "A", "text": "...", "translation": "（中文翻译）"}},
        {{"speaker": "B", "text": "...", "translation": "（中文翻译）"}}
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
        model=config.GEMINI_TEXT_MODEL,
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
