#!/usr/bin/env python3
"""Run extraction and merging of pathology concept data in one command."""

from __future__ import annotations

import subprocess
import sys

from pathlib import Path

SCRIPT_DIR = Path(__file__).parent


def run_command(cmd: list[str]) -> None:
    print(f"Running: {' '.join(cmd)}")
    result = subprocess.run(cmd, cwd=SCRIPT_DIR.parent)
    if result.returncode != 0:
        sys.exit(result.returncode)


def main() -> None:
    extract_cmd = [
        sys.executable,
        str(SCRIPT_DIR / "extract_pathology_concepts.py"),
        "-i",
        "2025胃癌临床整理.xlsx",
        "-o",
        str(SCRIPT_DIR / "extracted_pathology_concepts.json"),
    ]
    merge_cmd = [
        sys.executable,
        str(SCRIPT_DIR / "merge_clinical_features.py"),
    ]

    run_command(extract_cmd)
    run_command(merge_cmd)


if __name__ == "__main__":
    main()

