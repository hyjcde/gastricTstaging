#!/usr/bin/env python3
"""
从现有的JSON标注文件重新生成overlay图像（中间透明样式）
并保存到 lymph_node_analysis 文件夹
"""

import os
import json
import cv2
import numpy as np
from PIL import Image
import glob

# Configuration
PROJECT_ROOT = "/Users/huangyijun/Projects/胃癌T分期"
DATASET_ORIGINAL = os.path.join(PROJECT_ROOT, "Gastric_Cancer_Dataset")
DATASET_CROPPED = os.path.join(PROJECT_ROOT, "Gastric_Cancer_Dataset_Cropped")

def ensure_dir(path):
    if not os.path.exists(path):
        os.makedirs(path)

def create_mask_from_shapes(shapes, height, width):
    """
    从LabelMe JSON的shapes创建mask
    """
    mask = np.zeros((height, width), dtype=np.uint8)
    
    for shape in shapes:
        if shape.get('shape_type') == 'polygon':
            points = shape.get('points', [])
            if len(points) >= 3:
                # 转换为numpy数组
                pts = np.array(points, dtype=np.int32)
                # 填充多边形
                cv2.fillPoly(mask, [pts], 255)
    
    return mask

def create_transparent_overlay(img_rgb, mask_2d):
    """
    创建中间透明的overlay，只保留边缘轮廓
    """
    img_bgr = cv2.cvtColor(img_rgb, cv2.COLOR_RGB2BGR)
    overlay_bgr = img_bgr.copy()
    
    # 只绘制边缘轮廓，中间保持透明（不填充）
    mask_uint8 = mask_2d.astype(np.uint8)
    contours, _ = cv2.findContours(mask_uint8, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    # 绘制绿色边缘，线宽2像素
    cv2.drawContours(overlay_bgr, contours, -1, (0, 255, 0), 2)
    
    return overlay_bgr

def process_dataset(dataset_path, dataset_name):
    """
    处理单个数据集，从JSON标注重新生成overlay到新文件夹
    """
    print(f"\n{'='*60}")
    print(f"处理数据集: {dataset_name}")
    print(f"路径: {dataset_path}")
    print(f"{'='*60}")
    
    images_dir = os.path.join(dataset_path, "images")
    annotations_dir = os.path.join(dataset_path, "annotations")
    output_overlay_dir = os.path.join(dataset_path, "lymph_node_analysis")
    
    if not os.path.exists(images_dir):
        print(f"警告: 图像目录不存在: {images_dir}")
        return 0
    
    if not os.path.exists(annotations_dir):
        print(f"警告: 标注目录不存在: {annotations_dir}")
        return 0
    
    ensure_dir(output_overlay_dir)
    
    # 获取所有JSON标注文件
    json_files = glob.glob(os.path.join(annotations_dir, "*.json"))
    total_files = len(json_files)
    print(f"找到 {total_files} 个标注文件")
    
    if total_files == 0:
        print("没有找到标注文件，跳过此数据集")
        return 0
    
    processed_count = 0
    skipped_count = 0
    error_count = 0
    
    for json_path in json_files:
        try:
            # 获取基础文件名
            base_name = os.path.splitext(os.path.basename(json_path))[0]
            
            # 查找对应的图像文件（可能是.jpg）
            img_path = os.path.join(images_dir, base_name + ".jpg")
            
            if not os.path.exists(img_path):
                skipped_count += 1
                continue
            
            # 读取JSON标注
            with open(json_path, 'r', encoding='utf-8') as f:
                annotation = json.load(f)
            
            # 获取图像尺寸
            height = annotation.get('imageHeight', 0)
            width = annotation.get('imageWidth', 0)
            shapes = annotation.get('shapes', [])
            
            if height == 0 or width == 0:
                # 从图像文件读取尺寸
                img = Image.open(img_path)
                width, height = img.size
            
            # 从shapes创建mask
            mask = create_mask_from_shapes(shapes, height, width)
            
            if mask.sum() == 0:
                # 如果没有有效的mask，跳过
                skipped_count += 1
                continue
            
            # 读取图像
            img_rgb = np.array(Image.open(img_path))
            
            # 确保图像尺寸匹配
            if img_rgb.shape[:2] != (height, width):
                # 调整mask尺寸
                mask = cv2.resize(mask, (width, height), interpolation=cv2.INTER_NEAREST)
            
            # 创建透明overlay
            overlay_bgr = create_transparent_overlay(img_rgb, mask)
            
            # 保存overlay到新文件夹
            overlay_filename = base_name + "_overlay.jpg"
            overlay_path = os.path.join(output_overlay_dir, overlay_filename)
            cv2.imwrite(overlay_path, overlay_bgr)
            
            processed_count += 1
            if processed_count % 100 == 0:
                print(f"  已处理: {processed_count}/{total_files}")
                
        except Exception as e:
            print(f"  错误: 处理 {json_path} 时出错: {e}")
            error_count += 1
    
    print(f"\n完成: 成功处理 {processed_count} 个文件")
    print(f"      跳过 {skipped_count} 个文件")
    print(f"      错误 {error_count} 个文件")
    
    return processed_count

def main():
    """
    主函数：重新生成overlay到新文件夹
    """
    print("=" * 60)
    print("重新生成Overlay图像（中间透明样式）")
    print("从JSON标注文件生成，保存到 lymph_node_analysis 文件夹")
    print("=" * 60)
    
    total_processed = 0
    
    # 处理原始数据集
    if os.path.exists(DATASET_ORIGINAL):
        count = process_dataset(DATASET_ORIGINAL, "Gastric_Cancer_Dataset (Original)")
        total_processed += count
    else:
        print(f"\n警告: 原始数据集不存在: {DATASET_ORIGINAL}")
    
    # 处理裁剪数据集
    if os.path.exists(DATASET_CROPPED):
        count = process_dataset(DATASET_CROPPED, "Gastric_Cancer_Dataset_Cropped")
        total_processed += count
    else:
        print(f"\n警告: 裁剪数据集不存在: {DATASET_CROPPED}")
    
    print(f"\n{'='*60}")
    print(f"全部完成！总共处理: {total_processed} 个文件")
    print(f"{'='*60}")

if __name__ == "__main__":
    main()

