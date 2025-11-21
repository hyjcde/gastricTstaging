#!/usr/bin/env python3
"""Merge extracted pathology concepts into clinical_data.json files."""

import json
from pathlib import Path

def load_json(path):
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)

def save_json(path, data):
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def main():
    concepts_path = Path("scripts/extracted_pathology_concepts.json")
    if not concepts_path.exists():
        print("Extracted concepts file not found.")
        return

    concepts_data = load_json(concepts_path)
    
    # List of clinical data files to update
    data_files = [
        "gastric-scan-next/data/clinical_data.json",
        "gastric-scan-next/data/clinical_data_2024.json",
        "gastric-scan-next/data/clinical_data_2024_nac.json",
        "gastric-scan-next/data/clinical_data_2019.json",
        "gastric-scan-next/data/clinical_data_2019_nac.json"
    ]

    for file_path_str in data_files:
        file_path = Path(file_path_str)
        if not file_path.exists():
            continue
            
        print(f"Processing {file_path}...")
        clinical_data = load_json(file_path)
        updated_count = 0
        
        for pid, record in clinical_data.items():
            # Check if we have extracted concepts for this PID
            # Note: PIDs in concepts_data are strings
            if pid in concepts_data:
                extracted = concepts_data[pid]
                if "concept_features" in extracted:
                    record["concept_features"] = extracted["concept_features"]
                    updated_count += 1
        
        if updated_count > 0:
            save_json(file_path, clinical_data)
            print(f"  Updated {updated_count} records in {file_path.name}")
        else:
            print(f"  No matching records found in {file_path.name}")

if __name__ == "__main__":
    main()

