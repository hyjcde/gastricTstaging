"""
基于物理特征的可解释性 AI 诊断系统 V2
Explainable AI Diagnosis System Based on Physical Features V2

改进版本:
1. 自适应亮度分析 - 不依赖固定阈值
2. 梯度场分析 - 检测边界清晰度
3. 纹理特征 - 分析周边组织特性
4. 局部对比度 - 检测浆膜层是否存在

核心思路:
- T4 判定: 浆膜层（高回声亮线）是否被突破
  → 检测轮廓外侧是否存在"亮-暗-亮"的层状结构
  → 如果只有"暗"或"亮度渐变"，说明浆膜被突破

- T2/T3 判定: 边界清晰度 + 层次结构
  → T2: 边界清晰，层次分明
  → T3: 边界模糊，层次紊乱

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


class ExplainableFeatureExtractorV2:
    """
    改进版特征提取器
    
    核心改进:
    1. 使用局部自适应分析，不依赖全局阈值
    2. 分析梯度场而非绝对亮度
    3. 检测层状结构而非单一峰值
    """
    
    def __init__(
        self,
        skip_distance: int = 5,       # 跳过画笔宽度
        search_distance: int = 60,    # 向外搜索距离
        num_probes: int = 180,        # 探针数量
        pixel_spacing: float = 0.1,   # mm/pixel
    ):
        self.skip_distance = skip_distance
        self.search_distance = search_distance
        self.num_probes = num_probes
        self.pixel_spacing = pixel_spacing
        
    def load_annotation(self, json_path: str) -> Dict:
        """加载标注文件"""
        with open(json_path, 'r') as f:
            data = json.load(f)
        return data
    
    def extract_contour_from_shapes(self, shapes: List[Dict]) -> np.ndarray:
        """从 shapes 中提取轮廓点"""
        all_points = []
        for shape in shapes:
            points = np.array(shape['points'])
            all_points.extend(points.tolist())
        
        if not all_points:
            raise ValueError("No points found in shapes")
            
        return np.array(all_points)
    
    def resample_contour(self, contour: np.ndarray) -> np.ndarray:
        """
        均匀重采样轮廓点（不做平滑，保持原始形状）
        """
        # 确保轮廓闭合
        if not np.allclose(contour[0], contour[-1]):
            contour = np.vstack([contour, contour[0]])
        
        # 计算累积弧长
        diffs = np.diff(contour, axis=0)
        segment_lengths = np.sqrt((diffs ** 2).sum(axis=1))
        cumulative_length = np.concatenate([[0], np.cumsum(segment_lengths)])
        total_length = cumulative_length[-1]
        
        # 均匀采样
        target_lengths = np.linspace(0, total_length, self.num_probes, endpoint=False)
        resampled = []
        
        for target in target_lengths:
            # 找到对应的线段
            idx = np.searchsorted(cumulative_length, target) - 1
            idx = max(0, min(idx, len(contour) - 2))
            
            # 线性插值
            seg_start = cumulative_length[idx]
            seg_end = cumulative_length[idx + 1]
            if seg_end > seg_start:
                t = (target - seg_start) / (seg_end - seg_start)
            else:
                t = 0
            
            point = contour[idx] * (1 - t) + contour[idx + 1] * t
            resampled.append(point)
        
        return np.array(resampled)
    
    def compute_outward_normals(self, contour: np.ndarray) -> np.ndarray:
        """
        计算向外的法线方向
        使用质心来确定"外"的方向
        """
        centroid = np.mean(contour, axis=0)
        
        normals = np.zeros_like(contour)
        n = len(contour)
        
        for i in range(n):
            # 计算切线（使用相邻点）
            prev_i = (i - 1) % n
            next_i = (i + 1) % n
            tangent = contour[next_i] - contour[prev_i]
            
            # 法线 = 切线旋转 90 度
            normal = np.array([-tangent[1], tangent[0]])
            
            # 归一化
            norm = np.linalg.norm(normal)
            if norm > 0:
                normal = normal / norm
            
            # 确保指向外侧（远离质心）
            to_centroid = centroid - contour[i]
            if np.dot(normal, to_centroid) > 0:
                normal = -normal
            
            normals[i] = normal
        
        return normals
    
    def extract_radial_profile(
        self, 
        image: np.ndarray, 
        point: np.ndarray, 
        direction: np.ndarray,
        inner_dist: int = 20,
        outer_dist: int = 60
    ) -> Tuple[np.ndarray, np.ndarray]:
        """
        提取沿径向的亮度剖面
        
        Returns:
            distances: 距离数组（负=内侧，正=外侧）
            values: 对应的亮度值
        """
        h, w = image.shape[:2]
        
        # 生成采样点（内侧到外侧）
        distances = np.arange(-inner_dist, outer_dist + 1)
        values = []
        
        for d in distances:
            sample_point = point + direction * d
            x, y = int(sample_point[0]), int(sample_point[1])
            
            if 0 <= x < w and 0 <= y < h:
                values.append(float(image[y, x]))
            else:
                values.append(np.nan)
        
        return distances, np.array(values)
    
    def analyze_layer_structure(self, profile: np.ndarray, distances: np.ndarray) -> Dict:
        """
        分析层状结构
        
        胃壁正常层次（从内到外）:
        - 黏膜层 (mucosa): 高回声
        - 黏膜肌层: 低回声
        - 黏膜下层: 高回声
        - 固有肌层: 低回声
        - 浆膜层 (serosa): 高回声 ← 关键！
        
        T4 的特征: 浆膜层消失或不连续
        """
        # 移除 NaN
        valid_mask = ~np.isnan(profile)
        if np.sum(valid_mask) < 10:
            return {'valid': False}
        
        valid_profile = profile[valid_mask]
        valid_distances = distances[valid_mask]
        
        # 只分析外侧（距离 > skip_distance）
        outer_mask = valid_distances > self.skip_distance
        if np.sum(outer_mask) < 5:
            return {'valid': False}
        
        outer_profile = valid_profile[outer_mask]
        outer_distances = valid_distances[outer_mask]
        
        # 局部归一化
        p_min, p_max = np.percentile(outer_profile, [5, 95])
        if p_max - p_min < 10:  # 对比度太低
            normalized = np.zeros_like(outer_profile)
        else:
            normalized = (outer_profile - p_min) / (p_max - p_min)
            normalized = np.clip(normalized, 0, 1)
        
        # 计算梯度
        gradient = np.gradient(normalized)
        
        # 检测峰值（高回声带 = 浆膜层候选）
        # 峰值定义：局部最大值 + 高于中位数
        peaks = []
        median_val = np.median(normalized)
        for i in range(1, len(normalized) - 1):
            if normalized[i] > normalized[i-1] and normalized[i] > normalized[i+1]:
                if normalized[i] > median_val + 0.2:  # 显著高于中位数
                    peaks.append({
                        'index': i,
                        'distance': outer_distances[i],
                        'value': normalized[i],
                        'prominence': normalized[i] - median_val
                    })
        
        # 分析结果
        result = {
            'valid': True,
            'outer_profile': outer_profile.tolist(),
            'outer_distances': outer_distances.tolist(),
            'normalized_profile': normalized.tolist(),
            'gradient': gradient.tolist(),
            'peaks': peaks,
            'num_peaks': len(peaks),
            'mean_brightness': float(np.mean(outer_profile)),
            'contrast': float(p_max - p_min),
            'gradient_magnitude': float(np.mean(np.abs(gradient))),
        }
        
        # 浆膜层检测
        # 寻找外侧 10-40 像素范围内的高回声带
        serosal_candidates = [p for p in peaks if 10 < p['distance'] < 40]
        
        if serosal_candidates:
            best_peak = max(serosal_candidates, key=lambda x: x['prominence'])
            result['serosal_detected'] = True
            result['serosal_distance'] = best_peak['distance']
            result['serosal_prominence'] = best_peak['prominence']
        else:
            result['serosal_detected'] = False
            result['serosal_distance'] = None
            result['serosal_prominence'] = 0
        
        return result
    
    def compute_boundary_sharpness(self, image: np.ndarray, contour: np.ndarray) -> float:
        """
        计算边界清晰度
        使用 Sobel 梯度在轮廓附近的平均强度
        """
        # 计算梯度图
        sobelx = cv2.Sobel(image, cv2.CV_64F, 1, 0, ksize=3)
        sobely = cv2.Sobel(image, cv2.CV_64F, 0, 1, ksize=3)
        gradient_magnitude = np.sqrt(sobelx**2 + sobely**2)
        
        # 在轮廓点附近采样
        h, w = image.shape[:2]
        gradient_values = []
        
        for point in contour:
            x, y = int(point[0]), int(point[1])
            # 采样 3x3 邻域
            for dx in [-1, 0, 1]:
                for dy in [-1, 0, 1]:
                    nx, ny = x + dx, y + dy
                    if 0 <= nx < w and 0 <= ny < h:
                        gradient_values.append(gradient_magnitude[ny, nx])
        
        if gradient_values:
            return float(np.mean(gradient_values))
        return 0
    
    def compute_local_texture(self, image: np.ndarray, point: np.ndarray, radius: int = 10) -> Dict:
        """
        计算局部纹理特征
        """
        h, w = image.shape[:2]
        x, y = int(point[0]), int(point[1])
        
        # 提取局部区域
        x1, x2 = max(0, x - radius), min(w, x + radius)
        y1, y2 = max(0, y - radius), min(h, y + radius)
        
        if x2 <= x1 or y2 <= y1:
            return {'valid': False}
        
        patch = image[y1:y2, x1:x2].astype(float)
        
        return {
            'valid': True,
            'mean': float(np.mean(patch)),
            'std': float(np.std(patch)),
            'entropy': float(self._compute_entropy(patch)),
        }
    
    def _compute_entropy(self, patch: np.ndarray) -> float:
        """计算图像熵"""
        hist, _ = np.histogram(patch.flatten(), bins=256, range=(0, 256), density=True)
        hist = hist[hist > 0]
        return -np.sum(hist * np.log2(hist))
    
    def analyze_image(
        self, 
        image_path: str, 
        annotation_path: str,
        visualize: bool = True,
        output_dir: Optional[str] = None
    ) -> Dict:
        """
        分析单张图像
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
        
        # 提取轮廓
        raw_contour = self.extract_contour_from_shapes(shapes)
        contour = self.resample_contour(raw_contour)
        normals = self.compute_outward_normals(contour)
        
        # 分析每个探针点
        layer_analyses = []
        serosal_scores = []
        
        for i, (point, normal) in enumerate(zip(contour, normals)):
            # 提取径向剖面
            distances, profile = self.extract_radial_profile(
                gray, point, normal,
                inner_dist=15,
                outer_dist=self.search_distance
            )
            
            # 分析层状结构
            analysis = self.analyze_layer_structure(profile, distances)
            layer_analyses.append(analysis)
            
            if analysis['valid']:
                # 浆膜得分：基于是否检测到浆膜层
                if analysis['serosal_detected']:
                    score = 0.5 + 0.5 * analysis['serosal_prominence']
                else:
                    # 没有检测到浆膜，检查是否有足够的对比度
                    if analysis['contrast'] < 30:
                        score = 0.3  # 低对比度区域，不确定
                    else:
                        score = 0.1  # 高对比度但无浆膜，可能突破
                serosal_scores.append(score)
            else:
                serosal_scores.append(0.5)  # 无效数据，给中性分
        
        serosal_scores = np.array(serosal_scores)
        
        # 计算边界清晰度
        boundary_sharpness = self.compute_boundary_sharpness(gray, contour)
        
        # 计算整体指标
        # SII: 浆膜完整性指数（最低 20% 的平均分）
        sorted_scores = np.sort(serosal_scores)
        n_low = max(1, len(sorted_scores) // 5)
        sii = float(np.mean(sorted_scores[:n_low]))
        
        # 检测潜在突破点（连续低分区域）
        threshold = 0.3
        breach_mask = serosal_scores < threshold
        breach_indices = np.where(breach_mask)[0]
        breach_locations = contour[breach_mask] if len(breach_indices) > 0 else np.array([])
        
        # 找到最危险的区域（连续低分段）
        danger_zones = self._find_continuous_regions(breach_indices, min_length=5)
        
        # 计算对比度变异（代替 RTV）
        contrasts = [a['contrast'] for a in layer_analyses if a['valid']]
        contrast_cv = np.std(contrasts) / np.mean(contrasts) if contrasts and np.mean(contrasts) > 0 else 0
        
        # 结果
        results = {
            'image_path': image_path,
            'annotation_path': annotation_path,
            'sii': float(sii),
            'serosal_scores': serosal_scores.tolist(),
            'boundary_sharpness': float(boundary_sharpness),
            'contrast_cv': float(contrast_cv),
            'breach_count': len(breach_indices),
            'danger_zones': danger_zones,
            'num_danger_zones': len(danger_zones),
        }
        
        # T 分期预测
        if sii < 0.25 or len(danger_zones) >= 2:
            results['predicted_t_stage'] = 'T4'
            results['confidence'] = 'High' if sii < 0.2 else 'Medium'
            if danger_zones:
                zone_desc = f"在{len(danger_zones)}处检测到浆膜缺失"
            else:
                zone_desc = f"SII极低({sii:.2f})"
            results['explanation'] = f'{zone_desc}，高度怀疑浆膜受侵'
        elif sii < 0.4 or len(danger_zones) >= 1:
            results['predicted_t_stage'] = 'T3-T4'
            results['confidence'] = 'Medium'
            results['explanation'] = f'SII偏低({sii:.2f})，可能存在浆膜侵犯，建议进一步检查'
        elif boundary_sharpness < 20 or contrast_cv > 0.5:
            results['predicted_t_stage'] = 'T3'
            results['confidence'] = 'Medium'
            results['explanation'] = f'边界模糊(清晰度:{boundary_sharpness:.1f})，层次紊乱，倾向T3'
        else:
            results['predicted_t_stage'] = 'T2'
            results['confidence'] = 'Medium'
            results['explanation'] = f'浆膜完整(SII:{sii:.2f})，边界清晰，倾向T2'
        
        # 可视化
        if visualize:
            self._visualize_results(
                image, gray, contour, normals, 
                serosal_scores, breach_locations, layer_analyses, results,
                output_dir, Path(image_path).stem
            )
        
        return results
    
    def _find_continuous_regions(self, indices: np.ndarray, min_length: int = 3) -> List[Dict]:
        """
        找到连续的索引区域
        """
        if len(indices) == 0:
            return []
        
        regions = []
        start = indices[0]
        prev = indices[0]
        
        for i in range(1, len(indices)):
            # 考虑循环（首尾相连）
            if indices[i] - prev <= 2:  # 允许小间隙
                prev = indices[i]
            else:
                if prev - start + 1 >= min_length:
                    regions.append({
                        'start': int(start),
                        'end': int(prev),
                        'length': int(prev - start + 1),
                        'angle_start': int(start * 360 / self.num_probes),
                        'angle_end': int(prev * 360 / self.num_probes),
                    })
                start = indices[i]
                prev = indices[i]
        
        # 处理最后一段
        if prev - start + 1 >= min_length:
            regions.append({
                'start': int(start),
                'end': int(prev),
                'length': int(prev - start + 1),
                'angle_start': int(start * 360 / self.num_probes),
                'angle_end': int(prev * 360 / self.num_probes),
            })
        
        return regions
    
    def _visualize_results(
        self, 
        image: np.ndarray,
        gray: np.ndarray,
        contour: np.ndarray,
        normals: np.ndarray,
        serosal_scores: np.ndarray,
        breach_locations: np.ndarray,
        layer_analyses: List[Dict],
        results: Dict,
        output_dir: Optional[str],
        filename: str
    ):
        """生成可视化结果"""
        fig = plt.figure(figsize=(18, 12))
        
        # 1. 风险地图
        ax1 = fig.add_subplot(2, 3, 1)
        ax1.imshow(cv2.cvtColor(image, cv2.COLOR_BGR2RGB))
        
        # 绘制轮廓，颜色根据浆膜得分变化
        for i in range(len(contour) - 1):
            score = serosal_scores[i]
            if score > 0.6:
                color = (0, 0.8, 0)  # 绿色 - 安全
            elif score > 0.4:
                color = (0.8, 0.8, 0)  # 黄色 - 警告
            elif score > 0.25:
                color = (1, 0.5, 0)  # 橙色 - 高风险
            else:
                color = (1, 0, 0)  # 红色 - 危险
            ax1.plot([contour[i, 0], contour[i+1, 0]], 
                    [contour[i, 1], contour[i+1, 1]], 
                    color=color, linewidth=2.5)
        
        # 标记突破点
        if len(breach_locations) > 0:
            ax1.scatter(breach_locations[:, 0], breach_locations[:, 1], 
                       c='red', s=80, marker='x', linewidths=2, 
                       label='Potential Breach')
        
        # 绘制部分探针方向（每隔几个画一个）
        step = max(1, len(contour) // 36)
        for i in range(0, len(contour), step):
            start = contour[i]
            end = start + normals[i] * 30
            ax1.arrow(start[0], start[1], 
                     end[0] - start[0], end[1] - start[1],
                     head_width=3, head_length=2, fc='cyan', ec='cyan', alpha=0.5)
        
        ax1.set_title(f"Risk Map - Predicted: {results['predicted_t_stage']}", fontsize=12)
        ax1.axis('off')
        
        # 2. 浆膜得分雷达图
        ax2 = fig.add_subplot(2, 3, 2, projection='polar')
        angles = np.linspace(0, 2*np.pi, len(serosal_scores), endpoint=False)
        angles = np.concatenate([angles, [angles[0]]])
        scores_closed = np.concatenate([serosal_scores, [serosal_scores[0]]])
        
        ax2.plot(angles, scores_closed, 'b-', linewidth=1.5)
        ax2.fill(angles, scores_closed, alpha=0.3)
        ax2.set_ylim(0, 1)
        ax2.axhline(y=0.3, color='r', linestyle='--', alpha=0.5)
        ax2.set_title(f"Serosal Integrity (SII: {results['sii']:.2f})", fontsize=12)
        
        # 3. 典型剖面展示
        ax3 = fig.add_subplot(2, 3, 3)
        
        # 选择几个典型剖面
        n_profiles = 6
        indices = np.linspace(0, len(layer_analyses)-1, n_profiles, dtype=int)
        colors = plt.cm.viridis(np.linspace(0, 1, n_profiles))
        
        for idx, color in zip(indices, colors):
            analysis = layer_analyses[idx]
            if analysis['valid']:
                ax3.plot(analysis['outer_distances'], 
                        analysis['normalized_profile'],
                        color=color, alpha=0.7,
                        label=f'{idx*360//len(layer_analyses)}°')
        
        ax3.axhline(y=0.5, color='gray', linestyle='--', alpha=0.5)
        ax3.set_xlabel('Distance from contour (pixels)', fontsize=10)
        ax3.set_ylabel('Normalized brightness', fontsize=10)
        ax3.set_title('Radial Profiles (outer)', fontsize=12)
        ax3.legend(loc='upper right', fontsize=8)
        ax3.grid(True, alpha=0.3)
        
        # 4. 对比度分布
        ax4 = fig.add_subplot(2, 3, 4)
        contrasts = [a['contrast'] for a in layer_analyses if a['valid']]
        ax4.bar(range(len(contrasts)), contrasts, color='steelblue', alpha=0.7)
        ax4.axhline(y=np.mean(contrasts), color='r', linestyle='--', 
                   label=f'Mean: {np.mean(contrasts):.1f}')
        ax4.set_xlabel('Probe index', fontsize=10)
        ax4.set_ylabel('Local contrast', fontsize=10)
        ax4.set_title(f'Contrast Distribution (CV: {results["contrast_cv"]:.2f})', fontsize=12)
        ax4.legend()
        
        # 5. 浆膜检测统计
        ax5 = fig.add_subplot(2, 3, 5)
        detected = sum(1 for a in layer_analyses if a['valid'] and a.get('serosal_detected', False))
        not_detected = sum(1 for a in layer_analyses if a['valid'] and not a.get('serosal_detected', False))
        invalid = sum(1 for a in layer_analyses if not a['valid'])
        
        categories = ['Serosa Detected', 'Not Detected', 'Invalid']
        values = [detected, not_detected, invalid]
        colors_pie = ['green', 'red', 'gray']
        
        ax5.pie(values, labels=categories, colors=colors_pie, autopct='%1.1f%%',
               startangle=90)
        ax5.set_title('Serosal Layer Detection', fontsize=12)
        
        # 6. 诊断报告
        ax6 = fig.add_subplot(2, 3, 6)
        ax6.axis('off')
        
        report_text = f"""
AI DIAGNOSIS REPORT
{'='*50}

Predicted T-Stage: {results['predicted_t_stage']}
Confidence: {results['confidence']}

EXPLAINABILITY METRICS:
{'─'*50}

1. Serosal Integrity Index (SII): {results['sii']:.2f}
   Status: {'CRITICAL' if results['sii'] < 0.3 else 'WARNING' if results['sii'] < 0.5 else 'NORMAL'}
   
2. Boundary Sharpness: {results['boundary_sharpness']:.1f}
   Status: {'BLURRED' if results['boundary_sharpness'] < 20 else 'CLEAR'}

3. Contrast Variation: {results['contrast_cv']:.2f}
   Status: {'HIGH' if results['contrast_cv'] > 0.5 else 'NORMAL'}

4. Potential Breach Points: {results['breach_count']}
   Danger Zones: {results['num_danger_zones']}

{'─'*50}
INTERPRETATION:
{results['explanation']}

{'='*50}
"""
        ax6.text(0.05, 0.95, report_text, transform=ax6.transAxes, 
                fontsize=9, verticalalignment='top', fontfamily='monospace',
                bbox=dict(boxstyle='round', facecolor='lightyellow', alpha=0.8))
        
        plt.tight_layout()
        
        if output_dir:
            os.makedirs(output_dir, exist_ok=True)
            output_path = os.path.join(output_dir, f"{filename}_analysis_v2.png")
            plt.savefig(output_path, dpi=150, bbox_inches='tight')
            print(f"Saved visualization to: {output_path}")
        
        plt.show()
        plt.close()


def main():
    """测试脚本"""
    extractor = ExplainableFeatureExtractorV2(
        skip_distance=5,
        search_distance=60,
        num_probes=180,
        pixel_spacing=0.1
    )
    
    base_dir = Path("/Users/huangyijun/Projects/胃癌T分期/Gastric_Cancer_Dataset")
    images_dir = base_dir / "images"
    annotations_dir = base_dir / "annotations"
    output_dir = base_dir / "explainable_analysis_v2"
    
    # 测试不同分期的病例
    # 文件名中 1M = T1, 2M = T2, 3M = T3, 4M = T4
    test_cases = [
        # T4 病例
        ("Chemo_4MC_1444273 (1).jpg", "可能是 T4"),
        # T3 病例  
        ("Chemo_3MC_1444744 (2).jpg", "可能是 T3"),
        # T2 病例
        ("Chemo_2MC_1412595 (2).jpg", "可能是 T2"),
        # T1 病例
        ("Surgery_1M_1363628 (1).jpg", "可能是 T1"),
    ]
    
    results_list = []
    
    for img_name, expected in test_cases:
        img_path = images_dir / img_name
        json_name = img_name.replace('.jpg', '.json')
        json_path = annotations_dir / json_name
        
        if not img_path.exists():
            print(f"Image not found: {img_path}")
            continue
        if not json_path.exists():
            print(f"Annotation not found: {json_path}")
            continue
        
        print(f"\n{'='*60}")
        print(f"Analyzing: {img_name}")
        print(f"Expected: {expected}")
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
            print(f"  - Predicted: {results['predicted_t_stage']} ({results['confidence']})")
            print(f"  - SII: {results['sii']:.3f}")
            print(f"  - Boundary Sharpness: {results['boundary_sharpness']:.1f}")
            print(f"  - Breach Points: {results['breach_count']}")
            print(f"  - Danger Zones: {results['num_danger_zones']}")
            print(f"  - Explanation: {results['explanation']}")
            
        except Exception as e:
            print(f"Error: {e}")
            import traceback
            traceback.print_exc()
    
    # 保存汇总
    if results_list:
        import json as json_module
        summary_path = output_dir / "analysis_summary_v2.json"
        with open(summary_path, 'w') as f:
            json_module.dump(results_list, f, indent=2, ensure_ascii=False)
        print(f"\nSummary saved to: {summary_path}")


if __name__ == "__main__":
    main()

