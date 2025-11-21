#!/usr/bin/env python3
"""
Create a patient-level train/val/test split without leaking subjects across sets.
The script scans a directory of JPG images, extracts the patient identifier from
each filename, shuffles patients deterministically, and writes both JSON and TXT
manifests with the requested 70/10/20 split (or custom ratios via CLI flags).
"""

from __future__ import annotations

import argparse
import json
import math
import random
import re
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Sequence, Tuple

# Compile once so the regex is fast and easy to tweak if naming changes later.
PATIENT_PATTERN = re.compile(r"^[^_]+_[^_]+_(?P<patient>[A-Za-z0-9]+)")


def parse_args() -> argparse.Namespace:
    """Configure all CLI flags so the script stays reproducible and configurable."""
    parser = argparse.ArgumentParser(
        description="Patient-level data split for the gastric cancer dataset."
    )
    parser.add_argument(
        "--image-dir",
        type=Path,
        default=Path("/Users/huangyijun/Projects/胃癌T分期/Gastric_Cancer_Dataset_Cropped/images"),
        help="Directory that stores all JPG images (default points to cropped dataset).",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("/Users/huangyijun/Projects/胃癌T分期/splits"),
        help="Directory where the split manifests will be written.",
    )
    parser.add_argument(
        "--ratios",
        type=float,
        nargs=3,
        default=(0.7, 0.1, 0.2),
        metavar=("TRAIN", "VAL", "TEST"),
        help="Train/val/test ratios that must sum to 1.0 (defaults to 70/10/20).",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="Random seed so that the patient ordering and split stay reproducible.",
    )
    return parser.parse_args()


def extract_patient_id(stem: str) -> str:
    """Return the patient identifier encoded in the filename stem."""
    match = PATIENT_PATTERN.match(stem)
    if not match:
        raise ValueError(
            f"Filename '{stem}' does not follow the expected pattern "
            "'<group>_<course>_<patient> (image)'."
        )
    return match.group("patient")


def build_patient_index(image_dir: Path) -> Dict[str, List[Path]]:
    """
    Walk through the directory once, bucket every image path under its patient ID,
    and return a dictionary that maps patient -> list[Path].
    """
    if not image_dir.exists():
        raise FileNotFoundError(f"Image directory '{image_dir}' does not exist.")

    patient_to_files: Dict[str, List[Path]] = defaultdict(list)
    for path in sorted(image_dir.glob("*.jpg")):
        patient_id = extract_patient_id(path.stem)
        patient_to_files[patient_id].append(path)

    if not patient_to_files:
        raise RuntimeError(f"No JPG files found inside '{image_dir}'.")
    return patient_to_files


def normalize_ratios(ratios: Sequence[float]) -> Tuple[float, float, float]:
    """Ensure the three ratios sum to 1.0 to avoid silently dropping patients."""
    if len(ratios) != 3:
        raise ValueError("Exactly three ratios are required (train, val, test).")
    total = sum(ratios)
    if not math.isclose(total, 1.0, rel_tol=1e-6):
        ratios = tuple(r / total for r in ratios)  # type: ignore[assignment]
    return tuple(ratios)  # type: ignore[return-value]


def compute_split_counts(
    total_patients: int, ratios: Sequence[float]
) -> Tuple[int, int, int]:
    """Allocate the integer counts using the largest-remainder method."""
    if total_patients < 3:
        raise ValueError("Need at least three patients to create all splits.")

    normalized = normalize_ratios(ratios)
    raw_counts = [total_patients * r for r in normalized]
    counts = [math.floor(x) for x in raw_counts]
    remainder = total_patients - sum(counts)

    # Distribute leftover patients to the splits with the highest fractional parts.
    fractional_order = sorted(
        range(3), key=lambda idx: raw_counts[idx] - counts[idx], reverse=True
    )
    for i in range(remainder):
        counts[fractional_order[i]] += 1

    if min(counts) == 0:
        raise ValueError(
            f"Ratios {normalized} are incompatible with {total_patients} patients."
        )
    return counts[0], counts[1], counts[2]


def assign_patients(
    patient_ids: List[str], counts: Tuple[int, int, int], seed: int
) -> Dict[str, List[str]]:
    """Shuffle IDs deterministically and slice them into train/val/test buckets."""
    random.seed(seed)
    shuffled = patient_ids[:]
    random.shuffle(shuffled)

    train_count, val_count, test_count = counts
    splits = {
        "train": shuffled[:train_count],
        "val": shuffled[train_count : train_count + val_count],
        "test": shuffled[train_count + val_count : train_count + val_count + test_count],
    }
    return splits


def summarize_split(
    name: str, patients: List[str], patient_to_files: Dict[str, List[Path]]
) -> Dict[str, object]:
    """Build a lightweight summary for JSON export."""
    files = [str(path.name) for pid in patients for path in patient_to_files[pid]]
    return {
        "num_patients": len(patients),
        "num_images": len(files),
        "patients": sorted(patients),
        "files": sorted(files),
    }


def write_outputs(
    output_dir: Path,
    splits: Dict[str, List[str]],
    patient_to_files: Dict[str, List[Path]],
    image_dir: Path,
    ratios: Sequence[float],
    seed: int,
) -> None:
    """Persist both JSON (rich metadata) and TXT (simple manifests)."""
    output_dir.mkdir(parents=True, exist_ok=True)

    payload = {
        "metadata": {
            "image_dir": str(image_dir),
            "total_patients": len(patient_to_files),
            "total_images": sum(len(files) for files in patient_to_files.values()),
            "ratios": list(normalize_ratios(ratios)),
            "seed": seed,
        },
        "splits": {
            split_name: summarize_split(split_name, patients, patient_to_files)
            for split_name, patients in splits.items()
        },
    }

    json_path = output_dir / "patient_split.json"
    json_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False))

    for split_name, patients in splits.items():
        (output_dir / f"{split_name}_patients.txt").write_text(
            "\n".join(sorted(patients)) + "\n"
        )
        image_list = [
            str(patient_to_files[pid][idx].name)
            for pid in patients
            for idx in range(len(patient_to_files[pid]))
        ]
        (output_dir / f"{split_name}_images.txt").write_text(
            "\n".join(sorted(image_list)) + "\n"
        )


def main() -> None:
    """Glue all helper functions together for a clean CLI entry-point."""
    args = parse_args()
    patient_map = build_patient_index(args.image_dir)

    train_count, val_count, test_count = compute_split_counts(
        len(patient_map), args.ratios
    )
    splits = assign_patients(
        sorted(patient_map.keys()), (train_count, val_count, test_count), args.seed
    )
    write_outputs(args.output_dir, splits, patient_map, args.image_dir, args.ratios, args.seed)

    print(f"Finished! Train/val/test patient counts: {train_count}/{val_count}/{test_count}.")
    print(f"Manifests saved to: {args.output_dir}")


if __name__ == "__main__":
    main()

