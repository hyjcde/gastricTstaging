#!/usr/bin/env python3
import argparse
import glob
import json
import os
from pathlib import Path

import cv2

# Default crop rectangle (same as the 2025 pipeline)
DEFAULT_CROP = (115, 118, 115 + 1051, 118 + 757)


def ensure_dir(path: Path):
    path.mkdir(parents=True, exist_ok=True)


def clamp(value, min_v, max_v):
    return max(min_v, min(max_v, value))


def crop_image(image_path: Path, crop_rect, target_path: Path):
    img = cv2.imread(str(image_path))
    if img is None:
        print(f"[WARN] Unable to read image: {image_path}")
        return False

    h, w = img.shape[:2]
    x1, y1, x2, y2 = crop_rect
    x1 = clamp(x1, 0, w)
    x2 = clamp(x2, 0, w)
    y1 = clamp(y1, 0, h)
    y2 = clamp(y2, 0, h)

    if x2 <= x1 or y2 <= y1:
        print(f"[WARN] Invalid crop for {image_path}: {crop_rect}")
        return False

    cropped = img[y1:y2, x1:x2]
    cv2.imwrite(str(target_path), cropped)
    return True


def shift_annotation(data: dict, crop_rect, target_image_name):
    x1, y1, x2, y2 = crop_rect
    crop_width = x2 - x1
    crop_height = y2 - y1

    new_shapes = []
    for shape in data.get("shapes", []):
        points = shape.get("points", [])
        new_points = []
        for px, py in points:
            nx = px - x1
            ny = py - y1
            nx = clamp(nx, 0, crop_width)
            ny = clamp(ny, 0, crop_height)
            new_points.append([nx, ny])
        if new_points:
            shape["points"] = new_points
            new_shapes.append(shape)
    data["shapes"] = new_shapes
    data["imageHeight"] = crop_height
    data["imageWidth"] = crop_width
    data["imagePath"] = f"../images/{target_image_name}"
    data["imageData"] = None
    return data


def process_dataset(source_root: Path, output_root: Path, crop_rect, dry_run=False):
    overlays_dir = source_root / "overlays"
    images_dir = source_root / "images"
    annotations_dir = source_root / "annotations"
    lymph_dir = source_root / "lymph_node_analysis"

    if not overlays_dir.exists():
        print(f"[ERROR] Overlays directory missing: {overlays_dir}")
        return

    target_dirs = {
        "images": output_root / "images",
        "overlays": output_root / "overlays",
        "annotations": output_root / "annotations",
        "lymph_node_analysis": output_root / "lymph_node_analysis",
    }

    for path in target_dirs.values():
        ensure_dir(path)

    overlay_files = sorted(overlays_dir.glob("*.jpg"))
    print(f"Found {len(overlay_files)} overlay images in {overlays_dir}")

    processed = 0
    for overlay_path in overlay_files:
        relative_name = overlay_path.name
        image_name = relative_name.replace("_overlay.jpg", ".jpg")

        if dry_run:
            processed += 1
            continue

        overlay_target = target_dirs["overlays"] / relative_name
        if crop_image(overlay_path, crop_rect, overlay_target):
            processed += 1

        original_path = images_dir / image_name
        if original_path.exists():
            crop_image(original_path, crop_rect, target_dirs["images"] / image_name)

        annotation_path = annotations_dir / relative_name.replace("_overlay.jpg", ".json")
        if annotation_path.exists():
            with open(annotation_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            shifted = shift_annotation(data, crop_rect, image_name)
            with open(target_dirs["annotations"] / annotation_path.name, "w", encoding="utf-8") as f:
                json.dump(shifted, f, indent=2, ensure_ascii=False)

    if lymph_dir.exists() and not dry_run:
        lymph_files = sorted(lymph_dir.glob("*.jpg"))
        for lymph_path in lymph_files:
            crop_image(lymph_path, crop_rect, target_dirs["lymph_node_analysis"] / lymph_path.name)

    print(f"Processed {processed} overlay files and created cropped set under {output_root}")


def main():
    parser = argparse.ArgumentParser(
        description="Create cropped datasets for legacy cohorts (2019/2024) using the same ROI as the 2025 pipeline."
    )
    parser.add_argument("--year", choices=["2019", "2024"], required=True, help="Cohort year to crop")
    parser.add_argument(
        "--source",
        type=Path,
        help="Optional override for the source dataset root",
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="Optional override for the cropped output root",
    )
    parser.add_argument(
        "--dry-run", action="store_true", help="Only report paths without writing files"
    )
    parser.add_argument(
        "--coords",
        nargs=4,
        type=int,
        metavar=("X1", "Y1", "X2", "Y2"),
        default=DEFAULT_CROP,
        help="Manual crop rectangle (x1 y1 x2 y2)",
    )

    args = parser.parse_args()
    root = Path(os.getcwd())

    defaults = {
        "2019": {
            "source": root / "Gastric_Cancer_Dataset_2019",
            "output": root / "2019年直接手术" / "Cropped",
        },
        "2024": {
            "source": root / "Gastric_Cancer_Dataset_2024",
            "output": root / "Gastric_Cancer_Dataset_2024_Cropped",
        },
    }

    cohort = defaults[args.year]
    source_root = args.source or cohort["source"]
    output_root = args.output or cohort["output"]

    print(f"[INFO] Year: {args.year}")
    print(f"[INFO] Source dataset: {source_root}")
    print(f"[INFO] Output directory: {output_root}")
    print(f"[INFO] Crop rect: {args.coords}")

    if args.dry_run:
        print("[INFO] Dry run enabled, no files will be written.")

    process_dataset(source_root, output_root, tuple(args.coords), dry_run=args.dry_run)


if __name__ == "__main__":
    main()

