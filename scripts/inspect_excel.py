import pandas as pd

excel_path = "/Users/huangyijun/Projects/胃癌T分期/2025胃癌临床整理.xlsx"

try:
    # 读取Excel文件
    df = pd.read_excel(excel_path)
    
    # 打印列名
    print("Columns:")
    print(df.columns.tolist())
    
    # 打印前3行数据
    print("\nFirst 3 rows:")
    print(df.head(3))
    
    # 检查是否有可能是ID的列
    print("\nPotential ID columns:")
    for col in df.columns:
        if "ID" in str(col).upper() or "号" in str(col) or "名" in str(col):
            print(f"- {col}")
            
except Exception as e:
    print(f"Error reading Excel: {e}")

