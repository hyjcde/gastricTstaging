"""
处理2024年新辅助治疗数据
参考process_2024_project.py，适配2024新辅助治疗的文件结构
DICOM和NII文件在同一个目录下
"""

import os
import json
import base64
import numpy as np
import pydicom
import nibabel as nib
import cv2
from PIL import Image
import io
import shutil
import glob
import re

# Configuration
PROJECT_ROOT = "/Users/huangyijun/Projects/胃癌T分期"
SOURCE_ROOT = os.path.join(PROJECT_ROOT, "胃癌勾画新辅助治疗", "2024新辅助治疗")
OUTPUT_ROOT = os.path.join(PROJECT_ROOT, "Gastric_Cancer_Dataset_2024_nac")

def ensure_dir(path):
    if not os.path.exists(path):
        os.makedirs(path)

def numpy_to_base64(img_arr):
    img = Image.fromarray(img_arr)
    buffer = io.BytesIO()
    img.save(buffer, format="JPEG")
    img_str = base64.b64encode(buffer.getvalue()).decode("utf-8")
    return img_str

def create_labelme_json(image_path, image_data, height, width, shapes):
    return {
        "version": "4.5.6",
        "flags": {},
        "shapes": shapes,
        "imagePath": image_path,
        "imageData": image_data,
        "imageHeight": height,
        "imageWidth": width
    }

def get_contours_from_mask(mask):
    shapes = []
    mask = mask.astype(np.uint8)
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    for contour in contours:
        if cv2.contourArea(contour) < 10:
            continue
        epsilon = 0.001 * cv2.arcLength(contour, True)
        approx = cv2.approxPolyDP(contour, epsilon, True)
        points = approx.squeeze().tolist()
        
        if len(points) < 3:
            continue
        if not isinstance(points[0], list):
             if isinstance(points[0], (int, float)):
                 continue

        shape = {
            "label": "lesion",
            "points": points,
            "group_id": None,
            "shape_type": "polygon",
            "flags": {}
        }
        shapes.append(shape)
    return shapes

def match_dicom_to_nii(dcm_filename, nii_files):
    """
    匹配DICOM文件名到NII文件名
    DICOM格式: "病人ID-序列.dcm" 例如 "1086272-1.dcm" (病人1086272, 序列1)
    NII格式: "病人ID-序列(厚度).nii.gz" 例如 "1086272-1(13).nii.gz" (病人1086272, 序列1)
    """
    # 从DICOM文件名提取: "1086272-1.dcm" -> 病人ID=1086272, 序列=1
    dcm_base = os.path.splitext(dcm_filename)[0]  # "1086272-1"
    dcm_parts = dcm_base.split('-')  # ["1086272", "1"]
    
    if len(dcm_parts) != 2:
        return None
    
    dcm_patient_id = dcm_parts[0]  # "1086272"
    dcm_seq = dcm_parts[1]         # "1"
    
    # 尝试匹配NII文件
    # NII格式: "1086272-1(13).nii.gz" -> 病人ID=1086272, 序列=1
    matches = []
    for nii_file in nii_files:
        # 移除.gz扩展名
        nii_base = nii_file.replace('.gz', '')
        nii_base = os.path.splitext(nii_base)[0]  # "1086272-1(13)"
        nii_base_clean = re.sub(r'\([^)]*\)', '', nii_base)  # "1086272-1"
        nii_parts = nii_base_clean.split('-')  # ["1086272", "1"]
        
        if len(nii_parts) >= 2:
            nii_patient_id = nii_parts[0]  # "1086272"
            nii_seq = nii_parts[1]         # "1"
            
            # 病人ID和序列号都必须匹配
            if nii_patient_id == dcm_patient_id and nii_seq == dcm_seq:
                matches.append(nii_file)
    
    # 返回第一个匹配
    if matches:
        return matches[0]
    
    return None

def extract_patient_id_from_nii(nii_filename):
    """
    从NII文件名提取病人ID
    NII格式: "病人ID-序列(厚度).nii.gz" 例如 "1086272-1(13).nii.gz"
    返回: "1086272"
    """
    nii_base = nii_filename.replace('.gz', '')
    nii_base = os.path.splitext(nii_base)[0]  # "1086272-1(13)"
    nii_base_clean = re.sub(r'\([^)]*\)', '', nii_base)  # "1086272-1"
    nii_parts = nii_base_clean.split('-')  # ["1086272", "1"]
    
    if len(nii_parts) >= 2:
        return nii_parts[0]  # 返回病人ID（第一个部分）
    return None

