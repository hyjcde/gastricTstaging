import pandas as pd
import json
import os
import numpy as np

# 配置路径
EXCEL_PATH = "/Users/huangyijun/Projects/胃癌T分期/2025胃癌临床整理.xlsx"
OUTPUT_PATH = "/Users/huangyijun/Projects/胃癌T分期/gastric-scan-next/data/clinical_data.json"

# 确保输出目录存在
os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)

def safe_float(val):
    try:
        if pd.isna(val): return None
        return float(val)
    except:
        return None

def safe_str(val):
    if pd.isna(val): return ""
    return str(val).strip()

def map_sex(val):
    if pd.isna(val):
        return "Unknown"
    val_str = str(val).strip()
    if val_str == "男" or val_str == "1" or val_str == "1.0":
        return "Male"
    elif val_str == "女" or val_str == "0" or val_str == "0.0":
        return "Female"
    else:
        return "Unknown"

def map_tumor_location(val):
    try:
        v = int(val)
        mapping = {
            0: "Cardia/Fundus",
            1: "Body",
            2: "Angle/Antrum",
            3: "Whole Stomach"
        }
        return mapping.get(v, "Unknown")
    except:
        return "Unknown"

def map_differentiation(val):
    try:
        v = int(val)
        mapping = {
            1: "Well Differentiated",
            2: "Moderately Differentiated",
            3: "Mod-Poorly Differentiated",
            4: "Poorly Differentiated",
            5: "Undetermined"
        }
        return mapping.get(v, "Unknown")
    except:
        return "Unknown"

def process_excel():
    print(f"Reading Excel: {EXCEL_PATH}")
    
    # Read all sheets
    xls = pd.ExcelFile(EXCEL_PATH)
    print(f"Found {len(xls.sheet_names)} sheets: {xls.sheet_names}")
    
    # Combine all sheets
    all_dfs = []
    for sheet_name in xls.sheet_names:
        df_sheet = pd.read_excel(xls, sheet_name=sheet_name)
        print(f"  Sheet '{sheet_name}': {len(df_sheet)} rows")
        all_dfs.append(df_sheet)
    
    # Concatenate all dataframes
    df = pd.concat(all_dfs, ignore_index=True)
    print(f"Total rows after merging: {len(df)}")
    
    clinical_data = {}
    
    for _, row in df.iterrows():
        # 获取ID (住院号)
        patient_id = safe_str(row.get('住院号'))
        if not patient_id:
            continue
            
        # 构建数据对象
        data = {
            "age": safe_float(row.get('年龄')),
            "sex": map_sex(row.get('性别： 0=女， 1=男')),
            "tumorSize": {
                "length": safe_float(row.get('长径：cm')),
                "thickness": safe_float(row.get('厚径：cm'))
            },
            "location": map_tumor_location(row.get('肿瘤位置0=贲门、胃底，1=胃体，2=胃角、胃窦，3=全胃')),
            "biomarkers": {
                "cea": safe_float(row.get('CEA')),
                "ca199": safe_float(row.get('CA199')),
                "cea_positive": safe_float(row.get('CEA：0=阴性， 1=阳性')) == 1,
                "ca199_positive": safe_float(row.get('CA199：0=阴性， 1=阳性')) == 1
            },
            "pathology": {
                "type": safe_str(row.get('病理')),
                "differentiation": map_differentiation(row.get('分化程度（1=高分化，2=中分化，3=中-低分化，4=低分化，5=不确定）')),
                "lauren": safe_str(row.get('Lauren分型（1.肠型，2.弥漫型，3混合型，4不确定）')),
                "pT": safe_str(row.get('pT:1=T1（局限在粘膜及粘膜下层），2=T2（肿瘤侵犯肌层及浆膜下层），3=T3（肿瘤侵透浆膜层），4=T4a（侵犯较浅且到达了浆膜层），5=T4b（侵犯较深且到达了邻近组织或脏器）')),
                "pN": safe_str(row.get('N:0=N0，1=N1，2=N2，3=N3a，4=3b')),
                "pM": safe_str(row.get('M：0=没有远处转移，   1=有远处转移')),
                "pStage": safe_str(row.get('pStage(1=I;2=II;3=III,4=IV)'))
            }
        }
        
        clinical_data[patient_id] = data
        
    print(f"Processed {len(clinical_data)} patients.")
    
    # 保存为JSON
    with open(OUTPUT_PATH, 'w', encoding='utf-8') as f:
        json.dump(clinical_data, f, ensure_ascii=False, indent=2)
        
    print(f"Saved to: {OUTPUT_PATH}")

if __name__ == "__main__":
    process_excel()

