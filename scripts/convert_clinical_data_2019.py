import pandas as pd
import json
import os
import numpy as np

# 配置路径
EXCEL_PATH = "/Users/huangyijun/Projects/胃癌T分期/2019年直接手术/2019.xlsx"
OUTPUT_PATH = "/Users/huangyijun/Projects/胃癌T分期/gastric-scan-next/data/clinical_data_2019.json"

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

def map_t_stage_2019(val):
    try:
        v = int(val)
        mapping = {
            0: "Normal",
            1: "T1",
            2: "T2",
            3: "T3",
            4: "T4a",
            5: "T4b"
        }
        return mapping.get(v, "Unknown")
    except:
        return "Unknown"

def map_n_stage_2019(val):
    try:
        v = int(val)
        mapping = {
            0: "N0",
            1: "N1",  # 1-6 nodes
            2: "N2",  # 7-15 nodes
            3: "N3",  # 16+ nodes
            4: "N+"   # Several nodes
        }
        return mapping.get(v, "Unknown")
    except:
        return "Unknown"

def process_excel_2019():
    print(f"Reading Excel: {EXCEL_PATH}")
    
    df = pd.read_excel(EXCEL_PATH)
    print(f"Total rows: {len(df)}")
    
    clinical_data = {}
    
    for _, row in df.iterrows():
        # 获取ID
        patient_id = safe_str(row.get('ID'))
        if not patient_id:
            continue
        
        # 构建数据对象
        data = {
            "age": safe_float(row.get('年龄：岁')),
            "sex": map_sex_2019(row.get('性别： 0=女， 1=男')),
            "tumorSize": {
                "length": safe_float(row.get('长径：cm')),
                "thickness": safe_float(row.get('厚径：cm'))
            },
            "location": map_tumor_location_2019(row.get('超声位置分四类：0=贲门+胃底；1=胃体+胃角；2=胃窦+幽门；3=多部位')),
            "biomarkers": {
                "cea": None,  # 2019年数据中没有CEA数值，只有阳性/阴性
                "ca199": None,  # 2019年数据中没有CA199数值，只有阳性/阴性
                "cea_positive": safe_float(row.get('CEA：0=阴性， 1=阳性')) == 1,
                "ca199_positive": safe_float(row.get('CA199:  0=阴性，  1=阳性 ')) == 1
            },
            "pathology": {
                "type": safe_str(row.get('病理')),
                "differentiation": map_differentiation(row.get('分化程度（1=高分化，2=中分化，3=中-低分化，4=低分化，5=不确定）')),
                "lauren": safe_str(row.get('Lauren分型（1.肠型，2.弥漫型，3混合型，4不确定）')),
                "pT": map_t_stage_2019(row.get('T:0=正常，1=T1（局限在粘膜及粘膜下层），2=T2（肿瘤侵犯肌层及浆膜下层），3=T3（肿瘤侵透浆膜层），4=T4a（侵犯较浅且到达了浆膜层），5=T4b（侵犯较深且到达了邻近组织或脏器）')),
                "pN": map_n_stage_2019(row.get('N:0=阴性，1=1-6个淋巴结转移，2=7-15个淋巴结转移，3=16个以上淋巴结转移，4=数个淋巴结')),
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
    process_excel_2019()

