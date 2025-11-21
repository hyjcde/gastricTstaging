import os
import cv2
import numpy as np
import math

def create_overlay_grid(base_dir, output_file="overlay_summary.jpg", grid_cols=5, max_images=None):
    """
    Creates a grid summary of overlay images from all subdirectories.
    """
    overlay_images = []
    
    # Walk through all directories to find overlay images
    for root, dirs, files in os.walk(base_dir):
        if "overlay" in root:
            for file in files:
                if file.endswith("_overlay.jpg") and not file.startswith("._"):
                    overlay_images.append(os.path.join(root, file))
    
    if not overlay_images:
        print("No overlay images found.")
        return

    print(f"Found {len(overlay_images)} overlay images.")
    
    if max_images:
        overlay_images = overlay_images[:max_images]
        
    # Read images to determine size (assume all are roughly same size or resize)
    # We'll resize to a thumbnail size for the grid
    thumb_size = (300, 300)
    
    thumbnails = []
    for img_path in overlay_images:
        img = cv2.imread(img_path)
        if img is not None:
            # Resize maintaining aspect ratio
            h, w = img.shape[:2]
            scale = min(thumb_size[0]/w, thumb_size[1]/h)
            new_w = int(w * scale)
            new_h = int(h * scale)
            resized = cv2.resize(img, (new_w, new_h))
            
            # Pad to make it square thumb_size
            canvas = np.zeros((thumb_size[1], thumb_size[0], 3), dtype=np.uint8)
            y_offset = (thumb_size[1] - new_h) // 2
            x_offset = (thumb_size[0] - new_w) // 2
            canvas[y_offset:y_offset+new_h, x_offset:x_offset+new_w] = resized
            
            # Add filename text
            filename = os.path.basename(img_path).replace("_overlay.jpg", "")
            # Shorten filename if too long
            if len(filename) > 20:
                filename = filename[:17] + "..."
                
            cv2.putText(canvas, filename, (10, 20), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1, cv2.LINE_AA)
            
            thumbnails.append(canvas)
            
    if not thumbnails:
        return

    # Create grid
    n_images = len(thumbnails)
    grid_rows = math.ceil(n_images / grid_cols)
    
    grid_h = grid_rows * thumb_size[1]
    grid_w = grid_cols * thumb_size[0]
    
    grid_image = np.zeros((grid_h, grid_w, 3), dtype=np.uint8)
    
    for idx, thumb in enumerate(thumbnails):
        row = idx // grid_cols
        col = idx % grid_cols
        
        y = row * thumb_size[1]
        x = col * thumb_size[0]
        
        grid_image[y:y+thumb_size[1], x:x+thumb_size[0]] = thumb
        
    cv2.imwrite(output_file, grid_image)
    print(f"Saved overlay summary to {output_file}")

if __name__ == "__main__":
    base_directory = "放化疗"
    create_overlay_grid(base_directory, output_file="放化疗/overlay_summary.jpg")

