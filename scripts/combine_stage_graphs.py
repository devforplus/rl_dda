"""
Combine three stage result PNGs into a single image.

Usage (paths are relative to repo root):
    rye run python scripts/combine_stage_graphs.py \
        --dir src/src/models \
        --files training_results_고급-공격-중심-skill-1.0_20250812_203936.png \
                training_results_중급-균형-skill-0.5_20250812_183740.png \
                training_results_초급-생존-중심-skill-0.1_20250812_165848.png

Output: <dir>/training_results_combined_YYYYMMDD_HHMMSS.png
"""

from __future__ import annotations

import argparse
import os
from datetime import datetime
from typing import List

from PIL import Image


def load_images(base_dir: str, files: List[str]) -> List[Image.Image]:
    images: List[Image.Image] = []
    for f in files:
        path = os.path.join(base_dir, f)
        if not os.path.isfile(path):
            raise FileNotFoundError(path)
        images.append(Image.open(path).convert("RGB"))
    return images


def stack_vertically(images: List[Image.Image]) -> Image.Image:
    # Normalize widths to the max width; center images if widths differ
    max_w = max(img.width for img in images)
    total_h = sum(img.height for img in images)

    canvas = Image.new("RGB", (max_w, total_h), (255, 255, 255))
    y = 0
    for img in images:
        # If an image is narrower, paste centered
        x = (max_w - img.width) // 2
        canvas.paste(img, (x, y))
        y += img.height
    return canvas


def main() -> None:
    parser = argparse.ArgumentParser(description="Combine three PNG graphs into one.")
    parser.add_argument(
        "--dir", default="src/src/models", help="Directory containing PNG files"
    )
    parser.add_argument(
        "--files", nargs=3, metavar=("PNG1", "PNG2", "PNG3"), help="Three PNG filenames"
    )
    args = parser.parse_args()

    images = load_images(args.dir, args.files)
    combined = stack_vertically(images)

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_path = os.path.join(args.dir, f"training_results_combined_{ts}.png")
    combined.save(out_path, format="PNG")
    print(out_path)


if __name__ == "__main__":
    main()

