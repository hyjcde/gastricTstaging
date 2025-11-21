"""
处理2019年新辅助治疗临床数据
参考convert_clinical_data_2019.py，适配2019新辅助治疗的Excel格式
"""

import pandas as pd
import json
import os
import numpy as np

# 配置路径
EXCEL_PATH = "/Users/huangyijun/Projects/胃癌T分期/胃癌勾画新辅助治疗/2019新辅助治疗/2019新辅助.xlsx"
OUTPUT_PATH = "/Users/huangyijun/Projects/胃癌T分期/gastric-scan-next/data/clinical_data_2019_nac.json"

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

def map_sex_2019(val):
    if pd.isna(val):
        return "Unknown"
    try:
        v = float(val)
        return "Male" if v == 1.0 else "Female"
    except:
        val_str = str(val).strip()
        if val_str == "男" or val_str == "1" or val_str == "1.0":
            return "Male"
        elif val_str == "女" or val_str == "0" or val_str == "0.0":
            return "Female"
        else:
            return "Unknown"

def map_tumor_location_2019(val):
    try:
        v = int(val)
        mapping = {
            0: "Cardia/Fundus",
            1: "Body/Angle",
            2: "Antrum/Pylorus",
            3: "Multiple Sites"
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

def process_excel_2019_nac():
    print(f"Reading Excel: {EXCEL_PATH}")
    
    # 读取所有sheet
    xls = pd.ExcelFile(EXCEL_PATH)
    print(f"Found {len(xls.sheet_names)} sheets: {xls.sheet_names}")
    
    # 合并所有sheet的数据
    all_dfs = []
    for sheet_name in xls.sheet_names:
        try:
            df_sheet = pd.read_excel(EXCEL_PATH, sheet_name=sheet_name)
            print(f"  Sheet '{sheet_name}': {len(df_sheet)} rows")
            all_dfs.append(df_sheet)
        except Exception as e:
            print(f"  Error reading sheet '{sheet_name}': {e}")
            continue
    
    # 合并所有数据
    if not all_dfs:
        print("No data found in any sheet!")
        return
    
    df = pd.concat(all_dfs, ignore_index=True)
    print(f"Total rows after merging: {len(df)}")
    
    clinical_data = {}
    
    for _, row in df.iterrows():
        # 获取ID（优先使用ID列，如果没有则使用住院号）
        patient_id = safe_str(row.get('ID')) or safe_str(row.get('住院号'))
        if not patient_id:
            continue
        
        # 构建数据对象
        data = {
            "age": safe_float(row.get('年龄：岁')) or safe_float(row.get('年龄')),
            "sex": map_sex_2019(row.get('性别： 0=女， 1=男')),
            "tumorSize": {
                "length": safe_float(row.get('长径：cm')) or safe_float(row.get('长径')),
                "thickness": safe_float(row.get('厚径：cm')) or safe_float(row.get('厚径'))
            },
            "location": map_tumor_location_2019(row.get('超声位置分四类：0=贲门+胃底；1=胃体+胃角；2=胃窦+幽门；3=多部位')),
            "biomarkers": {
                "cea": None,
                "ca199": None,
                "cea_positive": safe_float(row.get('CEA：0=阴性， 1=阳性')) == 1,
                "ca199_positive": safe_float(row.get('CA199:  0=阴性，  1=阳性 ')) == 1
            },
            "pathology": {
                "type": safe_str(row.get('病理')),
                "differentiation": map_differentiation(row.get('分化程度（1=高分化，2=中分化，3=中-低分化，4=低分化，5=不确定）')),
                "lauren": safe_str(row.get('Lauren分型（1.肠型，2.弥漫型，3混合型，4不确定）')),
                "pT": safe_str(row.get('pT:1=T1（局限在粘膜及粘膜下层），2=T2（肿瘤侵犯肌层及浆膜下层），3=T3（肿瘤侵透浆膜层），4=T4a（侵犯较浅且到达了浆膜层），5=T4b（侵犯较深且到达了邻近组织或脏器）')),
                "pN": safe_str(row.get('N:0=阴性，1=1-6个淋巴结转移，2=7-15个淋巴结转移，3=16个以上淋巴结转移，4=数个淋巴结')),
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
    process_excel_2019_nac()

