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

def ensure_dir(path):
    if not os.path.exists(path):
        os.makedirs(path)

def numpy_to_base64(img_arr):
    """
    Convert numpy array (RGB) to base64 string for LabelMe.
    """
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
    """
    Extract contours from a binary mask.
    Returns a list of shapes for LabelMe.
    """
    shapes = []
    mask = mask.astype(np.uint8)
    
    # Find contours
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

def process_files(src_dir, out_dir):
    annotations_dir = os.path.join(out_dir, "annotations")
    image_dir = os.path.join(out_dir, "image") # Renamed to image
    overlay_dir = os.path.join(out_dir, "overlay")
    
    ensure_dir(annotations_dir)
    ensure_dir(image_dir)
    ensure_dir(overlay_dir)
    
    files = os.listdir(src_dir)
    dcm_files = [f for f in files if f.lower().endswith('.dcm') and not f.startswith('._')]
    
    print(f"Processing {src_dir} -> {out_dir}")
    print(f"Found {len(dcm_files)} DICOM files.")
    
    count = 0
    for dcm_file in dcm_files:
        base_name = os.path.splitext(dcm_file)[0]
        nii_file = base_name + ".nii.gz"
        
        dcm_path = os.path.join(src_dir, dcm_file)
        nii_path = os.path.join(src_dir, nii_file)
        
        if not os.path.exists(nii_path):
            # print(f"Warning: No corresponding NIfTI file for {dcm_file}. Skipping.")
            continue
            
        try:
            # Copy original DICOM to image folder
            shutil.copy2(dcm_path, os.path.join(image_dir, dcm_file))

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
            
            # 2. Read NIfTI
            nii = nib.load(nii_path)
            nii_data = nii.get_fdata()
            mask_2d = np.squeeze(nii_data)
            
            if mask_2d.shape != (height, width):
                if mask_2d.T.shape == (height, width):
                    mask_2d = mask_2d.T
                else:
                    print(f"Error: Shape mismatch for {dcm_file}. DICOM: {img_rgb.shape}, NIfTI: {mask_2d.shape}. Skipping.")
                    continue
            
            # 3. Save Image (JPG)
            jpg_filename = base_name + ".jpg"
            jpg_path = os.path.join(image_dir, jpg_filename)
            Image.fromarray(img_rgb).save(jpg_path)
            
            # 4. Create LabelMe JSON
            shapes = get_contours_from_mask(mask_2d)
            img_data_b64 = numpy_to_base64(img_rgb)
            
            # Use relative path for imagePath
            relative_image_path = f"../image/{jpg_filename}"
            
            json_content = create_labelme_json(relative_image_path, img_data_b64, height, width, shapes)
            json_filename = base_name + ".json"
            json_path = os.path.join(annotations_dir, json_filename)
            
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
            
            overlay_path = os.path.join(overlay_dir, base_name + "_overlay.jpg")
            cv2.imwrite(overlay_path, overlay_bgr)
            
            count += 1
            
        except Exception as e:
            print(f"Error processing {dcm_file}: {e}")
            
    print(f"Completed {src_dir}: Processed {count} files.")

if __name__ == "__main__":
    base_dir = "放化疗"
    # List all subdirectories that end with 'C' (e.g., 1M C, 2M C...)
    subdirs = [d for d in os.listdir(base_dir) if os.path.isdir(os.path.join(base_dir, d)) and d.endswith('C')]
    subdirs.sort()
    
    print(f"Found directories: {subdirs}")
    
    for subdir in subdirs:
        src_directory = os.path.join(base_dir, subdir)
        output_directory = os.path.join(base_dir, subdir, "LabelMe_Dataset")
        
        # Skip if already exists? Or overwrite? Let's overwrite to be safe/update.
        process_files(src_directory, output_directory)
        
    print("All conversions complete.")

