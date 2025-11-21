import os
import cv2
import glob
import numpy as np

# Configuration
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DATASET_ROOT = os.path.join(PROJECT_ROOT, "Gastric_Cancer_Dataset")
OUTPUT_ROOT = os.path.join(PROJECT_ROOT, "Gastric_Cancer_Dataset_Cropped")

# Crop Coordinates (Provided by User)
# x=115, y=118, w=1051, h=757
CROP_X1 = 115
CROP_Y1 = 118
CROP_W = 1051
CROP_H = 757
CROP_X2 = CROP_X1 + CROP_W
CROP_Y2 = CROP_Y1 + CROP_H

def ensure_dir(path):
    if not os.path.exists(path):
        os.makedirs(path)

def main():
    print(f"Starting Batch Crop...")
    print(f"ROI: x={CROP_X1}, y={CROP_Y1}, w={CROP_W}, h={CROP_H}")
    print(f"Output Directory: {OUTPUT_ROOT}")
    
    ensure_dir(os.path.join(OUTPUT_ROOT, "images"))
    ensure_dir(os.path.join(OUTPUT_ROOT, "overlays"))
    ensure_dir(os.path.join(OUTPUT_ROOT, "annotations"))

    # Get all overlays
    overlay_files = glob.glob(os.path.join(DATASET_ROOT, "overlays", "*.jpg"))
    total_files = len(overlay_files)
    print(f"Found {total_files} sets of images to process.")
    
    processed_count = 0
    skipped_count = 0
    
    for overlay_path in overlay_files:
        filename = os.path.basename(overlay_path)
        
        # 1. Process Overlay
        img_overlay = cv2.imread(overlay_path)
        if img_overlay is None:
            print(f"Warning: Could not read {overlay_path}")
            skipped_count += 1
            continue
            
        # Check if crop is within bounds
        h, w = img_overlay.shape[:2]
        if CROP_X2 > w or CROP_Y2 > h:
            # If image is smaller than crop, we might need adjustment or skip
            # For now, we just clamp
            x2 = min(CROP_X2, w)
            y2 = min(CROP_Y2, h)
            x1 = min(CROP_X1, x2)
            y1 = min(CROP_Y1, y2)
        else:
            x1, y1, x2, y2 = CROP_X1, CROP_Y1, CROP_X2, CROP_Y2
            
        cropped_overlay = img_overlay[y1:y2, x1:x2]
        cv2.imwrite(os.path.join(OUTPUT_ROOT, "overlays", filename), cropped_overlay)
        
        # 2. Process Original Image
        original_filename = filename.replace("_overlay.jpg", ".jpg")
        original_path = os.path.join(DATASET_ROOT, "images", original_filename)
        
        if os.path.exists(original_path):
            img_orig = cv2.imread(original_path)
            if img_orig is not None:
                # Resize check? Assuming same size
                if img_orig.shape[:2] != img_overlay.shape[:2]:
                    # If dimensions differ, we skip or warn. 
                    # Usually in this dataset they are aligned.
                    pass
                
                cropped_orig = img_orig[y1:y2, x1:x2]
                cv2.imwrite(os.path.join(OUTPUT_ROOT, "images", original_filename), cropped_orig)
        
        # 3. Process Annotations (JSON) - Optional but recommended
        # We need to update coordinates in the json if we want to use them later
        # But since we have masks (overlays), maybe we don't use jsons?
        # Let's try to copy and shift points if json exists.
        json_filename = filename.replace("_overlay.jpg", ".json")
        json_path = os.path.join(DATASET_ROOT, "annotations", json_filename)
        
        if os.path.exists(json_path):
            import json
            with open(json_path, 'r') as f:
                data = json.load(f)
            
            # Shift shapes
            new_shapes = []
            for shape in data.get('shapes', []):
                new_points = []
                for p in shape['points']:
                    nx = p[0] - x1
                    ny = p[1] - y1
                    # Clip to new boundaries? Or just let them be
                    new_points.append([nx, ny])
                shape['points'] = new_points
                new_shapes.append(shape)
            
            data['shapes'] = new_shapes
            data['imageHeight'] = y2 - y1
            data['imageWidth'] = x2 - x1
            data['imagePath'] = f"../images/{original_filename}"
            data['imageData'] = None # Clear base64 to save space
            
            with open(os.path.join(OUTPUT_ROOT, "annotations", json_filename), 'w') as f:
                json.dump(data, f, indent=2)

        processed_count += 1
        if processed_count % 100 == 0:
            print(f"Processed {processed_count}/{total_files}...")

    print(f"Done. Processed: {processed_count}, Skipped: {skipped_count}")
    print(f"Results saved to: {OUTPUT_ROOT}")

if __name__ == "__main__":
    main()

