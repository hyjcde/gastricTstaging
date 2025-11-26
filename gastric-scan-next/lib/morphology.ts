/**
 * 形态学操作工具库
 * 用于前端图像处理，如生成瘤周环
 */

/**
 * 执行形态学膨胀并生成瘤周环 (Peritumoral Ring)
 * 
 * 原理：
 * 1. Ring = Dilate(Mask) - Mask
 * 2. 在前端使用 Canvas 像素操作实现
 * 
 * @param maskUrl 原始分割掩码的 URL
 * @param radius 膨胀半径（像素），默认 20px (约 5mm，视分辨率而定)
 * @param color 环的颜色 [r, g, b, a]
 * @returns Promise<string> 返回生成的瘤周环图像的 Data URL (PNG)
 */
export async function generatePeritumoralRing(
  maskUrl: string, 
  radius: number = 20,
  color: [number, number, number, number] = [255, 215, 0, 180] // Gold color
): Promise<string> {
  return new Promise((resolve, reject) => {
    const img = new Image();
    img.crossOrigin = "Anonymous";
    img.src = maskUrl;
    
    img.onload = () => {
      try {
        const canvas = document.createElement('canvas');
        const width = img.width;
        const height = img.height;
        canvas.width = width;
        canvas.height = height;
        
        const ctx = canvas.getContext('2d', { willReadFrequently: true });
        if (!ctx) {
          reject(new Error('Could not get canvas context'));
          return;
        }

        // 1. 绘制原始掩码
        ctx.drawImage(img, 0, 0);
        const originalImageData = ctx.getImageData(0, 0, width, height);
        const originalData = originalImageData.data;
        
        // 创建二值掩码 (0: 背景, 1: 前景)
        // 使用 Int8Array 节省内存
        const binaryMask = new Int8Array(width * height);
        const dilatedMask = new Int8Array(width * height);
        
        // 提取前景
        for (let i = 0; i < originalData.length; i += 4) {
          // 只要 Alpha > 0 或 RGB 不全为黑，视为前景
          if (originalData[i + 3] > 20) { 
             const idx = i / 4;
             binaryMask[idx] = 1;
             dilatedMask[idx] = 1;
          }
        }

        // 2. 形态学膨胀 (Dilation)
        // 为了性能，不使用多次迭代，而是使用距离变换的简化思想：
        // 只需要找到所有 "背景" 像素，如果它距离任意 "前景" 像素的距离 <= radius，则标记为膨胀区域。
        // 但最朴素的 BFS 或者多轮迭代在 JS 中可能较慢。
        // 这里采用优化的两遍扫描算法 (Two-pass Distance Transform) 近似，或者简单的迭代膨胀。
        // 考虑到 radius 可能较大 (20px)，迭代 20 次 3x3 会很慢。
        // 更好的方法：不仅标记是否前景，而是通过坐标判断。
        
        // 方法 B: 对于每个前景点，绘制一个圆到新 Canvas？(利用 Canvas 自身的绘图能力)
        // 这是一个非常快的方法！
        // 1. 清空 Canvas
        // 2. 绘制原 Mask
        // 3. 设置 globalCompositeOperation = 'source-over'
        // 4. 对原 Mask 应用 shadowBlur 或 filter 不太准确。
        // 5. 正确做法：将 Mask 绘制到 Canvas，然后设置 context.shadowBlur 也不行，那是高斯模糊。
        
        // 回到像素操作：对于 radius 较小的情况，迭代尚可。
        // 对于 radius=20，像素数 512x512，25万像素。
        // 如果用 BFS：
        // 把所有边缘像素加入队列，向外层层扩散 radius 层。
        
        const queue: number[] = [];
        const visited = new Int8Array(width * height); // 记录距离
        
        // 初始化队列：所有前景像素的边界像素（即邻域有背景的）
        // 简化：所有前景像素入队，距离设为 0
        // 为了区分 "原始前景" 和 "扩散区域"，我们可以在 visited 中存储距离
        // 0: 原始前景, 1..radius: 扩散区域, -1: 背景
        
        // 初始化
        for (let y = 0; y < height; y++) {
          for (let x = 0; x < width; x++) {
            const idx = y * width + x;
            if (binaryMask[idx] === 1) {
               // 它是前景。检查是否是边缘？
               // 既然要向外扩，就把所有前景当做源。
               // 但为了减少计算，只有边缘像素才需要作为源。
               // 简单起见，直接把所有前景设为距离 0。
               // 等等，BFS 是从源点出发寻找未访问点。
               // 这里源点是“前景”，目标是“背景”。
               // 我们想要计算每个背景像素到最近前景像素的距离。
               // 所以，把所有前景像素放入队列，距离为 0。
               // 这种方法在 JS 大数组操作下可能导致内存压力，但 512x512 = 260k，还好。
               // 优化：只把边缘前景像素放入队列。
               
               // 检查 4 邻域是否有背景
               let isEdge = false;
               if (x > 0 && binaryMask[idx - 1] === 0) isEdge = true;
               else if (x < width - 1 && binaryMask[idx + 1] === 0) isEdge = true;
               else if (y > 0 && binaryMask[idx - width] === 0) isEdge = true;
               else if (y < height - 1 && binaryMask[idx + width] === 0) isEdge = true;
               
               if (isEdge) {
                   queue.push(idx);
                   // visited[idx] = 0; // 0 代表距离 0 (本身)
                   // 实际上我们用 visited 记录距离，初始化为 -1 (未访问)
                   // 前景像素不需要被访问（因为不需要变色），我们需要访问的是背景。
                   // 所以把边缘前景放入队列，但它们本身已经是环内（不显示）。
                   // 我们的目标是找到距离 <= radius 的背景像素。
               }
            }
          }
        }
        
        // 初始化距离数组：前景设为 0，背景设为 infinity
        const distances = new Int16Array(width * height).fill(-1);
        
        // 此时 queue 里全是边缘前景像素索引
        // 设置它们的距离为 0
        for (const idx of queue) {
            distances[idx] = 0;
        }
        
        let head = 0;
        while (head < queue.length) {
            const idx = queue[head++];
            const d = distances[idx];
            
            if (d >= radius) continue; // 达到最大半径，停止扩散
            
            const cx = idx % width;
            const cy = Math.floor(idx / width);
            
            // 检查 4 邻域
            const neighbors = [
                { x: cx - 1, y: cy, idx: idx - 1 },
                { x: cx + 1, y: cy, idx: idx + 1 },
                { x: cx, y: cy - 1, idx: idx - width },
                { x: cx, y: cy + 1, idx: idx + width }
            ];
            
            for (const n of neighbors) {
                if (n.x >= 0 && n.x < width && n.y >= 0 && n.y < height) {
                    // 如果是背景（binaryMask[n.idx] == 0）且未被访问（distances[n.idx] == -1）
                    if (binaryMask[n.idx] === 0 && distances[n.idx] === -1) {
                        distances[n.idx] = d + 1;
                        queue.push(n.idx);
                    }
                    // 或者是前景？前景不需要处理，因为我们是从前景往外扩。
                }
            }
        }
        
        // 3. 生成环图像
        // 遍历 distances，如果 0 < dist <= radius，则是环
        const ringImageData = ctx.createImageData(width, height);
        for (let i = 0; i < width * height; i++) {
            if (distances[i] > 0 && distances[i] <= radius) {
                const p = i * 4;
                // 渐变透明度？或者固定颜色
                ringImageData.data[p] = color[0];
                ringImageData.data[p + 1] = color[1];
                ringImageData.data[p + 2] = color[2];
                // 让内圈更实，外圈更虚？可选。这里用固定透明度。
                ringImageData.data[p + 3] = color[3];
            }
        }
        
        ctx.putImageData(ringImageData, 0, 0);
        resolve(canvas.toDataURL('image/png'));
        
      } catch (e) {
        reject(e);
      }
    };
    
    img.onerror = (err) => reject(new Error('Failed to load mask image for processing'));
  });
}