def process_single_file(dcm_path, nii_path, out_dirs, prefix, queue):
    try:
        # 1. Read DICOM
        ds = pydicom.dcmread(dcm_path)
        pixel_array = ds.pixel_array
        
        if len(pixel_array.shape) == 2:
            img_min = pixel_array.min()
            img_max = pixel_array.max()
            if img_max > img_min:
                img_norm = ((pixel_array - img_min) / (img_max - img_min) * 255).astype(np.uint8)
            else:
                img_norm = np.zeros_like(pixel_array, dtype=np.uint8)
            img_rgb = cv2.cvtColor(img_norm, cv2.COLOR_GRAY2RGB)
        else:
            img_rgb = pixel_array.astype(np.uint8)
        
        height, width = img_rgb.shape[:2]
        
        # 2. Read NIfTI (处理.gz压缩文件)
        # nibabel可以直接读取.gz文件
        nii = nib.load(nii_path)
        nii_data = nii.get_fdata()
        mask_2d = np.squeeze(nii_data)
        
        # Transpose fix
        if mask_2d.shape != (height, width):
            if mask_2d.T.shape == (height, width):
                mask_2d = mask_2d.T
            else:
                return False, f"Shape mismatch: DICOM {img_rgb.shape} vs NIfTI {mask_2d.shape}"

        # 从NII文件名提取病人ID
        nii_filename = os.path.basename(nii_path)
        patient_id = extract_patient_id_from_nii(nii_filename)
        
        # Define filenames with prefix
        # DICOM格式: "1086272-1.dcm" (病人ID-序列)
        # 输出格式: NAC_2024_队列-病人ID-序列.jpg 例如 NAC_2024_1-1086272-1.jpg
        dcm_base = os.path.splitext(os.path.basename(dcm_path))[0]  # "1086272-1"
        dcm_parts = dcm_base.split('-')
        
        if patient_id and len(dcm_parts) == 2:
            # 使用从NII提取的病人ID和队列号
            new_base_name = f"{prefix}_{queue}-{patient_id}-{dcm_parts[1]}"
        else:
            # 回退到原始格式
            new_base_name = f"{prefix}_{dcm_base}"
        
        jpg_filename = new_base_name + ".jpg"
        json_filename = new_base_name + ".json"
        overlay_filename = new_base_name + "_overlay.jpg"
        
        # Paths
        jpg_path = os.path.join(out_dirs['images'], jpg_filename)
        json_path = os.path.join(out_dirs['annotations'], json_filename)
        overlay_path = os.path.join(out_dirs['overlays'], overlay_filename)
        overlay_transparent_path = os.path.join(out_dirs['overlaysTransparent'], overlay_filename)
        
        # 3. Save Image (JPG)
        Image.fromarray(img_rgb).save(jpg_path)
        
        # 4. Create LabelMe JSON
        shapes = get_contours_from_mask(mask_2d)
        img_data_b64 = numpy_to_base64(img_rgb)
        
        # Relative path for LabelMe
        relative_image_path = f"../images/{jpg_filename}"
        
        json_content = create_labelme_json(relative_image_path, img_data_b64, height, width, shapes)
        with open(json_path, 'w') as f:
            json.dump(json_content, f, indent=2)
            
        # 5. Create Overlay (中间透明，只保留边缘)
        img_bgr = cv2.cvtColor(img_rgb, cv2.COLOR_RGB2BGR)
        overlay_bgr = img_bgr.copy()
        
        # 只绘制边缘轮廓，中间保持透明（不填充）
        mask_uint8 = mask_2d.astype(np.uint8)
        contours, _ = cv2.findContours(mask_uint8, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        # 绘制绿色边缘，线宽2像素
        cv2.drawContours(overlay_bgr, contours, -1, (0, 255, 0), 2)
        
        cv2.imwrite(overlay_path, overlay_bgr)
        cv2.imwrite(overlay_transparent_path, overlay_bgr)
        
        return True, "Success"
        
    except Exception as e:
        return False, str(e)

def main():
    # 1. Setup Directories
    print(f"Creating dataset at: {OUTPUT_ROOT}")
    ensure_dir(OUTPUT_ROOT)
    
    out_dirs = {
        'images': os.path.join(OUTPUT_ROOT, "images"),
        'annotations': os.path.join(OUTPUT_ROOT, "annotations"),
        'overlays': os.path.join(OUTPUT_ROOT, "overlays"),
        'overlaysTransparent': os.path.join(OUTPUT_ROOT, "lymph_node_analysis")
    }
    for d in out_dirs.values():
        ensure_dir(d)
    
    # 2. Process Data
    total_processed = 0
    total_errors = 0
    unmatched_dcm = []
    
    # 处理DICOM1+NII1 (队列1)
    dicom1_nii1_dir = os.path.join(SOURCE_ROOT, "DICOM1+NII1")
    dicom2_nii2_dir = os.path.join(SOURCE_ROOT, "DICOM2+NII2")
    
    if os.path.exists(dicom1_nii1_dir):
        print(f"Processing DICOM1+NII1 (Queue 1)...")
        
        # 获取所有DICOM和NII文件（在同一目录下）
        all_files = os.listdir(dicom1_nii1_dir)
        dcm_files = [f for f in all_files if f.lower().endswith('.dcm') and not f.startswith('._')]
        nii_files = [f for f in all_files if f.lower().endswith('.gz') and not f.startswith('._')]
        
        print(f"Found {len(dcm_files)} DICOM files and {len(nii_files)} NII files")
        
        for dcm_file in dcm_files:
            dcm_path = os.path.join(dicom1_nii1_dir, dcm_file)
            
            # 匹配NII文件
            matched_nii = match_dicom_to_nii(dcm_file, nii_files)
            
            if not matched_nii:
                unmatched_dcm.append(dcm_file)
                continue
            
            nii_path = os.path.join(dicom1_nii1_dir, matched_nii)
            
            if not os.path.exists(nii_path):
                unmatched_dcm.append(dcm_file)
                continue
            
            prefix = "NAC_2024"
            
            success, msg = process_single_file(dcm_path, nii_path, out_dirs, prefix, queue="1")
            
            if success:
                total_processed += 1
                if total_processed % 50 == 0:
                    print(f"Processed {total_processed} files...")
            else:
                print(f"Error {dcm_file}: {msg}")
                total_errors += 1
    
    # 处理DICOM2+NII2 (队列2)
    if os.path.exists(dicom2_nii2_dir):
        print(f"\nProcessing DICOM2+NII2 (Queue 2)...")
        
        # 获取所有DICOM和NII文件（在同一目录下）
        all_files = os.listdir(dicom2_nii2_dir)
        dcm_files = [f for f in all_files if f.lower().endswith('.dcm') and not f.startswith('._')]
        nii_files = [f for f in all_files if (f.lower().endswith('.gz') or f.lower().endswith('.nii')) and not f.startswith('._')]
        
        print(f"Found {len(dcm_files)} DICOM files and {len(nii_files)} NII files")
        
        for dcm_file in dcm_files:
            dcm_path = os.path.join(dicom2_nii2_dir, dcm_file)
            
            # 匹配NII文件
            matched_nii = match_dicom_to_nii(dcm_file, nii_files)
            
            if not matched_nii:
                unmatched_dcm.append(dcm_file)
                continue
            
            nii_path = os.path.join(dicom2_nii2_dir, matched_nii)
            
            if not os.path.exists(nii_path):
                unmatched_dcm.append(dcm_file)
                continue
            
            prefix = "NAC_2024"
            
            success, msg = process_single_file(dcm_path, nii_path, out_dirs, prefix, queue="2")
            
            if success:
                total_processed += 1
                if total_processed % 50 == 0:
                    print(f"Processed {total_processed} files...")
            else:
                print(f"Error {dcm_file}: {msg}")
                total_errors += 1
    
    print(f"\nProcessing Complete.")
    print(f"Total processed: {total_processed}")
    print(f"Errors: {total_errors}")
    print(f"Unmatched DICOM files: {len(unmatched_dcm)}")
    if len(unmatched_dcm) > 0 and len(unmatched_dcm) <= 20:
        print(f"Unmatched files: {unmatched_dcm[:20]}")

if __name__ == "__main__":
    main()

