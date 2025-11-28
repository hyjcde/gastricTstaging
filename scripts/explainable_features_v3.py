"""
基于物理特征的可解释性 AI 诊断系统 V3
Explainable AI Diagnosis System Based on Physical Features V3

核心思路转变：从"区域统计"转向"法向采样分析"
- 标注已经很精细，只需验证边界线是"实墙(T3)"还是"漏风的墙(T4)"
- 盯着边界线两侧 2-3mm 的狭长地带

三大算法：
1. 法向高斯加权梯度法 (Normal-Weighted Gradient Analysis) - 容错性最强
2. 边界内外双线性相关性分析 (Bilinear Boundary Correlation) - 利用周边像素
3. 曲率-亮度联合检测 (Curvature-Intensity Joint Detection) - 形态学特征

Author: AI Assistant
Date: 2024
"""

import numpy as np
import cv2
import json
import os
from pathlib import Path
from typing import List, Tuple, Dict, Optional
import matplotlib
matplotlib.use('Agg')  # 非交互式后端，不弹窗
import matplotlib.pyplot as plt


class ExplainableFeatureExtractorV3:
    """
    V3 版本：基于法向采样的边界验证算法
    
    核心改进：
    1. 法向宽容度采样 - 容忍标注误差
    2. 双轨相关性分析 - 检测内外同质化
    3. 曲率-梯度联合 - 检测突破点形态
    """
    
    def __init__(
        self,
        tolerance_pixels: int = 8,    # 法向采样容错范围（像素）
        track_offset: int = 5,        # 双轨偏移距离
        window_size: int = 11,        # 局部分析窗口大小
        pixel_spacing: float = 0.1,   # mm/pixel
    ):
        self.tolerance_pixels = tolerance_pixels
        self.track_offset = track_offset
        self.window_size = window_size
        self.pixel_spacing = pixel_spacing
        
    def load_annotation(self, json_path: str) -> Tuple[np.ndarray, Tuple[int, int]]:
        """
        加载标注文件，返回轮廓点和图像尺寸
        """
        with open(json_path, 'r') as f:
            data = json.load(f)
        
        shapes = data.get('shapes', [])
        if not shapes:
            raise ValueError("No shapes found")
        
        # 合并所有点
        all_points = []
        for shape in shapes:
            points = np.array(shape['points'])
            all_points.extend(points.tolist())
        
        image_size = (data.get('imageHeight', 960), data.get('imageWidth', 1280))
        return np.array(all_points), image_size
    
    def create_mask_from_points(self, points: np.ndarray, image_size: Tuple[int, int]) -> np.ndarray:
        """
        从点集创建二值 mask
        """
        h, w = image_size
        mask = np.zeros((h, w), dtype=np.uint8)
        
        # 转换为整数坐标
        pts = points.astype(np.int32).reshape((-1, 1, 2))
        cv2.fillPoly(mask, [pts], 255)
        
        return mask
    
    def get_smooth_contour(self, mask: np.ndarray, num_points: int = 360) -> np.ndarray:
        """
        获取平滑的轮廓点
        使用轻微平滑消除手抖，但保持整体形状
        """
        # 获取轮廓
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
        if not contours:
            raise ValueError("No contours found")
        
        # 取最大轮廓
        cnt = max(contours, key=cv2.contourArea)
        points = cnt.squeeze()
        
        if len(points.shape) == 1:
            points = points.reshape(-1, 2)
        
        # 轻微平滑（保持形状，只消除锯齿）
        # 使用移动平均
        window = 5
        pad = window // 2
        padded_x = np.concatenate([points[-pad:, 0], points[:, 0], points[:pad, 0]])
        padded_y = np.concatenate([points[-pad:, 1], points[:, 1], points[:pad, 1]])
        
        kernel = np.ones(window) / window
        smooth_x = np.convolve(padded_x, kernel, mode='valid')
        smooth_y = np.convolve(padded_y, kernel, mode='valid')
        
        smoothed = np.column_stack([smooth_x, smooth_y])
        
        # 均匀重采样
        return self._resample_contour(smoothed, num_points)
    
    def _resample_contour(self, contour: np.ndarray, num_points: int) -> np.ndarray:
        """均匀重采样轮廓"""
        # 计算累积弧长
        diffs = np.diff(contour, axis=0)
        segment_lengths = np.sqrt((diffs ** 2).sum(axis=1))
        cumulative = np.concatenate([[0], np.cumsum(segment_lengths)])
        total_length = cumulative[-1]
        
        # 均匀采样
        target_lengths = np.linspace(0, total_length, num_points, endpoint=False)
        resampled = []
        
        for target in target_lengths:
            idx = np.searchsorted(cumulative, target) - 1
            idx = max(0, min(idx, len(contour) - 2))
            
            seg_len = cumulative[idx + 1] - cumulative[idx]
            if seg_len > 0:
                t = (target - cumulative[idx]) / seg_len
            else:
                t = 0
            
            point = contour[idx] * (1 - t) + contour[idx + 1] * t
            resampled.append(point)
        
        return np.array(resampled)
    
    def compute_normals(self, contour: np.ndarray) -> np.ndarray:
        """
        计算每个点的外法线方向
        """
        n = len(contour)
        normals = np.zeros_like(contour)
        centroid = np.mean(contour, axis=0)
        
        for i in range(n):
            # 切线方向（使用相邻点）
            prev_i = (i - 1) % n
            next_i = (i + 1) % n
            tangent = contour[next_i] - contour[prev_i]
            
            # 法线 = 切线旋转 90 度
            normal = np.array([-tangent[1], tangent[0]])
            
            # 归一化
            norm = np.linalg.norm(normal)
            if norm > 0:
                normal = normal / norm
            
            # 确保指向外侧
            to_centroid = centroid - contour[i]
            if np.dot(normal, to_centroid) > 0:
                normal = -normal
            
            normals[i] = normal
        
        return normals
    
    def compute_curvature(self, contour: np.ndarray) -> np.ndarray:
        """
        计算轮廓曲率
        正值 = 凸向外（可能是突破点）
        负值 = 凹向内
        """
        n = len(contour)
        curvatures = np.zeros(n)
        
        for i in range(n):
            prev_i = (i - 1) % n
            next_i = (i + 1) % n
            
            # 三点计算曲率
            p0 = contour[prev_i]
            p1 = contour[i]
            p2 = contour[next_i]
            
            # 向量
            v1 = p1 - p0
            v2 = p2 - p1
            
            # 叉积（判断凹凸）
            cross = v1[0] * v2[1] - v1[1] * v2[0]
            
            # 曲率近似
            len1 = np.linalg.norm(v1)
            len2 = np.linalg.norm(v2)
            
            if len1 > 0 and len2 > 0:
                curvatures[i] = 2 * cross / (len1 * len2 * (len1 + len2))
            else:
                curvatures[i] = 0
        
        return curvatures
    
    # ==================== 形态学特征计算 ====================
    
    def compute_morphology_features(self, mask: np.ndarray, contour: np.ndarray) -> Dict:
        """
        计算肿瘤形态学特征
        这些特征与肿瘤大小和形状相关，用于辅助T分期判断
        """
        # 基本几何特征
        area = cv2.contourArea(contour.astype(np.int32))
        perimeter = cv2.arcLength(contour.astype(np.int32), True)
        
        # 圆度 (Circularity): 4π × 面积 / 周长²
        # 圆形 = 1.0, 不规则形状 < 1.0
        circularity = 4 * np.pi * area / (perimeter ** 2) if perimeter > 0 else 0
        
        # 拟合椭圆获取长短轴
        if len(contour) >= 5:
            ellipse = cv2.fitEllipse(contour.astype(np.int32))
            center, axes, angle = ellipse
            major_axis = max(axes)  # 长轴
            minor_axis = min(axes)  # 短轴
            aspect_ratio = major_axis / minor_axis if minor_axis > 0 else 1
        else:
            major_axis = minor_axis = 0
            aspect_ratio = 1
        
        # 凸包相关
        hull = cv2.convexHull(contour.astype(np.int32))
        hull_area = cv2.contourArea(hull)
        solidity = area / hull_area if hull_area > 0 else 0  # 实心度
        
        # 边界不规则度 (Boundary Irregularity)
        # 使用凸包周长与实际周长的比值
        hull_perimeter = cv2.arcLength(hull, True)
        irregularity = perimeter / hull_perimeter if hull_perimeter > 0 else 1
        
        # 等效直径 (假设为圆形时的直径)
        equivalent_diameter = np.sqrt(4 * area / np.pi) if area > 0 else 0
        
        # 转换为物理尺寸 (mm)
        area_mm2 = area * (self.pixel_spacing ** 2)
        diameter_mm = equivalent_diameter * self.pixel_spacing
        major_axis_mm = major_axis * self.pixel_spacing
        minor_axis_mm = minor_axis * self.pixel_spacing
        
        return {
            'area_pixels': float(area),
            'area_mm2': float(area_mm2),
            'perimeter_pixels': float(perimeter),
            'circularity': float(circularity),
            'aspect_ratio': float(aspect_ratio),
            'solidity': float(solidity),
            'irregularity': float(irregularity),
            'equivalent_diameter_mm': float(diameter_mm),
            'major_axis_mm': float(major_axis_mm),
            'minor_axis_mm': float(minor_axis_mm),
        }
    
    # ==================== 算法一：法向梯度采样 ====================
    
    def algorithm1_normal_gradient(
        self, 
        image: np.ndarray, 
        contour: np.ndarray, 
        normals: np.ndarray
    ) -> Dict:
        """
        算法一：法向高斯加权梯度法
        
        核心逻辑：
        - 沿法线方向采样 ±tolerance_pixels 范围
        - 寻找最大梯度值（"墙"的位置）
        - 如果整个范围内梯度都很低，说明"墙塌了"
        """
        h, w = image.shape[:2]
        
        # 计算梯度图
        gX = cv2.Sobel(image, cv2.CV_64F, 1, 0, ksize=3)
        gY = cv2.Sobel(image, cv2.CV_64F, 0, 1, ksize=3)
        gradient_mag = cv2.magnitude(gX, gY)
        
        # 归一化梯度
        grad_max = np.percentile(gradient_mag, 99)
        if grad_max > 0:
            gradient_normalized = gradient_mag / grad_max
        else:
            gradient_normalized = gradient_mag
        
        boundary_strengths = []
        best_offsets = []  # 记录最强梯度的偏移位置
        
        for i, (point, normal) in enumerate(zip(contour, normals)):
            local_max_grad = 0
            best_offset = 0
            
            # 法向采样范围：-tolerance 到 +tolerance
            for offset in range(-self.tolerance_pixels, self.tolerance_pixels + 1):
                sample_x = int(point[0] + normal[0] * offset)
                sample_y = int(point[1] + normal[1] * offset)
                
                if 0 <= sample_x < w and 0 <= sample_y < h:
                    val = gradient_normalized[sample_y, sample_x]
                    if val > local_max_grad:
                        local_max_grad = val
                        best_offset = offset
            
            boundary_strengths.append(local_max_grad)
            best_offsets.append(best_offset)
        
        boundary_strengths = np.array(boundary_strengths)
        best_offsets = np.array(best_offsets)
        
        # 计算统计指标
        # 最弱环节（最低 10% 的平均值）
        weakest_10 = np.percentile(boundary_strengths, 10)
        mean_strength = np.mean(boundary_strengths)
        
        # 找出连续的弱边界区域（潜在突破点）
        weak_threshold = 0.15  # 梯度阈值
        weak_mask = boundary_strengths < weak_threshold
        weak_regions = self._find_continuous_regions(np.where(weak_mask)[0], min_length=5)
        
        return {
            'boundary_strengths': boundary_strengths,
            'best_offsets': best_offsets,
            'weakest_10_percentile': float(weakest_10),
            'mean_strength': float(mean_strength),
            'weak_regions': weak_regions,
            'num_weak_regions': len(weak_regions),
        }
    
    # ==================== 算法二：双轨相关性分析 ====================
    
    def algorithm2_bilinear_correlation(
        self, 
        image: np.ndarray, 
        contour: np.ndarray, 
        normals: np.ndarray
    ) -> Dict:
        """
        算法二：边界内外双线性相关性分析
        
        核心逻辑：
        - 建立内轨（肿瘤侧）和外轨（脂肪侧）
        - 计算两轨的相关性和差异
        - T3: 内外差异大（负相关）
        - T4: 内外相似（正相关）= 突破
        """
        h, w = image.shape[:2]
        
        inner_values = []
        outer_values = []
        
        for point, normal in zip(contour, normals):
            # 内轨：向内偏移
            inner_x = int(point[0] - normal[0] * self.track_offset)
            inner_y = int(point[1] - normal[1] * self.track_offset)
            
            # 外轨：向外偏移
            outer_x = int(point[0] + normal[0] * self.track_offset)
            outer_y = int(point[1] + normal[1] * self.track_offset)
            
            # 采样（使用小窗口平均）
            inner_val = self._sample_with_window(image, inner_x, inner_y, 3)
            outer_val = self._sample_with_window(image, outer_x, outer_y, 3)
            
            inner_values.append(inner_val)
            outer_values.append(outer_val)
        
        inner_values = np.array(inner_values)
        outer_values = np.array(outer_values)
        
        # 计算差异
        diff_values = np.abs(outer_values - inner_values)
        
        # 局部相关性（滑动窗口）
        local_correlations = []
        half_win = self.window_size // 2
        
        for i in range(len(inner_values)):
            # 获取局部窗口
            indices = [(i + j) % len(inner_values) for j in range(-half_win, half_win + 1)]
            local_inner = inner_values[indices]
            local_outer = outer_values[indices]
            
            # 计算相关系数
            if np.std(local_inner) > 0 and np.std(local_outer) > 0:
                corr = np.corrcoef(local_inner, local_outer)[0, 1]
            else:
                corr = 0
            
            local_correlations.append(corr)
        
        local_correlations = np.array(local_correlations)
        
        # 高相关性区域 = 潜在突破点
        high_corr_threshold = 0.5
        high_corr_mask = local_correlations > high_corr_threshold
        breach_regions = self._find_continuous_regions(np.where(high_corr_mask)[0], min_length=5)
        
        # 低差异区域 = 潜在突破点
        low_diff_threshold = np.percentile(diff_values, 20)
        low_diff_mask = diff_values < low_diff_threshold
        
        return {
            'inner_values': inner_values,
            'outer_values': outer_values,
            'diff_values': diff_values,
            'local_correlations': local_correlations,
            'mean_diff': float(np.mean(diff_values)),
            'mean_correlation': float(np.mean(local_correlations)),
            'breach_regions': breach_regions,
            'num_breach_regions': len(breach_regions),
        }
    
    def _sample_with_window(self, image: np.ndarray, x: int, y: int, window: int = 3) -> float:
        """在窗口内采样平均值"""
        h, w = image.shape[:2]
        half = window // 2
        
        x1, x2 = max(0, x - half), min(w, x + half + 1)
        y1, y2 = max(0, y - half), min(h, y + half + 1)
        
        if x2 > x1 and y2 > y1:
            return float(np.mean(image[y1:y2, x1:x2]))
        return 0.0
    
    # ==================== 算法三：曲率-梯度联合检测 ====================
    
    def algorithm3_curvature_gradient(
        self, 
        image: np.ndarray, 
        contour: np.ndarray, 
        normals: np.ndarray,
        curvatures: np.ndarray,
        boundary_strengths: np.ndarray
    ) -> Dict:
        """
        算法三：曲率-亮度联合检测
        
        核心逻辑：
        - 高曲率（尖锐突起）+ 低梯度（无边界墙）= T4 突破
        - 高曲率 + 高梯度 = 正常褶皱（T3）
        
        Risk = f(Curvature) × f(1/Gradient)
        """
        # 归一化曲率（只关心凸向外的部分）
        # 正曲率 = 凸向外
        positive_curvature = np.maximum(curvatures, 0)
        curv_max = np.percentile(positive_curvature, 95)
        if curv_max > 0:
            normalized_curvature = positive_curvature / curv_max
        else:
            normalized_curvature = positive_curvature
        
        # 梯度越低，风险越高
        inv_gradient = 1 - np.clip(boundary_strengths, 0, 1)
        
        # 联合风险分数
        # 高曲率 × 低梯度 = 高风险
        risk_scores = normalized_curvature * inv_gradient
        
        # 平滑风险分数
        kernel = np.ones(5) / 5
        padded = np.concatenate([risk_scores[-2:], risk_scores, risk_scores[:2]])
        smoothed_risk = np.convolve(padded, kernel, mode='valid')
        
        # 找到高风险点
        high_risk_threshold = np.percentile(smoothed_risk, 90)
        high_risk_mask = smoothed_risk > high_risk_threshold
        high_risk_regions = self._find_continuous_regions(np.where(high_risk_mask)[0], min_length=3)
        
        return {
            'curvatures': curvatures,
            'normalized_curvature': normalized_curvature,
            'risk_scores': smoothed_risk,
            'max_risk': float(np.max(smoothed_risk)),
            'mean_risk': float(np.mean(smoothed_risk)),
            'high_risk_regions': high_risk_regions,
            'num_high_risk_regions': len(high_risk_regions),
        }
    
    def _find_continuous_regions(self, indices: np.ndarray, min_length: int = 3) -> List[Dict]:
        """找到连续的索引区域"""
        if len(indices) == 0:
            return []
        
        regions = []
        start = indices[0]
        prev = indices[0]
        
        for i in range(1, len(indices)):
            if indices[i] - prev <= 2:  # 允许小间隙
                prev = indices[i]
            else:
                if prev - start + 1 >= min_length:
                    regions.append({
                        'start': int(start),
                        'end': int(prev),
                        'length': int(prev - start + 1),
                    })
                start = indices[i]
                prev = indices[i]
        
        if prev - start + 1 >= min_length:
            regions.append({
                'start': int(start),
                'end': int(prev),
                'length': int(prev - start + 1),
            })
        
        return regions
    
    # ==================== 综合分析 ====================
    
    def analyze_image(
        self, 
        image_path: str, 
        annotation_path: str,
        visualize: bool = True,
        output_dir: Optional[str] = None
    ) -> Dict:
        """
        综合分析单张图像
        """
        # 加载图像
        image = cv2.imread(image_path)
        if image is None:
            raise ValueError(f"Cannot load image: {image_path}")
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        
        # 加载标注
        points, image_size = self.load_annotation(annotation_path)
        
        # 创建 mask 并获取轮廓
        mask = self.create_mask_from_points(points, image_size)
        contour = self.get_smooth_contour(mask, num_points=360)
        normals = self.compute_normals(contour)
        curvatures = self.compute_curvature(contour)
        
        # 计算形态学特征
        morphology = self.compute_morphology_features(mask, contour)
        
        # 运行三个算法
        result1 = self.algorithm1_normal_gradient(gray, contour, normals)
        result2 = self.algorithm2_bilinear_correlation(gray, contour, normals)
        result3 = self.algorithm3_curvature_gradient(
            gray, contour, normals, curvatures, result1['boundary_strengths']
        )
        
        # 综合评分
        # SII (Serosal Integrity Index) 基于算法一
        sii = result1['weakest_10_percentile']
        
        # BCI (Boundary Correlation Index) 基于算法二
        # 高相关性 = 低分（突破）
        bci = 1 - np.clip(result2['mean_correlation'], 0, 1)
        
        # CRI (Curvature Risk Index) 基于算法三
        cri = 1 - result3['mean_risk']
        
        # 综合分数 (加权平均)
        composite_score = 0.5 * sii + 0.3 * bci + 0.2 * cri
        
        # 统计危险区域
        total_danger_regions = (
            result1['num_weak_regions'] + 
            result2['num_breach_regions'] + 
            result3['num_high_risk_regions']
        )
        
        # ==================== 改进的 T 分期预测逻辑 ====================
        # 结合形态学特征（肿瘤大小）和边界特征
        
        tumor_size = morphology['equivalent_diameter_mm']
        irregularity = morphology['irregularity']
        circularity = morphology['circularity']
        
        # 大小分类阈值 (mm)
        SMALL_THRESHOLD = 15   # <15mm 为小肿瘤
        MEDIUM_THRESHOLD = 30  # 15-30mm 为中等
        LARGE_THRESHOLD = 50   # >50mm 为大肿瘤
        
        # 边界强度分类
        # 小肿瘤对边界强度要求更宽松（因为小肿瘤可能在暗区）
        # 大肿瘤边界应该更清晰
        
        if tumor_size < SMALL_THRESHOLD:
            # 小肿瘤：主要看形状规则度
            if circularity > 0.7 and irregularity < 1.3:
                # 小且规则 → 倾向 T1/T2
                if sii > 0.2:
                    predicted_stage = 'T1-T2'
                    confidence = 'Medium'
                    explanation = f'小肿瘤(Ø{tumor_size:.1f}mm)，形状规则，边界可见(SII:{sii:.2f})，倾向早期'
                else:
                    predicted_stage = 'T2-T3'
                    confidence = 'Low'
                    explanation = f'小肿瘤(Ø{tumor_size:.1f}mm)，边界较弱(SII:{sii:.2f})，需进一步评估'
            else:
                # 小但不规则 → 可能 T2-T3
                predicted_stage = 'T2-T3'
                confidence = 'Low'
                explanation = f'小肿瘤(Ø{tumor_size:.1f}mm)，形状不规则，建议综合评估'
                
        elif tumor_size < MEDIUM_THRESHOLD:
            # 中等肿瘤：边界和形状都考虑
            if sii > 0.35 and circularity > 0.6:
                predicted_stage = 'T2'
                confidence = 'Medium'
                explanation = f'中等肿瘤(Ø{tumor_size:.1f}mm)，边界清晰(SII:{sii:.2f})，倾向T2'
            elif sii > 0.25:
                predicted_stage = 'T3'
                confidence = 'Medium'
                explanation = f'中等肿瘤(Ø{tumor_size:.1f}mm)，边界一般(SII:{sii:.2f})，倾向T3'
            elif sii > 0.15:
                predicted_stage = 'T3-T4'
                confidence = 'Medium'
                explanation = f'中等肿瘤(Ø{tumor_size:.1f}mm)，边界较弱(SII:{sii:.2f})，可能浆膜侵犯'
            else:
                predicted_stage = 'T4'
                confidence = 'High'
                explanation = f'中等肿瘤(Ø{tumor_size:.1f}mm)，边界模糊(SII:{sii:.2f})，高度怀疑T4'
                
        elif tumor_size < LARGE_THRESHOLD:
            # 较大肿瘤：边界是关键
            if sii > 0.3:
                predicted_stage = 'T3'
                confidence = 'Medium'
                explanation = f'较大肿瘤(Ø{tumor_size:.1f}mm)，边界可见(SII:{sii:.2f})，倾向T3'
            elif sii > 0.2:
                predicted_stage = 'T3-T4'
                confidence = 'Medium'
                explanation = f'较大肿瘤(Ø{tumor_size:.1f}mm)，边界较弱(SII:{sii:.2f})，可能浆膜侵犯'
            else:
                predicted_stage = 'T4'
                confidence = 'High'
                explanation = f'较大肿瘤(Ø{tumor_size:.1f}mm)，边界模糊(SII:{sii:.2f})，高度怀疑浆膜突破'
        else:
            # 巨大肿瘤：几乎肯定是晚期
            if sii > 0.25:
                predicted_stage = 'T3-T4'
                confidence = 'Medium'
                explanation = f'巨大肿瘤(Ø{tumor_size:.1f}mm)，边界部分可见(SII:{sii:.2f})'
            else:
                predicted_stage = 'T4'
                confidence = 'High'
                explanation = f'巨大肿瘤(Ø{tumor_size:.1f}mm)，边界模糊(SII:{sii:.2f})，高度怀疑T4'
        
        # 危险区域修正
        if total_danger_regions >= 5 and 'T4' not in predicted_stage:
            # 多个危险区域，提高分期
            if predicted_stage == 'T2':
                predicted_stage = 'T2-T3'
            elif predicted_stage == 'T3':
                predicted_stage = 'T3-T4'
            explanation += f'；发现{total_danger_regions}个危险区域'
        
        results = {
            'image_path': image_path,
            'annotation_path': annotation_path,
            'sii': float(sii),
            'bci': float(bci),
            'cri': float(cri),
            'composite_score': float(composite_score),
            'predicted_t_stage': predicted_stage,
            'confidence': confidence,
            'explanation': explanation,
            'morphology': morphology,
            'algorithm1': result1,
            'algorithm2': result2,
            'algorithm3': result3,
            'total_danger_regions': total_danger_regions,
        }
        
        # 可视化
        if visualize:
            self._visualize_results(
                image, gray, contour, normals,
                result1, result2, result3, results,
                output_dir, Path(image_path).stem
            )
        
        return results
    
    def _visualize_results(
        self, 
        image: np.ndarray,
        gray: np.ndarray,
        contour: np.ndarray,
        normals: np.ndarray,
        result1: Dict,
        result2: Dict,
        result3: Dict,
        results: Dict,
        output_dir: Optional[str],
        filename: str
    ):
        """生成可视化结果（不弹窗）"""
        fig = plt.figure(figsize=(20, 12))
        
        # 1. 风险地图（算法一：梯度强度）
        ax1 = fig.add_subplot(2, 4, 1)
        ax1.imshow(cv2.cvtColor(image, cv2.COLOR_BGR2RGB))
        
        strengths = result1['boundary_strengths']
        for i in range(len(contour) - 1):
            strength = strengths[i]
            if strength > 0.3:
                color = (0, 0.8, 0)  # 绿色 - 强边界
            elif strength > 0.15:
                color = (1, 0.8, 0)  # 黄色 - 中等
            else:
                color = (1, 0, 0)    # 红色 - 弱边界
            ax1.plot([contour[i, 0], contour[i+1, 0]], 
                    [contour[i, 1], contour[i+1, 1]], 
                    color=color, linewidth=2)
        
        ax1.set_title(f'Gradient Strength (SII: {results["sii"]:.2f})', fontsize=10)
        ax1.axis('off')
        
        # 2. 双轨差异图（算法二）
        ax2 = fig.add_subplot(2, 4, 2)
        ax2.imshow(cv2.cvtColor(image, cv2.COLOR_BGR2RGB))
        
        diffs = result2['diff_values']
        diff_max = np.percentile(diffs, 95)
        for i in range(len(contour) - 1):
            diff = diffs[i] / diff_max if diff_max > 0 else 0
            if diff > 0.5:
                color = (0, 0.8, 0)  # 绿色 - 差异大（正常）
            elif diff > 0.25:
                color = (1, 0.8, 0)  # 黄色
            else:
                color = (1, 0, 0)    # 红色 - 差异小（同质化）
            ax2.plot([contour[i, 0], contour[i+1, 0]], 
                    [contour[i, 1], contour[i+1, 1]], 
                    color=color, linewidth=2)
        
        ax2.set_title(f'Inner-Outer Diff (Corr: {result2["mean_correlation"]:.2f})', fontsize=10)
        ax2.axis('off')
        
        # 3. 曲率-风险图（算法三）
        ax3 = fig.add_subplot(2, 4, 3)
        ax3.imshow(cv2.cvtColor(image, cv2.COLOR_BGR2RGB))
        
        risks = result3['risk_scores']
        for i in range(len(contour) - 1):
            risk = risks[i]
            if risk < 0.2:
                color = (0, 0.8, 0)  # 绿色 - 低风险
            elif risk < 0.5:
                color = (1, 0.8, 0)  # 黄色
            else:
                color = (1, 0, 0)    # 红色 - 高风险
            ax3.plot([contour[i, 0], contour[i+1, 0]], 
                    [contour[i, 1], contour[i+1, 1]], 
                    color=color, linewidth=2)
        
        ax3.set_title(f'Curvature Risk (Max: {result3["max_risk"]:.2f})', fontsize=10)
        ax3.axis('off')
        
        # 4. 综合风险图
        ax4 = fig.add_subplot(2, 4, 4)
        ax4.imshow(cv2.cvtColor(image, cv2.COLOR_BGR2RGB))
        
        # 综合三个算法的结果
        combined = (
            (1 - strengths) * 0.5 +  # 梯度弱 = 高风险
            (1 - diffs / (diff_max + 1e-6)) * 0.3 +  # 差异小 = 高风险
            risks * 0.2
        )
        
        for i in range(len(contour) - 1):
            risk = combined[i]
            if risk < 0.3:
                color = (0, 0.8, 0)
            elif risk < 0.5:
                color = (1, 0.8, 0)
            else:
                color = (1, 0, 0)
            ax4.plot([contour[i, 0], contour[i+1, 0]], 
                    [contour[i, 1], contour[i+1, 1]], 
                    color=color, linewidth=2.5)
        
        ax4.set_title(f'Combined: {results["predicted_t_stage"]}', fontsize=10, fontweight='bold')
        ax4.axis('off')
        
        # 5. 梯度强度曲线
        ax5 = fig.add_subplot(2, 4, 5)
        angles = np.linspace(0, 360, len(strengths), endpoint=False)
        ax5.fill_between(angles, strengths, alpha=0.3, color='blue')
        ax5.plot(angles, strengths, 'b-', linewidth=1)
        ax5.axhline(y=0.15, color='r', linestyle='--', alpha=0.7, label='Weak threshold')
        ax5.set_xlabel('Angle (degrees)')
        ax5.set_ylabel('Gradient Strength')
        ax5.set_title('Algorithm 1: Normal Gradient')
        ax5.legend(fontsize=8)
        ax5.set_xlim(0, 360)
        ax5.set_ylim(0, 1)
        ax5.grid(True, alpha=0.3)
        
        # 6. 内外轨差异曲线
        ax6 = fig.add_subplot(2, 4, 6)
        ax6.plot(angles, result2['inner_values'], 'b-', alpha=0.7, label='Inner track')
        ax6.plot(angles, result2['outer_values'], 'r-', alpha=0.7, label='Outer track')
        ax6.fill_between(angles, result2['inner_values'], result2['outer_values'], 
                        alpha=0.2, color='green')
        ax6.set_xlabel('Angle (degrees)')
        ax6.set_ylabel('Intensity')
        ax6.set_title('Algorithm 2: Bilinear Tracks')
        ax6.legend(fontsize=8)
        ax6.set_xlim(0, 360)
        ax6.grid(True, alpha=0.3)
        
        # 7. 曲率和风险曲线
        ax7 = fig.add_subplot(2, 4, 7)
        ax7.plot(angles, result3['normalized_curvature'], 'g-', alpha=0.7, label='Curvature')
        ax7.plot(angles, risks, 'r-', linewidth=1.5, label='Risk Score')
        ax7.set_xlabel('Angle (degrees)')
        ax7.set_ylabel('Value')
        ax7.set_title('Algorithm 3: Curvature-Risk')
        ax7.legend(fontsize=8)
        ax7.set_xlim(0, 360)
        ax7.grid(True, alpha=0.3)
        
        # 8. 诊断报告
        ax8 = fig.add_subplot(2, 4, 8)
        ax8.axis('off')
        
        morph = results.get('morphology', {})
        report = f"""
DIAGNOSIS REPORT
{'='*40}

Predicted T-Stage: {results['predicted_t_stage']}
Confidence: {results['confidence']}

MORPHOLOGY:
{'─'*40}
Diameter: {morph.get('equivalent_diameter_mm', 0):.1f} mm
Area: {morph.get('area_mm2', 0):.1f} mm²
Circularity: {morph.get('circularity', 0):.2f}
Irregularity: {morph.get('irregularity', 0):.2f}

BOUNDARY METRICS:
{'─'*40}
1. SII (Serosal Integrity): {results['sii']:.3f}
   Weak regions: {result1['num_weak_regions']}

2. BCI (Boundary Corr): {results['bci']:.3f}
   Breach regions: {result2['num_breach_regions']}

3. CRI (Curvature Risk): {results['cri']:.3f}
   High risk: {result3['num_high_risk_regions']}

Total Danger Zones: {results['total_danger_regions']}

{'─'*40}
{results['explanation']}
{'='*40}
"""
        ax8.text(0.02, 0.98, report, transform=ax8.transAxes, 
                fontsize=8, verticalalignment='top', fontfamily='monospace',
                bbox=dict(boxstyle='round', facecolor='lightyellow', alpha=0.8))
        
        plt.tight_layout()
        
        if output_dir:
            os.makedirs(output_dir, exist_ok=True)
            output_path = os.path.join(output_dir, f"{filename}_analysis_v3.png")
            plt.savefig(output_path, dpi=150, bbox_inches='tight')
            print(f"Saved: {output_path}")
        
        plt.close(fig)


