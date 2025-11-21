#!/usr/bin/env python3
"""Extract pathology concept features from the 2025 gastric cancer Excel sheet."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

import pandas as pd


# Improved regex patterns to avoid greedy matching
PATTERN_MAP: dict[str, re.Pattern] = {
    # Match Ki-67 followed by percentage or positive/negative, stop at punctuation or specific keywords
    "ki67": re.compile(r"Ki-?67[^，；。\n]*?(?:\d+(?:%|％)|\+|阳性|阴性)", re.IGNORECASE),
    
    # Match CPS score
    "cps": re.compile(r"CPS[^，；。\n]*?\d+(?:\+| \d+)?", re.IGNORECASE),
    
    # Match PD-1 expression (exclude PD-L1 via lookahead or careful context)
    "pd1": re.compile(r"PD-1(?![-L])(?![a-zA-Z0-9])[^，；。\n]*?(?:\+|阳性|阴性|expression)", re.IGNORECASE),
    
    # Match FoxP3
    "foxp3": re.compile(r"FoxP3[^，；。\n]*?(?:\+|阳性|阴性|散在|少量|个别)", re.IGNORECASE),
    
    # Match CD markers (exclude CD31/CD34 etc)
    "cd3": re.compile(r"CD3(?![0-9])[^，；。\n]*?(?:\+|阳性|阴性)", re.IGNORECASE),
    "cd4": re.compile(r"CD4(?![0-9])[^，；。\n]*?(?:\+|阳性|阴性)", re.IGNORECASE),
    "cd8": re.compile(r"CD8(?![0-9])[^，；。\n]*?(?:\+|阳性|阴性)", re.IGNORECASE),
    
    # Match Vascular/Neural invasion - look for specific phrases
    "vascular": re.compile(r"(?:脉管|血管)(?:内)?(?:瘤栓)?(?:[^，；。\n]*?)?(?:见|有|无|未见)(?:[^，；。\n]*?)?(?:侵犯|瘤栓)?", re.IGNORECASE),
    "neural": re.compile(r"神经(?:侵犯|浸润)?(?:[^，；。\n]*?)?(?:见|有|无|未见)(?:[^，；。\n]*?)?(?:侵犯|浸润)?", re.IGNORECASE),
}

# Mapping for numeric codes
DIFFERENTIATION_MAP = {
    "1": "高分化",
    "2": "中分化",
    "3": "中-低分化",
    "4": "低分化",
    "5": "不确定"
}

LAUREN_MAP = {
    "1": "肠型",
    "2": "弥漫型",
    "3": "混合型",
    "4": "不确定",
    "10": "10" # Keep original if unknown
}

def clean_text(value: object) -> str:
    if pd.isna(value):
        return ""
    text = str(value).strip()
    # Normalize punctuation
    text = text.replace("：", ":").replace("，", ",").replace("；", ";").replace("。", ".")
    return re.sub(r"\s+", " ", text).strip()


def extract_features_from_text(text: str) -> dict[str, str]:
    if not text:
        return {}
    features: dict[str, str] = {}
    
    # Pre-cleaning for extraction
    search_text = clean_text(text)
    
    for key, pattern in PATTERN_MAP.items():
        match = pattern.search(search_text)
        if match:
            val = match.group(0).strip()
            # Cleanup trailing garbage
            val = re.sub(r"[,\.;:]+$", "", val).strip()
            features[key] = val
            
    return features


def map_value(value: str, mapping: dict[str, str]) -> str:
    # Handle cases where value might be "1.0" or "1"
    if not value:
        return value
    
    # Try direct match
    if value in mapping:
        return mapping[value]
    
    # Try removing decimal
    if value.endswith(".0"):
        v_int = value[:-2]
        if v_int in mapping:
            return mapping[v_int]
            
    return value # Return original if no map found


def parse_excel(path: Path) -> dict[str, dict[str, str]]:
    df = pd.read_excel(path, dtype=str)
    results: dict[str, dict[str, str]] = {}

    # Column name patterns (handles slight variations)
    col_diff = next((c for c in df.columns if "分化程度" in str(c)), None)
    col_lauren = next((c for c in df.columns if "Lauren" in str(c)), None)
    col_pt = next((c for c in df.columns if "pT" in str(c) or "pStage" in str(c)), None)

    for _, row in df.iterrows():
        patient_id = clean_text(row.get("住院号", ""))
        if not patient_id:
            continue
            
        pathology_text = clean_text(row.get("病理", ""))
        features = extract_features_from_text(pathology_text)
        
        # Get mapped values
        diff_raw = clean_text(row.get(col_diff, "")) if col_diff else ""
        lauren_raw = clean_text(row.get(col_lauren, "")) if col_lauren else ""
        
        features["differentiation"] = map_value(diff_raw, DIFFERENTIATION_MAP)
        features["lauren"] = map_value(lauren_raw, LAUREN_MAP)
        
        results[patient_id] = {
            "name": clean_text(row.get("姓名", "")),
            "age": clean_text(row.get("年龄", "")),
            "sex": clean_text(row.get("性别： 0=女， 1=男", "")).replace("0", "Female").replace("1", "Male").replace("女", "Female").replace("男", "Male"),
            "tumor_length_cm": clean_text(row.get("长径：cm", "")),
            "tumor_thickness_cm": clean_text(row.get("厚径：cm", "")),
            "cea": clean_text(row.get("CEA", "")),
            "ca199": clean_text(row.get("CA199", "")),
            "concept_features": features,
        }
    return results


def main() -> None:
    parser = argparse.ArgumentParser(description="Extract pathology concept features from Excel.")
    parser.add_argument(
        "--input",
        "-i",
        nargs="+",
        default=["2025胃癌临床整理.xlsx"],
        help="Excel files to scan (default: 2025胃癌临床整理.xlsx)",
    )
    parser.add_argument(
        "--output",
        "-o",
        default="scripts/extracted_pathology_concepts.json",
        help="Path to write extracted JSON.",
    )
    args = parser.parse_args()

    combined: dict[str, dict[str, str]] = {}
    for excel_path in args.input:
        path = Path(excel_path)
        if not path.exists():
            # Try relative to project root if not found
            root_path = Path.cwd() / excel_path
            if root_path.exists():
                path = root_path
            else:
                print(f"Warning: {excel_path} does not exist. Skipping.")
                continue
                
        try:
            print(f"Parsing {path}...")
            extracted = parse_excel(path)
            combined.update(extracted)
        except Exception as e:
            print(f"Error parsing {path}: {e}")

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(combined, ensure_ascii=False, indent=2))
    print(f"Wrote {len(combined)} concept feature entries to {output_path}")


if __name__ == "__main__":
    main()
