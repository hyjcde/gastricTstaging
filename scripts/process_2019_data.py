"""
处理2019年直接手术数据：
1. 将NII文件转换为JPG
2. 生成LabelMe JSON标注（如果有标注数据）
3. 生成overlay图像
4. 保存到Gastric_Cancer_Dataset_2019目录
"""

import os
import json
import numpy as np
import nibabel as nib
import cv2
from PIL import Image
import glob
import re

PROJECT_ROOT = "/Users/huangyijun/Projects/胃癌T分期"
SOURCE_ROOT = os.path.join(PROJECT_ROOT, "2019年直接手术")
OUTPUT_ROOT = os.path.join(PROJECT_ROOT, "Gastric_Cancer_Dataset_2019")

# 创建输出目录
for subdir in ['images', 'overlays', 'annotations', 'lymph_node_analysis']:
    os.makedirs(os.path.join(OUTPUT_ROOT, subdir), exist_ok=True)

def process_nii_to_jpg(nii_path, output_path):
    """将NII文件转换为JPG"""
    try:
        nii_img = nib.load(nii_path)
        data = nii_img.get_fdata()
        
        # 获取中间切片（通常是最大尺寸的切片）
        if len(data.shape) == 3:
            mid_slice = data.shape[2] // 2
            img_2d = data[:, :, mid_slice]
        elif len(data.shape) == 2:
            img_2d = data
        else:
            print(f"Unsupported shape: {data.shape} for {nii_path}")
            return False
        
        # 归一化到0-255
        img_2d = np.nan_to_num(img_2d)
        img_min = np.min(img_2d)
        img_max = np.max(img_2d)
        if img_max > img_min:
            img_2d = ((img_2d - img_min) / (img_max - img_min) * 255).astype(np.uint8)
        else:
            img_2d = np.zeros_like(img_2d, dtype=np.uint8)
        
        # 转换为RGB
        img_rgb = cv2.cvtColor(img_2d, cv2.COLOR_GRAY2RGB)
        
        # 保存为JPG
        cv2.imwrite(output_path, cv2.cvtColor(img_rgb, cv2.COLOR_RGB2BGR))
        return True
    except Exception as e:
        print(f"Error processing {nii_path}: {e}")
        return False

def extract_patient_id_from_filename(filename):
    """从文件名提取病人ID
    格式: 1-1-2(13).nii -> 提取 "1" 作为病人ID
    或者: 1-100-1(15).nii -> 提取 "1-100" 或 "100"
    """
    # 移除扩展名
    name = filename.replace('.nii', '').replace('.jpg', '')
    
    # 提取第一个数字作为主要ID
    match = re.match(r'^(\d+)', name)
    if match:
        return match.group(1)
    
    # 如果没有匹配，返回整个名称（去除括号内容）
    return re.sub(r'\([^)]*\)', '', name).strip()

def process_2019_data():
    """处理2019年的NII数据"""
    nii1_dir = os.path.join(SOURCE_ROOT, "NII1")
    nii2_dir = os.path.join(SOURCE_ROOT, "NII2")
    
    processed_count = 0
    
    # 处理NII1
    if os.path.exists(nii1_dir):
        nii_files = glob.glob(os.path.join(nii1_dir, "*.nii"))
        print(f"Found {len(nii_files)} files in NII1")
        
        for nii_path in nii_files:
            filename = os.path.basename(nii_path)
            patient_id = extract_patient_id_from_filename(filename)
            
            # 生成输出文件名：Surgery_2019_{patient_id}_{original_name}.jpg
            base_name = filename.replace('.nii', '')
            output_filename = f"Surgery_2019_{base_name}.jpg"
            output_path = os.path.join(OUTPUT_ROOT, 'images', output_filename)
            
            if process_nii_to_jpg(nii_path, output_path):
                processed_count += 1
                if processed_count % 50 == 0:
                    print(f"Processed {processed_count} files...")
    
    # 处理NII2
    if os.path.exists(nii2_dir):
        nii_files = glob.glob(os.path.join(nii2_dir, "*.nii"))
        print(f"Found {len(nii_files)} files in NII2")
        
        for nii_path in nii_files:
            filename = os.path.basename(nii_path)
            patient_id = extract_patient_id_from_filename(filename)
            
            # 生成输出文件名
            base_name = filename.replace('.nii', '')
            output_filename = f"Surgery_2019_{base_name}.jpg"
            output_path = os.path.join(OUTPUT_ROOT, 'images', output_filename)
            
            if process_nii_to_jpg(nii_path, output_path):
                processed_count += 1
                if processed_count % 50 == 0:
                    print(f"Processed {processed_count} files...")
    
    print(f"\nTotal processed: {processed_count} files")
    print(f"Output directory: {OUTPUT_ROOT}")

if __name__ == "__main__":
    process_2019_data()

