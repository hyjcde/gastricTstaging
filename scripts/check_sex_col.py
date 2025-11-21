import pandas as pd

excel_path = "/Users/huangyijun/Projects/胃癌T分期/2025胃癌临床整理.xlsx"

try:
    df = pd.read_excel(excel_path)
    print("Sex column values (first 10):")
    print(df['性别： 0=女， 1=男'].head(10).tolist())
    print("\nUnique values:")
    print(df['性别： 0=女， 1=男'].unique())
except Exception as e:
    print(e)

