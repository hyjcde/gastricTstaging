#!/usr/bin/env python3
"""Compare the extracted concept features with the original pathology text for spot checks."""

from __future__ import annotations

import argparse
import json
import random
from pathlib import Path


def load_clinical(path: Path) -> dict[str, dict]:
    if not path.exists():
        raise FileNotFoundError(path)
    return json.loads(path.read_text(encoding='utf-8'))


def print_sample(sample: tuple[str, dict], clinical_data: dict[str, dict]) -> None:
    pid, concepts = sample
    record = clinical_data.get(pid)
    if not record:
        return
    pathology = record.get("pathology", {}).get("type", "").replace("\n", " ")
    print(f"\nPatient {pid}")
    print("Pathology excerpt:", pathology[:200] + "..." if len(pathology) > 200 else pathology)
    for key, value in concepts.get("concept_features", {}).items():
        print(f"  {key}: {value}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Spot-check extracted pathology concept quality")
    parser.add_argument(
        "--concepts",
        "-c",
        default="scripts/extracted_pathology_concepts.json",
        help="Merged JSON of extracted concept features",
    )
    parser.add_argument(
        "--clinical",
        "-d",
        default="gastric-scan-next/data/clinical_data.json",
        help="Clinical JSON to cross-reference",
    )
    parser.add_argument(
        "--count",
        "-n",
        type=int,
        default=5,
        help="Number of random samples to inspect",
    )
    args = parser.parse_args()

    concepts_data = load_clinical(Path(args.concepts))
    clinical_data = load_clinical(Path(args.clinical))

    patient_ids = list(concepts_data.keys())
    if not patient_ids:
        print("No extracted concepts found.")
        return

    random.seed(42)
    samples = random.sample(patient_ids, min(args.count, len(patient_ids)))
    for pid in samples:
        print_sample((pid, concepts_data[pid]), clinical_data)


if __name__ == "__main__":
    main()

