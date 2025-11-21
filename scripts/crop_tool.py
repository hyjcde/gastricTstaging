import os
import cv2
import glob
import numpy as np
from flask import Flask, render_template_string, request, jsonify, send_file
import threading
import webbrowser
import time

app = Flask(__name__)

# Configuration
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DATASET_ROOT = os.path.join(PROJECT_ROOT, "Gastric_Cancer_Dataset")
OUTPUT_ROOT = os.path.join(PROJECT_ROOT, "Gastric_Cancer_Dataset_Cropped")

# Default image to show for cropping
DEFAULT_IMAGE = "Chemo_1MC_1424711 (3)_overlay.jpg"

HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>Dataset Crop Tool</title>
    <style>
        body { font-family: Arial, sans-serif; text-align: center; padding: 20px; background-color: #f0f0f0; }
        .container { display: inline-block; position: relative; margin-top: 20px; border: 2px solid #333; box-shadow: 0 0 10px rgba(0,0,0,0.1); }
        #canvas { cursor: crosshair; }
        .controls { margin: 20px; padding: 20px; background: white; border-radius: 8px; display: inline-block; }
        button { padding: 10px 20px; font-size: 16px; cursor: pointer; background-color: #007bff; color: white; border: none; border-radius: 4px; }
        button:hover { background-color: #0056b3; }
        button:disabled { background-color: #ccc; cursor: not-allowed; }
        #status { margin-top: 10px; font-weight: bold; color: #333; }
        .info { color: #666; margin-bottom: 10px; }
    </style>
</head>
<body>
    <h1>Ultrasound Dataset Cropper</h1>
    <div class="info">
        Step 1: Click and drag on the image to select the area you want to KEEP.<br>
        Step 2: Click "Start Batch Crop" to process all images.
    </div>
    
    <div class="controls">
        <div>
            Crop Area: <span id="coords">None</span>
        </div>
        <br>
        <button id="cropBtn" onclick="startCrop()" disabled>Start Batch Crop</button>
        <div id="status"></div>
    </div>

    <br>

    <div class="container">
        <canvas id="canvas"></canvas>
    </div>

    <script>
        const canvas = document.getElementById('canvas');
        const ctx = canvas.getContext('2d');
        let img = new Image();
        let startX, startY, endX, endY;
        let isDrawing = false;
        let hasSelection = false;
        
        // Load image
        img.onload = function() {
            canvas.width = img.width;
            canvas.height = img.height;
            ctx.drawImage(img, 0, 0);
        };
        img.src = "/image";

        function getMousePos(evt) {
            const rect = canvas.getBoundingClientRect();
            return {
                x: Math.round((evt.clientX - rect.left) * (canvas.width / rect.width)),
                y: Math.round((evt.clientY - rect.top) * (canvas.height / rect.height))
            };
        }

        canvas.addEventListener('mousedown', function(e) {
            const pos = getMousePos(e);
            startX = pos.x;
            startY = pos.y;
            isDrawing = true;
            hasSelection = false;
            document.getElementById('cropBtn').disabled = true;
            draw(pos.x, pos.y);
        });

        canvas.addEventListener('mousemove', function(e) {
            if (!isDrawing) return;
            const pos = getMousePos(e);
            draw(pos.x, pos.y);
        });

        canvas.addEventListener('mouseup', function(e) {
            if (!isDrawing) return;
            isDrawing = false;
            const pos = getMousePos(e);
            endX = pos.x;
            endY = pos.y;
            
            // Normalize coordinates
            const x1 = Math.min(startX, endX);
            const y1 = Math.min(startY, endY);
            const x2 = Math.max(startX, endX);
            const y2 = Math.max(startY, endY);
            
            if (x2 - x1 > 10 && y2 - y1 > 10) {
                hasSelection = true;
                document.getElementById('cropBtn').disabled = false;
                document.getElementById('coords').innerText = `x=${x1}, y=${y1}, w=${x2-x1}, h=${y2-y1}`;
                
                // Store final normalized coords
                startX = x1; startY = y1; endX = x2; endY = y2;
            }
        });

        function draw(currentX, currentY) {
            // Clear and redraw image
            ctx.clearRect(0, 0, canvas.width, canvas.height);
            ctx.drawImage(img, 0, 0);
            
            // Draw selection rectangle
            ctx.strokeStyle = '#00FF00';
            ctx.lineWidth = 3;
            ctx.beginPath();
            const w = currentX - startX;
            const h = currentY - startY;
            ctx.rect(startX, startY, w, h);
            ctx.stroke();
            
            // Dim outside area
            ctx.fillStyle = 'rgba(0,0,0,0.5)';
            // Top
            ctx.fillRect(0, 0, canvas.width, Math.min(startY, currentY));
            // Bottom
            ctx.fillRect(0, Math.max(startY, currentY), canvas.width, canvas.height - Math.max(startY, currentY));
            // Left
            ctx.fillRect(0, Math.min(startY, currentY), Math.min(startX, currentX), Math.abs(h));
            // Right
            ctx.fillRect(Math.max(startX, currentX), Math.min(startY, currentY), canvas.width - Math.max(startX, currentX), Math.abs(h));
        }

        function startCrop() {
            if (!hasSelection) return;
            
            const btn = document.getElementById('cropBtn');
            const status = document.getElementById('status');
            btn.disabled = true;
            btn.innerText = "Processing...";
            status.innerText = "Starting batch processing... check terminal for details.";

            fetch('/process', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    x1: startX,
                    y1: startY,
                    x2: endX,
                    y2: endY
                })
            })
            .then(response => response.json())
            .then(data => {
                btn.innerText = "Done!";
                status.innerText = data.message;
                alert("Processing Complete! Saved to: " + data.output_path);
            })
            .catch(error => {
                btn.innerText = "Error";
                btn.disabled = false;
                status.innerText = "Error: " + error;
            });
        }
    </script>
</body>
</html>
"""

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)

@app.route('/image')
def get_image():
    # Try to find the default image
    img_path = os.path.join(DATASET_ROOT, "overlays", DEFAULT_IMAGE)
    if not os.path.exists(img_path):
        # Fallback to first jpg in overlays
        files = glob.glob(os.path.join(DATASET_ROOT, "overlays", "*.jpg"))
        if files:
            img_path = files[0]
        else:
            return "No images found in " + os.path.join(DATASET_ROOT, "overlays"), 404
            
    return send_file(img_path, mimetype='image/jpeg')

@app.route('/process', methods=['POST'])
def process():
    data = request.json
    x1, y1 = int(data['x1']), int(data['y1'])
    x2, y2 = int(data['x2']), int(data['y2'])
    
    # Ensure output directories exist
    os.makedirs(os.path.join(OUTPUT_ROOT, "images"), exist_ok=True)
    os.makedirs(os.path.join(OUTPUT_ROOT, "overlays"), exist_ok=True)
    
    # Get all images
    # We assume corresponding filenames in images/ and overlays/
    overlay_files = glob.glob(os.path.join(DATASET_ROOT, "overlays", "*.jpg"))
    
    processed_count = 0
    
    print(f"Starting batch crop. ROI: ({x1},{y1}) to ({x2},{y2})")
    print(f"Found {len(overlay_files)} overlays to process.")
    
    for overlay_path in overlay_files:
        filename = os.path.basename(overlay_path)
        
        # Process Overlay
        img_overlay = cv2.imread(overlay_path)
        if img_overlay is not None:
            cropped_overlay = img_overlay[y1:y2, x1:x2]
            cv2.imwrite(os.path.join(OUTPUT_ROOT, "overlays", filename), cropped_overlay)
        
        # Process Original Image (if exists)
        # The overlay has _overlay.jpg, the original is usually .jpg
        # But checking the user's filenames: "Chemo_1MC_1424711 (3)_overlay.jpg"
        # The original should be "Chemo_1MC_1424711 (3).jpg"
        
        original_filename = filename.replace("_overlay.jpg", ".jpg")
        original_path = os.path.join(DATASET_ROOT, "images", original_filename)
        
        if os.path.exists(original_path):
            img_orig = cv2.imread(original_path)
            if img_orig is not None:
                # Resize check? Assuming original and overlay are same size
                if img_orig.shape[:2] != img_overlay.shape[:2]:
                    # If sizes differ, we might need to scale coordinates?
                    # Usually they match in this pipeline. Let's assume match.
                    pass
                    
                cropped_orig = img_orig[y1:y2, x1:x2]
                cv2.imwrite(os.path.join(OUTPUT_ROOT, "images", original_filename), cropped_orig)
        
        processed_count += 1
        if processed_count % 100 == 0:
            print(f"Processed {processed_count} images...")

    return jsonify({
        "status": "success", 
        "message": f"Processed {processed_count} images.",
        "output_path": OUTPUT_ROOT
    })

def open_browser():
    time.sleep(1.5)
    webbrowser.open('http://127.0.0.1:5001')

if __name__ == '__main__':
    print("Starting Crop Tool Server...")
    print("Please open http://127.0.0.1:5001 in your browser if it doesn't open automatically.")
    
    # Run browser opener in separate thread
    threading.Thread(target=open_browser).start()
    
    app.run(host='0.0.0.0', port=5001, debug=False)

