# make_video.py
import argparse
import shutil
import sys
from pathlib import Path

import config
from steps.generate_script import generate_script
from steps.generate_images import generate_images
from steps.generate_audio import generate_audio
from steps.assemble_video import assemble_video
from steps.export_bilingual import export_bilingual


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
        "script": ["script.json", "bilingual.txt"],
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

    print("\nStep 1b: Exporting bilingual transcript...")
    bilingual_path = export_bilingual(script, output_dir)

    print("\nStep 2: Generating illustrations...")
    generate_images(script, output_dir)

    print("\nStep 3: Generating audio...")
    generate_audio(script, output_dir)

    print("\nSteps 4-5: Assembling video...")
    final_path = assemble_video(script, output_dir)

    print(f"\n✓ Done!")
    print(f"  Video:    {final_path}")
    print(f"  Bilingual: {bilingual_path}")


if __name__ == "__main__":
    main()
