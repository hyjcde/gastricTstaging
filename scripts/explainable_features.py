"""
基于物理特征的可解释性 AI 诊断系统
Explainable AI Diagnosis System Based on Physical Features

核心算法:
1. SII (Serosal Integrity Index) - 浆膜完整性指数: 用于 T4 鉴别
2. RTV (Radial Thickness Variance) - 径向厚度变异: 用于 T2/T3 鉴别

Author: AI Assistant
Date: 2024
"""

import numpy as np
import cv2
import json
import os
from pathlib import Path
from typing import List, Tuple, Dict, Optional
import matplotlib.pyplot as plt


class ExplainableFeatureExtractor:
    """
    基于物理特征的可解释性特征提取器
    
    核心理念: 拒绝黑盒，回归病理
    - 测量几何特征（厚度不均）
    - 探测物理屏障（浆膜完整性）
    """
    
    def __init__(
        self,
        skip_distance: int = 8,      # 跳过画笔宽度的像素数
        search_distance: int = 50,   # 搜索范围（像素），约 5mm
        brightness_threshold: float = 0.6,  # 高回声判定阈值（相对于局部最大值）
        num_probes: int = 360,       # 发射探针数量
        pixel_spacing: float = 0.1,  # mm/pixel，需要根据实际图像校准
    ):
        """
        初始化特征提取器
        
        Args:
            skip_distance: 跳过的像素距离（避免画笔干扰）
            search_distance: 向外搜索的距离（像素）
            brightness_threshold: 高回声判定阈值
            num_probes: 沿轮廓发射的探针数量
            pixel_spacing: 像素间距 (mm/pixel)
        """
        self.skip_distance = skip_distance
        self.search_distance = search_distance
        self.brightness_threshold = brightness_threshold
        self.num_probes = num_probes
        self.pixel_spacing = pixel_spacing
        
    def load_annotation(self, json_path: str) -> Dict:
        """
        加载 LabelMe 格式的标注文件
        
        Args:
            json_path: JSON 标注文件路径
            
        Returns:
            包含 shapes 和图像尺寸的字典
        """
        with open(json_path, 'r') as f:
            data = json.load(f)
        return data
    
    def extract_contour_from_shapes(self, shapes: List[Dict]) -> np.ndarray:
        """
        从 shapes 中提取轮廓点
        
        Args:
            shapes: LabelMe shapes 列表
            
        Returns:
            轮廓点数组 (N, 2)
        """
        # 合并所有 shape 的点
        all_points = []
        for shape in shapes:
            points = np.array(shape['points'])
            all_points.extend(points.tolist())
        
        if not all_points:
            raise ValueError("No points found in shapes")
            
        return np.array(all_points)
    
    def smooth_contour(self, contour: np.ndarray, smoothing_factor: float = 0.01) -> np.ndarray:
        """
        平滑轮廓（消除手抖锯齿）
        使用移动平均 + 均匀重采样，保持轮廓贴合
        
        Args:
            contour: 原始轮廓点 (N, 2)
            smoothing_factor: 平滑因子 (影响移动平均窗口大小)
            
        Returns:
            平滑后的轮廓点
        """
        # 确保轮廓是闭合的
        if not np.allclose(contour[0], contour[-1]):
            contour = np.vstack([contour, contour[0]])
        
        # 1. 移动平均平滑（保持原始点数，只消除锯齿）
        window_size = max(3, int(len(contour) * smoothing_factor))
        if window_size % 2 == 0:
            window_size += 1  # 确保是奇数
        
        # 对闭合轮廓进行循环填充
        pad_size = window_size // 2
        padded_x = np.concatenate([contour[-pad_size:, 0], contour[:, 0], contour[:pad_size, 0]])
        padded_y = np.concatenate([contour[-pad_size:, 1], contour[:, 1], contour[:pad_size, 1]])
        
        # 移动平均
        kernel = np.ones(window_size) / window_size
        smooth_x = np.convolve(padded_x, kernel, mode='valid')
        smooth_y = np.convolve(padded_y, kernel, mode='valid')
        
        smoothed_contour = np.column_stack([smooth_x, smooth_y])
        
        # 2. 均匀重采样到指定数量的点
        # 计算轮廓总长度
        total_length = 0
        lengths = [0]
        for i in range(len(smoothed_contour) - 1):
            dist = np.linalg.norm(smoothed_contour[i+1] - smoothed_contour[i])
            total_length += dist
            lengths.append(total_length)
        
        # 闭合距离
        close_dist = np.linalg.norm(smoothed_contour[0] - smoothed_contour[-1])
        total_length += close_dist
        lengths.append(total_length)
        
        # 均匀重采样
        resampled_points = []
        target_distances = np.linspace(0, total_length, self.num_probes, endpoint=False)
        
        for target_dist in target_distances:
            # 找到对应的线段
            for i in range(len(lengths) - 1):
                if lengths[i] <= target_dist <= lengths[i + 1]:
                    # 在线段上插值
                    seg_length = lengths[i + 1] - lengths[i]
                    if seg_length > 0:
                        t = (target_dist - lengths[i]) / seg_length
                    else:
                        t = 0
                    
                    # 处理闭合段
                    if i < len(smoothed_contour) - 1:
                        point = smoothed_contour[i] * (1 - t) + smoothed_contour[i + 1] * t
                    else:
                        point = smoothed_contour[-1] * (1 - t) + smoothed_contour[0] * t
                    
                    resampled_points.append(point)
                    break
        
        return np.array(resampled_points)
    
    def compute_normals(self, contour: np.ndarray) -> np.ndarray:
        """
        计算轮廓每个点的法线方向（向外）
        
        Args:
            contour: 轮廓点 (N, 2)
            
        Returns:
            法线向量 (N, 2)，已归一化
        """
        # 计算切线方向（使用中心差分）
        tangents = np.zeros_like(contour)
        tangents[1:-1] = contour[2:] - contour[:-2]
        tangents[0] = contour[1] - contour[-1]
        tangents[-1] = contour[0] - contour[-2]
        
        # 法线 = 切线旋转 90 度
        normals = np.zeros_like(tangents)
        normals[:, 0] = -tangents[:, 1]
        normals[:, 1] = tangents[:, 0]
        
        # 归一化
        norms = np.linalg.norm(normals, axis=1, keepdims=True)
        norms[norms == 0] = 1  # 避免除以零
        normals = normals / norms
        
        # 确保法线向外（假设轮廓是逆时针方向）
        # 计算质心
        centroid = np.mean(contour, axis=0)
        
        # 检查法线方向，如果指向质心则翻转
        for i in range(len(normals)):
            to_centroid = centroid - contour[i]
            if np.dot(normals[i], to_centroid) > 0:
                normals[i] = -normals[i]
                
        return normals
    
    def compute_sii(
        self, 
        image: np.ndarray, 
        contour: np.ndarray, 
        normals: np.ndarray
    ) -> Tuple[float, np.ndarray, np.ndarray]:
        """
        计算浆膜完整性指数 (Serosal Integrity Index)
        
        雷达搜索法:
        1. 沿轮廓每个点向法线外侧发射探针
        2. 跳过画笔宽度，在搜索范围内扫描亮度
        3. 判断是否存在高回声屏障（浆膜）
        
        Args:
            image: 灰度图像
            contour: 平滑后的轮廓点
            normals: 法线方向
            
        Returns:
            sii: 浆膜完整性指数 (0-1, 1表示完整)
            scores: 每个探针点的得分
            breach_locations: 潜在突破点位置
        """
        h, w = image.shape[:2]
        scores = np.zeros(len(contour))
        profiles = []
        
        for i, (point, normal) in enumerate(zip(contour, normals)):
            # 生成探针采样点
            distances = np.arange(self.skip_distance, self.skip_distance + self.search_distance)
            sample_points = point + normal * distances[:, np.newaxis]
            
            # 采集亮度值
            brightness_values = []
            for sp in sample_points:
                x, y = int(sp[0]), int(sp[1])
                if 0 <= x < w and 0 <= y < h:
                    brightness_values.append(image[y, x])
                else:
                    brightness_values.append(0)
            
            brightness_values = np.array(brightness_values, dtype=float)
            profiles.append(brightness_values)
            
            # 判断是否存在高回声屏障
            if len(brightness_values) > 0 and np.max(brightness_values) > 0:
                # 归一化
                max_val = np.max(brightness_values)
                normalized = brightness_values / max_val
                
                # 检测峰值
                peak_mask = normalized > self.brightness_threshold
                if np.any(peak_mask):
                    # 找到第一个峰值的位置
                    first_peak_idx = np.argmax(peak_mask)
                    # 得分基于峰值强度和位置
                    peak_strength = normalized[first_peak_idx]
                    position_factor = 1 - (first_peak_idx / len(distances))  # 越近越好
                    scores[i] = peak_strength * (0.5 + 0.5 * position_factor)
                else:
                    scores[i] = 0  # 无屏障
            else:
                scores[i] = 0
        
        # 计算 SII（使用最低分区域的平均值）
        # 找到最危险的区域（连续低分段）
        window_size = max(1, len(scores) // 36)  # 10度窗口
        smoothed_scores = np.convolve(scores, np.ones(window_size)/window_size, mode='same')
        
        # SII = 最低区域的平均得分
        min_region_score = np.min(smoothed_scores)
        sii = np.mean(scores)  # 整体 SII
        
        # 找到潜在突破点（得分低于阈值的位置）
        threshold = 0.3
        breach_mask = smoothed_scores < threshold
        breach_locations = contour[breach_mask]
        
        return sii, scores, breach_locations
    
    def compute_rtv(
        self, 
        image: np.ndarray, 
        contour: np.ndarray, 
        normals: np.ndarray,
        inner_search: int = 30,
        outer_search: int = 50
    ) -> Tuple[float, np.ndarray]:
        """
        计算径向厚度变异 (Radial Thickness Variance)
        
        用于 T2/T3 鉴别:
        - RTV 低（厚度均匀）→ T2
        - RTV 高（厚度起伏大）→ T3
        
        Args:
            image: 灰度图像
            contour: 平滑后的轮廓点
            normals: 法线方向
            inner_search: 向内搜索距离
            outer_search: 向外搜索距离
            
        Returns:
            rtv: 径向厚度变异系数
            thickness: 每个点的厚度值
        """
        h, w = image.shape[:2]
        thickness = np.zeros(len(contour))
        
        for i, (point, normal) in enumerate(zip(contour, normals)):
            # 向内和向外搜索
            inner_distances = np.arange(1, inner_search)
            outer_distances = np.arange(1, outer_search)
            
            inner_points = point - normal * inner_distances[:, np.newaxis]
            outer_points = point + normal * outer_distances[:, np.newaxis]
            
            # 采集内侧亮度
            inner_brightness = []
            for ip in inner_points:
                x, y = int(ip[0]), int(ip[1])
                if 0 <= x < w and 0 <= y < h:
                    inner_brightness.append(image[y, x])
                else:
                    inner_brightness.append(0)
            
            # 采集外侧亮度
            outer_brightness = []
            for op in outer_points:
                x, y = int(op[0]), int(op[1])
                if 0 <= x < w and 0 <= y < h:
                    outer_brightness.append(image[y, x])
                else:
                    outer_brightness.append(0)
            
            inner_brightness = np.array(inner_brightness, dtype=float)
            outer_brightness = np.array(outer_brightness, dtype=float)
            
            # 计算"墙"的厚度（基于亮度梯度）
            # 简化版本：找到内外边界的距离
            inner_edge = 0
            outer_edge = 0
            
            if len(inner_brightness) > 0:
                # 内边界：亮度快速下降的位置
                gradient = np.abs(np.diff(inner_brightness))
                if len(gradient) > 0 and np.max(gradient) > 10:
                    inner_edge = np.argmax(gradient)
            
            if len(outer_brightness) > 0:
                # 外边界：高回声峰值位置
                if np.max(outer_brightness) > 50:
                    outer_edge = np.argmax(outer_brightness)
            
            thickness[i] = self.skip_distance + inner_edge + outer_edge
        
        # 计算变异系数 (CV)
        mean_thickness = np.mean(thickness)
        std_thickness = np.std(thickness)
        
        if mean_thickness > 0:
            rtv = std_thickness / mean_thickness
        else:
            rtv = 0
            
        return rtv, thickness
    
    def analyze_image(
        self, 
        image_path: str, 
        annotation_path: str,
        visualize: bool = True,
        output_dir: Optional[str] = None
    ) -> Dict:
        """
        分析单张图像
        
        Args:
            image_path: 图像路径
            annotation_path: 标注 JSON 路径
            visualize: 是否生成可视化
            output_dir: 输出目录
            
        Returns:
            分析结果字典
        """
        # 加载图像
        image = cv2.imread(image_path)
        if image is None:
            raise ValueError(f"Cannot load image: {image_path}")
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        
        # 加载标注
        annotation = self.load_annotation(annotation_path)
        shapes = annotation.get('shapes', [])
        
        if not shapes:
            raise ValueError(f"No shapes found in annotation: {annotation_path}")
        
        # 提取并平滑轮廓
        raw_contour = self.extract_contour_from_shapes(shapes)
        smooth_contour = self.smooth_contour(raw_contour)
        
        # 计算法线
        normals = self.compute_normals(smooth_contour)
        
        # 计算 SII
        sii, sii_scores, breach_locations = self.compute_sii(gray, smooth_contour, normals)
        
        # 计算 RTV
        rtv, thickness = self.compute_rtv(gray, smooth_contour, normals)
        
        # 结果
        results = {
            'image_path': image_path,
            'annotation_path': annotation_path,
            'sii': float(sii),
            'sii_scores': sii_scores.tolist(),
            'rtv': float(rtv),
            'thickness': thickness.tolist(),
            'breach_count': len(breach_locations),
            'mean_thickness_mm': float(np.mean(thickness) * self.pixel_spacing),
            'std_thickness_mm': float(np.std(thickness) * self.pixel_spacing),
        }
        
        # T 分期预测
        if sii < 0.3:
            results['predicted_t_stage'] = 'T4'
            results['confidence'] = 'High' if sii < 0.2 else 'Medium'
            results['explanation'] = f'SII极低({sii:.2f})，检测到{len(breach_locations)}处潜在浆膜突破点'
        elif rtv > 0.4:
            results['predicted_t_stage'] = 'T3'
            results['confidence'] = 'High' if rtv > 0.5 else 'Medium'
            results['explanation'] = f'RTV较高({rtv:.2f})，胃壁厚度不均匀，符合T3特征'
        else:
            results['predicted_t_stage'] = 'T2'
            results['confidence'] = 'Medium'
            results['explanation'] = f'SII正常({sii:.2f})，RTV较低({rtv:.2f})，倾向T2'
        
        # 可视化
        if visualize:
            self._visualize_results(
                image, gray, smooth_contour, normals, 
                sii_scores, breach_locations, thickness, results,
                output_dir, Path(image_path).stem
            )
        
        return results
    
    def _visualize_results(
        self, 
        image: np.ndarray,
        gray: np.ndarray,
        contour: np.ndarray,
        normals: np.ndarray,
        sii_scores: np.ndarray,
        breach_locations: np.ndarray,
        thickness: np.ndarray,
        results: Dict,
        output_dir: Optional[str],
        filename: str
    ):
        """
        生成可视化结果
        """
        fig, axes = plt.subplots(2, 2, figsize=(16, 12))
        
        # 1. 原图 + 轮廓 + 风险着色
        ax1 = axes[0, 0]
        ax1.imshow(cv2.cvtColor(image, cv2.COLOR_BGR2RGB))
        
        # 绘制轮廓，颜色根据 SII 得分变化（绿=安全，红=危险）
        for i in range(len(contour) - 1):
            score = sii_scores[i]
            # 红绿灯机制
            if score > 0.5:
                color = (0, 1, 0)  # 绿色 - 安全
            elif score > 0.3:
                color = (1, 1, 0)  # 黄色 - 警告
            else:
                color = (1, 0, 0)  # 红色 - 危险
            ax1.plot([contour[i, 0], contour[i+1, 0]], 
                    [contour[i, 1], contour[i+1, 1]], 
                    color=color, linewidth=2)
        
        # 标记突破点
        if len(breach_locations) > 0:
            ax1.scatter(breach_locations[:, 0], breach_locations[:, 1], 
                       c='red', s=100, marker='x', linewidths=2, 
                       label='Potential Invasion Site')
            ax1.legend(loc='upper right')
        
        ax1.set_title(f"Risk Map - Predicted: {results['predicted_t_stage']}", fontsize=14)
        ax1.axis('off')
        
        # 2. SII 雷达图
        ax2 = axes[0, 1]
        angles = np.linspace(0, 2*np.pi, len(sii_scores), endpoint=False)
        
        # 闭合曲线
        angles = np.concatenate([angles, [angles[0]]])
        scores_closed = np.concatenate([sii_scores, [sii_scores[0]]])
        
        ax2 = plt.subplot(2, 2, 2, projection='polar')
        ax2.plot(angles, scores_closed, 'b-', linewidth=2)
        ax2.fill(angles, scores_closed, alpha=0.3)
        ax2.set_ylim(0, 1)
        ax2.set_title(f"SII Radar (Overall: {results['sii']:.2f})", fontsize=14)
        
        # 3. 厚度分布
        ax3 = axes[1, 0]
        x = np.arange(len(thickness))
        ax3.fill_between(x, thickness, alpha=0.3)
        ax3.plot(x, thickness, 'b-', linewidth=1)
        ax3.axhline(y=np.mean(thickness), color='r', linestyle='--', 
                   label=f'Mean: {np.mean(thickness):.1f}px')
        ax3.set_xlabel('Contour Position (degrees)', fontsize=12)
        ax3.set_ylabel('Wall Thickness (pixels)', fontsize=12)
        ax3.set_title(f"Radial Thickness Variance (RTV: {results['rtv']:.2f})", fontsize=14)
        ax3.legend()
        ax3.grid(True, alpha=0.3)
        
        # 4. 诊断报告
        ax4 = axes[1, 1]
        ax4.axis('off')
        
        report_text = f"""
╔══════════════════════════════════════════════════════════════╗
║                    AI DIAGNOSIS REPORT                       ║
╠══════════════════════════════════════════════════════════════╣
║                                                              ║
║  Predicted T-Stage: {results['predicted_t_stage']:>5}  ({results['confidence']} Confidence)        ║
║                                                              ║
╠══════════════════════════════════════════════════════════════╣
║  EXPLAINABILITY METRICS:                                     ║
║                                                              ║
║  1. Serosal Integrity Index (SII): {results['sii']:.2f}                      ║
║     → {'CRITICAL' if results['sii'] < 0.3 else 'NORMAL':>8} - {len(breach_locations)} potential breach points detected   ║
║                                                              ║
║  2. Radial Thickness Variance (RTV): {results['rtv']:.2f}                    ║
║     → {'HIGH' if results['rtv'] > 0.4 else 'NORMAL':>8} - Wall thickness {'irregular' if results['rtv'] > 0.4 else 'uniform'}         ║
║                                                              ║
║  3. Mean Wall Thickness: {results['mean_thickness_mm']:.1f} mm                          ║
║     (Std: {results['std_thickness_mm']:.1f} mm)                                          ║
║                                                              ║
╠══════════════════════════════════════════════════════════════╣
║  INTERPRETATION:                                             ║
║  {results['explanation']:<60} ║
║                                                              ║
╚══════════════════════════════════════════════════════════════╝
"""
        ax4.text(0.05, 0.95, report_text, transform=ax4.transAxes, 
                fontsize=10, verticalalignment='top', fontfamily='monospace',
                bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))
        
        plt.tight_layout()
        
        if output_dir:
            os.makedirs(output_dir, exist_ok=True)
            output_path = os.path.join(output_dir, f"{filename}_analysis.png")
            plt.savefig(output_path, dpi=150, bbox_inches='tight')
            print(f"Saved visualization to: {output_path}")
        
        plt.show()
        plt.close()