def main():
    """测试脚本"""
    extractor = ExplainableFeatureExtractorV3(
        tolerance_pixels=8,
        track_offset=5,
        window_size=11,
        pixel_spacing=0.1
    )
    
    base_dir = Path("/Users/huangyijun/Projects/胃癌T分期/Gastric_Cancer_Dataset")
    images_dir = base_dir / "images"
    annotations_dir = base_dir / "annotations"
    output_dir = base_dir / "explainable_analysis_v3"
    
    # 测试不同分期的病例
    # 文件名规则: Chemo/Surgery_[T分期]MC/M_ID (序号).jpg
    # 1M/1MC = T1, 2M/2MC = T2, 3M/3MC = T3, 4M/4MC = T4
    test_cases = [
        # T4 病例
        ("Chemo_4MC_1444273 (1).jpg", "T4"),
        ("Chemo_4MC_1444273 (5).jpg", "T4"),
        ("Surgery_4M_1483646 (1).jpg", "T4"),
        # T3 病例
        ("Chemo_3MC_1444744 (2).jpg", "T3"),
        ("Chemo_3MC_1444744 (1).jpg", "T3"),
        # T2 病例
        ("Chemo_2MC_1412595 (2).jpg", "T2"),
        ("Chemo_2MC_1396900 (1).jpg", "T2"),
        ("Chemo_2MC_1448235 (1).jpg", "T2"),
        # T1 病例
        ("Chemo_1MC_1410481 (1).jpg", "T1"),
        ("Chemo_1MC_1424711 (1).jpg", "T1"),
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
            
            # 简化结果用于保存
            save_results = {
                'image': img_name,
                'expected': expected,
                'predicted': results['predicted_t_stage'],
                'confidence': results['confidence'],
                'sii': results['sii'],
                'bci': results['bci'],
                'cri': results['cri'],
                'composite_score': results['composite_score'],
                'total_danger_regions': results['total_danger_regions'],
                'explanation': results['explanation'],
            }
            results_list.append(save_results)
            
            match = '✓' if expected in results['predicted_t_stage'] else '✗'
            print(f"\nResults: {match}")
            print(f"  - Predicted: {results['predicted_t_stage']} ({results['confidence']})")
            print(f"  - SII: {results['sii']:.3f}")
            print(f"  - BCI: {results['bci']:.3f}")
            print(f"  - CRI: {results['cri']:.3f}")
            print(f"  - Composite: {results['composite_score']:.3f}")
            print(f"  - Danger Zones: {results['total_danger_regions']}")
            
        except Exception as e:
            print(f"Error: {e}")
            import traceback
            traceback.print_exc()
    
    # 保存汇总
    if results_list:
        import json as json_module
        summary_path = output_dir / "analysis_summary_v3.json"
        with open(summary_path, 'w') as f:
            json_module.dump(results_list, f, indent=2, ensure_ascii=False)
        print(f"\nSummary saved to: {summary_path}")
        
        # 打印准确率
        correct = sum(1 for r in results_list if r['expected'] in r['predicted'])
        print(f"\nAccuracy: {correct}/{len(results_list)} = {correct/len(results_list)*100:.1f}%")


if __name__ == "__main__":
    main()

