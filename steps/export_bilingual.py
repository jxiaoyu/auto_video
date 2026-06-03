# steps/export_bilingual.py
from pathlib import Path


def export_bilingual(script: dict, output_dir: Path) -> Path:
    """Write a Chinese-English bilingual reading transcript to bilingual.txt.

    Skips if the file already exists.
    Returns the path to bilingual.txt.
    """
    out_path = output_dir / "bilingual.txt"

    if out_path.exists():
        print("  [skip] bilingual.txt already exists")
        return out_path

    characters = script.get("characters", {})

    def char_info(key: str) -> tuple[str, str]:
        """Return (name, appearance) for character key A or B."""
        c = characters.get(key, {})
        if isinstance(c, dict):
            return c.get("name", key), c.get("appearance", "")
        return key, str(c)

    name_a, appearance_a = char_info("A")
    name_b, appearance_b = char_info("B")

    lines: list[str] = []

    # Header
    lines.append(f"Topic: {script.get('topic', '')}")
    lines.append("")
    lines.append("Characters:")
    lines.append(f"  {name_a} (A): {appearance_a}")
    lines.append(f"  {name_b} (B): {appearance_b}")
    lines.append("")
    lines.append("=" * 50)

    # Rounds
    for round_data in script.get("rounds", []):
        lines.append("")
        lines.append(f"Round {round_data['round']}")
        lines.append("-" * 30)

        for line in round_data.get("lines", []):
            speaker_key = line.get("speaker", "?")
            name = name_a if speaker_key == "A" else name_b
            text = line.get("text", "")
            translation = line.get("translation", "")

            lines.append(f"{name}: {text}")
            if translation:
                lines.append(f"        {translation}")
            lines.append("")

    output_dir.mkdir(parents=True, exist_ok=True)
    out_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"  [done] bilingual.txt — {len(script.get('rounds', []))} rounds")
    return out_path