def main():
    """
    测试脚本
    """
    # 初始化特征提取器
    extractor = ExplainableFeatureExtractor(
        skip_distance=8,
        search_distance=50,
        brightness_threshold=0.6,
        num_probes=360,
        pixel_spacing=0.1
    )
    
    # 数据目录
    base_dir = Path("/Users/huangyijun/Projects/胃癌T分期/Gastric_Cancer_Dataset")
    images_dir = base_dir / "images"
    annotations_dir = base_dir / "annotations"
    output_dir = base_dir / "explainable_analysis"
    
    # 找几张测试图片
    test_cases = [
        "Chemo_1MC_1410481 (1)",
        "Surgery_1M_1363628 (1)",
    ]
    
    # 如果指定的不存在，找几张存在的
    available_images = list(images_dir.glob("*.jpg"))[:3]
    
    results_list = []
    
    for img_path in available_images:
        name = img_path.stem
        json_path = annotations_dir / f"{name}.json"
        
        if not json_path.exists():
            print(f"Skipping {name}: annotation not found")
            continue
        
        print(f"\n{'='*60}")
        print(f"Analyzing: {name}")
        print(f"{'='*60}")
        
        try:
            results = extractor.analyze_image(
                str(img_path),
                str(json_path),
                visualize=True,
                output_dir=str(output_dir)
            )
            results_list.append(results)
            
            print(f"\nResults:")
            print(f"  - Predicted T-Stage: {results['predicted_t_stage']} ({results['confidence']})")
            print(f"  - SII: {results['sii']:.3f}")
            print(f"  - RTV: {results['rtv']:.3f}")
            print(f"  - Breach Points: {results['breach_count']}")
            print(f"  - Explanation: {results['explanation']}")
            
        except Exception as e:
            print(f"Error analyzing {name}: {e}")
            import traceback
            traceback.print_exc()
    
    # 保存汇总结果
    if results_list:
        import json as json_module
        summary_path = output_dir / "analysis_summary.json"
        with open(summary_path, 'w') as f:
            json_module.dump(results_list, f, indent=2)
        print(f"\nSummary saved to: {summary_path}")


if __name__ == "__main__":
    main()

