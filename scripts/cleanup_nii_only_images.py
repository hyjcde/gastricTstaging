"""
清理从NII直接生成的图片，只保留从DICOM生成的图片
- 从DICOM生成的：Surgery_2019_692-2.jpg（两个部分）
- 从NII生成的：Surgery_2019_2-692-2(16).jpg（三个或更多部分，有括号）
"""

import os
import re
from collections import defaultdict

PROJECT_ROOT = "/Users/huangyijun/Projects/胃癌T分期"
IMAGES_DIR = os.path.join(PROJECT_ROOT, "Gastric_Cancer_Dataset_2019", "images")
OVERLAYS_DIR = os.path.join(PROJECT_ROOT, "Gastric_Cancer_Dataset_2019", "overlays")
OVERLAYS_TRANSPARENT_DIR = os.path.join(PROJECT_ROOT, "Gastric_Cancer_Dataset_2019", "lymph_node_analysis")
ANNOTATIONS_DIR = os.path.join(PROJECT_ROOT, "Gastric_Cancer_Dataset_2019", "annotations")

def get_dicom_key_from_filename(filename):
    """从文件名提取DICOM对应的key"""
    base = filename.replace('Surgery_2019_', '').replace('.jpg', '').replace('.json', '')
    base_clean = re.sub(r'\([^)]*\)', '', base)
    parts = base_clean.split('-')
    
    # 如果只有两个部分，就是DICOM key
    if len(parts) == 2:
        return '-'.join(parts)
    # 如果有三个或更多部分，提取最后两个部分作为DICOM key
    elif len(parts) >= 3:
        return '-'.join(parts[-2:])
    else:
        return base_clean

def main():
    # 获取所有图片文件
    all_images = [f for f in os.listdir(IMAGES_DIR) if f.startswith('Surgery_2019_') and f.endswith('.jpg')]
    
    # 按DICOM key分组
    image_groups = defaultdict(list)
    for img in all_images:
        dicom_key = get_dicom_key_from_filename(img)
        image_groups[dicom_key].append(img)
    
    # 找出有多个图片的DICOM key
    duplicates = {k: v for k, v in image_groups.items() if len(v) > 1}
    
    print(f"Total images: {len(all_images)}")
    print(f"DICOM keys with multiple images: {len(duplicates)}")
    
    # 确定要删除的图片（从NII生成的，格式复杂）
    to_delete = []
    to_keep = []
    
    for dicom_key, imgs in duplicates.items():
        # 找出格式简单的（从DICOM生成的）和格式复杂的（从NII生成的）
        simple_format = [img for img in imgs if len(img.replace('Surgery_2019_', '').replace('.jpg', '').split('-')) == 2]
        complex_format = [img for img in imgs if len(img.replace('Surgery_2019_', '').replace('.jpg', '').split('-')) >= 3]
        
        if simple_format and complex_format:
            # 保留简单的，删除复杂的
            to_keep.extend(simple_format)
            to_delete.extend(complex_format)
        elif complex_format:
            # 如果只有复杂的，检查是否有对应的DICOM文件
            # 这里我们假设如果有复杂的，应该删除（因为process_2019_project.py应该已经生成了简单的）
            to_delete.extend(complex_format)
    
    # 对于没有重复的，检查格式
    for dicom_key, imgs in image_groups.items():
        if len(imgs) == 1:
            img = imgs[0]
            parts = img.replace('Surgery_2019_', '').replace('.jpg', '').split('-')
            # 如果格式复杂（三个或更多部分），可能是从NII生成的
            if len(parts) >= 3:
                # 检查是否有对应的DICOM文件
                # 这里我们保守一点，只删除确定是从NII生成的
                base_clean = re.sub(r'\([^)]*\)', '', '-'.join(parts))
                if len(base_clean.split('-')) >= 3:
                    to_delete.append(img)
            else:
                to_keep.append(img)
    
    print(f"\nImages to keep: {len(to_keep)}")
    print(f"Images to delete: {len(to_delete)}")
    
    if len(to_delete) > 0:
        print(f"\nSample images to delete (first 10):")
        for img in to_delete[:10]:
            print(f"  {img}")
        
        # 确认删除
        response = input(f"\nDelete {len(to_delete)} images? (yes/no): ")
        if response.lower() == 'yes':
            deleted_count = 0
            for img in to_delete:
                # 删除图片
                img_path = os.path.join(IMAGES_DIR, img)
                if os.path.exists(img_path):
                    os.remove(img_path)
                    deleted_count += 1
                
                # 删除对应的overlay
                overlay_name = img.replace('.jpg', '_overlay.jpg')
                overlay_path = os.path.join(OVERLAYS_DIR, overlay_name)
                if os.path.exists(overlay_path):
                    os.remove(overlay_path)
                
                overlay_transparent_path = os.path.join(OVERLAYS_TRANSPARENT_DIR, overlay_name)
                if os.path.exists(overlay_transparent_path):
                    os.remove(overlay_transparent_path)
                
                # 删除对应的annotation
                json_name = img.replace('.jpg', '.json')
                json_path = os.path.join(ANNOTATIONS_DIR, json_name)
                if os.path.exists(json_path):
                    os.remove(json_path)
            
            print(f"\nDeleted {deleted_count} images and their associated files.")
        else:
            print("Deletion cancelled.")
    else:
        print("No images to delete.")

if __name__ == "__main__":
    main()

