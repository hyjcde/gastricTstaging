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

# Configuration
PROJECT_ROOT = "/Users/huangyijun/Projects/胃癌T分期"
OUTPUT_ROOT = os.path.join(PROJECT_ROOT, "Gastric_Cancer_Dataset")
SCRIPTS_DIR = os.path.join(PROJECT_ROOT, "scripts")

DIRS_TO_PROCESS = [
    {
        "path": os.path.join(PROJECT_ROOT, "放化疗"),
        "group": "Chemo",
        "suffix_filter": "C" # Folders ending with 'C' like '1M C'
    },
    {
        "path": os.path.join(PROJECT_ROOT, "直接手术"),
        "group": "Surgery",
        "suffix_filter": "M" # Folders ending with 'M' like '1M' (strict check needed)
    }
]

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

def process_single_file(dcm_path, nii_path, out_dirs, prefix):
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
        
        # 2. Read NIfTI
        nii = nib.load(nii_path)
        nii_data = nii.get_fdata()
        mask_2d = np.squeeze(nii_data)
        
        # Transpose fix
        if mask_2d.shape != (height, width):
            if mask_2d.T.shape == (height, width):
                mask_2d = mask_2d.T
            else:
                return False, f"Shape mismatch: DICOM {img_rgb.shape} vs NIfTI {mask_2d.shape}"

        # Define filenames with prefix
        base_name = os.path.splitext(os.path.basename(dcm_path))[0]
        new_base_name = f"{prefix}_{base_name}"
        
        jpg_filename = new_base_name + ".jpg"
        dcm_filename = new_base_name + ".dcm"
        json_filename = new_base_name + ".json"
        overlay_filename = new_base_name + "_overlay.jpg"
        
        # Paths
        jpg_path = os.path.join(out_dirs['images'], jpg_filename)
        dcm_out_path = os.path.join(out_dirs['images'], dcm_filename)
        json_path = os.path.join(out_dirs['annotations'], json_filename)
        overlay_path = os.path.join(out_dirs['overlays'], overlay_filename)
        
        # 3. Save Image (JPG) & Copy DICOM
        Image.fromarray(img_rgb).save(jpg_path)
        shutil.copy2(dcm_path, dcm_out_path)
        
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
        'overlays': os.path.join(OUTPUT_ROOT, "overlays")
    }
    for d in out_dirs.values():
        ensure_dir(d)
        
    ensure_dir(SCRIPTS_DIR)
    
    # 2. Process Data
    total_processed = 0
    total_errors = 0
    
    for source in DIRS_TO_PROCESS:
        base_path = source['path']
        group = source['group']
        suffix = source['suffix_filter']
        
        if not os.path.exists(base_path):
            print(f"Skipping missing directory: {base_path}")
            continue
            
        subdirs = [d for d in os.listdir(base_path) if os.path.isdir(os.path.join(base_path, d))]
        
        for subdir in subdirs:
            # Filter logic
            # Chemo: "1M C" -> ends with 'C'
            # Surgery: "1M" -> ends with 'M' (or digit+M)
            
            should_process = False
            phase = ""
            
            if group == "Chemo":
                if subdir.endswith(" C"):
                    should_process = True
                    phase = subdir.replace(" ", "") # "1M C" -> "1MC"
            elif group == "Surgery":
                # Check if it looks like "1M", "2M" etc.
                if subdir.endswith("M") and subdir[:-1].isdigit():
                    should_process = True
                    phase = subdir
            
            if not should_process:
                continue
                
            print(f"Processing {group} - {subdir}...")
            
            src_dir = os.path.join(base_path, subdir)
            files = os.listdir(src_dir)
            dcm_files = [f for f in files if f.lower().endswith('.dcm') and not f.startswith('._')]
            
            for dcm_file in dcm_files:
                base_name = os.path.splitext(dcm_file)[0]
                nii_file = base_name + ".nii.gz"
                dcm_path = os.path.join(src_dir, dcm_file)
                nii_path = os.path.join(src_dir, nii_file)
                
                if not os.path.exists(nii_path):
                    continue
                
                # Prefix: Group_Phase_Filename
                # e.g. Chemo_1MC_12345
                prefix = f"{group}_{phase}"
                
                success, msg = process_single_file(dcm_path, nii_path, out_dirs, prefix)
                
                if success:
                    total_processed += 1
                else:
                    print(f"Error {dcm_file}: {msg}")
                    total_errors += 1
                    
    print(f"Processing Complete. Total: {total_processed}, Errors: {total_errors}")
    
    # 3. Move Scripts
    print("Moving scripts...")
    scripts_to_move = ["convert_data.py", "batch_convert.py", "visualize_overlays.py", "process_project.py"]
    for script in scripts_to_move:
        if os.path.exists(script):
            shutil.move(script, os.path.join(SCRIPTS_DIR, script))
            print(f"Moved {script} to {SCRIPTS_DIR}")
            
    # 4. Generate Summary for new dataset
    print("Generating summary visualization...")
    # We can reuse the logic from visualize_overlays but point to the new dir
    # Or just call it via os.system if we moved it? 
    # Better to just inline a simple summary generator or call the moved script.
    # Let's call the moved script logic if possible, but it's easier to just run a quick summary here.
    
    # Simple summary
    overlay_files = glob.glob(os.path.join(out_dirs['overlays'], "*.jpg"))
    if overlay_files:
        overlay_files = overlay_files[:100] # Limit to 100 for summary
        thumbnails = []
        thumb_size = (100, 100)
        for img_path in overlay_files:
            img = cv2.imread(img_path)
            if img is not None:
                img = cv2.resize(img, thumb_size)
                thumbnails.append(img)
        
        if thumbnails:
            # Create grid
            cols = 10
            rows = (len(thumbnails) + cols - 1) // cols
            grid = np.zeros((rows * thumb_size[1], cols * thumb_size[0], 3), dtype=np.uint8)
            for i, thumb in enumerate(thumbnails):
                r = i // cols
                c = i % cols
                grid[r*100:(r+1)*100, c*100:(c+1)*100] = thumb
            
            cv2.imwrite(os.path.join(OUTPUT_ROOT, "dataset_summary.jpg"), grid)
            print("Summary saved.")

if __name__ == "__main__":
    main()

