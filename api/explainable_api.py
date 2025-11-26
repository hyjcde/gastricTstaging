"""
可解释性分析 API 服务
Explainable Analysis API Service

提供 RESTful API 接口，供前端调用进行可解释性分析

启动方式:
    uvicorn explainable_api:app --reload --port 8001

或者:
    python explainable_api.py
"""

import os
import sys
import json
import base64
from pathlib import Path
from typing import Optional
from io import BytesIO

import numpy as np
import cv2
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel

# 添加父目录到路径，以便导入 scripts 模块
sys.path.insert(0, str(Path(__file__).parent.parent))
from scripts.explainable_features_v3 import ExplainableFeatureExtractorV3

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt


app = FastAPI(
    title="Gastric Cancer Explainable AI API",
    description="可解释性 AI 分析接口 - 基于法向梯度的边界验证算法",
    version="1.0.0"
)

# CORS 配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 生产环境应该限制
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 初始化特征提取器
extractor = ExplainableFeatureExtractorV3(
    tolerance_pixels=8,
    track_offset=5,
    window_size=11,
    pixel_spacing=0.1
)

# 数据目录
BASE_DIR = Path(__file__).parent.parent / "Gastric_Cancer_Dataset"
IMAGES_DIR = BASE_DIR / "images"
ANNOTATIONS_DIR = BASE_DIR / "annotations"


class AnalysisRequest(BaseModel):
    """分析请求"""
    patient_id: str
    image_name: Optional[str] = None


class AnalysisResponse(BaseModel):
    """分析响应"""
    success: bool
    patient_id: str
    predicted_stage: Optional[str] = None
    confidence: Optional[str] = None
    sii: Optional[float] = None
    bci: Optional[float] = None
    cri: Optional[float] = None
    composite_score: Optional[float] = None
    explanation: Optional[str] = None
    total_danger_regions: Optional[int] = None
    visualization_base64: Optional[str] = None
    error: Optional[str] = None


def generate_visualization_base64(
    image: np.ndarray,
    gray: np.ndarray,
    contour: np.ndarray,
    result1: dict,
    result2: dict,
    result3: dict,
    results: dict
) -> str:
    """生成可视化图像并返回 base64 编码"""
    
    fig = plt.figure(figsize=(16, 10))
    
    # 1. 综合风险地图
    ax1 = fig.add_subplot(2, 3, 1)
    ax1.imshow(cv2.cvtColor(image, cv2.COLOR_BGR2RGB))
    
    strengths = result1['boundary_strengths']
    diffs = result2['diff_values']
    risks = result3['risk_scores']
    diff_max = np.percentile(diffs, 95) if len(diffs) > 0 else 1
    
    # 综合风险
    combined = (
        (1 - strengths) * 0.5 +
        (1 - diffs / (diff_max + 1e-6)) * 0.3 +
        risks * 0.2
    )
    
    for i in range(len(contour) - 1):
        risk = combined[i]
        if risk < 0.3:
            color = (0, 0.8, 0)  # 绿色
        elif risk < 0.5:
            color = (1, 0.8, 0)  # 黄色
        else:
            color = (1, 0, 0)    # 红色
        ax1.plot([contour[i, 0], contour[i+1, 0]], 
                [contour[i, 1], contour[i+1, 1]], 
                color=color, linewidth=2.5)
    
    ax1.set_title(f'Risk Map - {results["predicted_t_stage"]}', fontsize=11, fontweight='bold')
    ax1.axis('off')
    
    # 2. 梯度强度图
    ax2 = fig.add_subplot(2, 3, 2)
    ax2.imshow(cv2.cvtColor(image, cv2.COLOR_BGR2RGB))
    
    for i in range(len(contour) - 1):
        strength = strengths[i]
        if strength > 0.3:
            color = (0, 0.8, 0)
        elif strength > 0.15:
            color = (1, 0.8, 0)
        else:
            color = (1, 0, 0)
        ax2.plot([contour[i, 0], contour[i+1, 0]], 
                [contour[i, 1], contour[i+1, 1]], 
                color=color, linewidth=2)
    
    ax2.set_title(f'Gradient (SII: {results["sii"]:.2f})', fontsize=10)
    ax2.axis('off')
    
    # 3. 内外差异图
    ax3 = fig.add_subplot(2, 3, 3)
    ax3.imshow(cv2.cvtColor(image, cv2.COLOR_BGR2RGB))
    
    for i in range(len(contour) - 1):
        diff = diffs[i] / diff_max if diff_max > 0 else 0
        if diff > 0.5:
            color = (0, 0.8, 0)
        elif diff > 0.25:
            color = (1, 0.8, 0)
        else:
            color = (1, 0, 0)
        ax3.plot([contour[i, 0], contour[i+1, 0]], 
                [contour[i, 1], contour[i+1, 1]], 
                color=color, linewidth=2)
    
    ax3.set_title(f'Inner-Outer Diff', fontsize=10)
    ax3.axis('off')
    
    # 4. 梯度曲线
    ax4 = fig.add_subplot(2, 3, 4)
    angles = np.linspace(0, 360, len(strengths), endpoint=False)
    ax4.fill_between(angles, strengths, alpha=0.3, color='blue')
    ax4.plot(angles, strengths, 'b-', linewidth=1)
    ax4.axhline(y=0.15, color='r', linestyle='--', alpha=0.7, label='Threshold')
    ax4.set_xlabel('Angle')
    ax4.set_ylabel('Gradient')
    ax4.set_title('Boundary Gradient', fontsize=10)
    ax4.set_xlim(0, 360)
    ax4.set_ylim(0, 1)
    ax4.grid(True, alpha=0.3)
    
    # 5. 内外轨对比
    ax5 = fig.add_subplot(2, 3, 5)
    ax5.plot(angles, result2['inner_values'], 'b-', alpha=0.7, label='Inner')
    ax5.plot(angles, result2['outer_values'], 'r-', alpha=0.7, label='Outer')
    ax5.fill_between(angles, result2['inner_values'], result2['outer_values'], 
                    alpha=0.2, color='green')
    ax5.set_xlabel('Angle')
    ax5.set_ylabel('Intensity')
    ax5.set_title('Bilinear Tracks', fontsize=10)
    ax5.legend(fontsize=8)
    ax5.set_xlim(0, 360)
    ax5.grid(True, alpha=0.3)
    
    # 6. 诊断摘要
    ax6 = fig.add_subplot(2, 3, 6)
    ax6.axis('off')
    
    report = f"""
DIAGNOSIS SUMMARY
{'='*35}

Predicted: {results['predicted_t_stage']}
Confidence: {results['confidence']}

METRICS:
- SII (Gradient): {results['sii']:.3f}
- BCI (Boundary): {results['bci']:.3f}  
- CRI (Curvature): {results['cri']:.3f}
- Composite: {results['composite_score']:.3f}

Danger Zones: {results['total_danger_regions']}

{results['explanation']}
"""
    ax6.text(0.05, 0.95, report, transform=ax6.transAxes, 
            fontsize=9, verticalalignment='top', fontfamily='monospace',
            bbox=dict(boxstyle='round', facecolor='lightyellow', alpha=0.8))
    
    plt.tight_layout()
    
    # 保存到内存
    buf = BytesIO()
    plt.savefig(buf, format='png', dpi=120, bbox_inches='tight')
    plt.close(fig)
    buf.seek(0)
    
    # 转换为 base64
    return base64.b64encode(buf.read()).decode('utf-8')


@app.get("/")
async def root():
    """API 根路径"""
    return {
        "message": "Gastric Cancer Explainable AI API",
        "version": "1.0.0",
        "endpoints": {
            "/analyze": "POST - 执行可解释性分析",
            "/patients": "GET - 获取可用患者列表",
            "/health": "GET - 健康检查"
        }
    }


@app.get("/health")
async def health_check():
    """健康检查"""
    return {"status": "healthy"}


@app.get("/patients")
async def list_patients():
    """获取可用患者列表"""
    if not IMAGES_DIR.exists():
        raise HTTPException(status_code=500, detail="Images directory not found")
    
    # 获取所有 jpg 文件
    images = list(IMAGES_DIR.glob("*.jpg"))
    
    # 按患者 ID 分组
    patients = {}
    for img in images:
        name = img.stem
        # 解析文件名: Chemo_4MC_1444273 (1)
        parts = name.split('_')
        if len(parts) >= 3:
            patient_id = parts[2].split(' ')[0]
            t_stage = parts[1][0] if parts[1][0].isdigit() else '?'
            
            if patient_id not in patients:
                patients[patient_id] = {
                    'id': patient_id,
                    't_stage': f'T{t_stage}',
                    'type': parts[0],
                    'images': []
                }
            patients[patient_id]['images'].append(name + '.jpg')
    
    return list(patients.values())


@app.post("/analyze", response_model=AnalysisResponse)
async def analyze_patient(request: AnalysisRequest):
    """
    执行可解释性分析
    
    Args:
        request: 包含 patient_id 和可选的 image_name
        
    Returns:
        分析结果，包括预测分期、各项指标和可视化图像
    """
    try:
        # 查找图像文件
        if request.image_name:
            image_path = IMAGES_DIR / request.image_name
            json_name = request.image_name.replace('.jpg', '.json')
        else:
            # 根据 patient_id 查找第一张图像
            pattern = f"*_{request.patient_id}*.jpg"
            matches = list(IMAGES_DIR.glob(pattern))
            if not matches:
                return AnalysisResponse(
                    success=False,
                    patient_id=request.patient_id,
                    error=f"No images found for patient {request.patient_id}"
                )
            image_path = matches[0]
            json_name = image_path.stem + '.json'
        
        json_path = ANNOTATIONS_DIR / json_name
        
        # 检查文件存在
        if not image_path.exists():
            return AnalysisResponse(
                success=False,
                patient_id=request.patient_id,
                error=f"Image not found: {image_path.name}"
            )
        
        if not json_path.exists():
            return AnalysisResponse(
                success=False,
                patient_id=request.patient_id,
                error=f"Annotation not found: {json_path.name}"
            )
        
        # 加载图像
        image = cv2.imread(str(image_path))
        if image is None:
            return AnalysisResponse(
                success=False,
                patient_id=request.patient_id,
                error="Failed to load image"
            )
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        
        # 加载标注
        points, image_size = extractor.load_annotation(str(json_path))
        
        # 创建 mask 并获取轮廓
        mask = extractor.create_mask_from_points(points, image_size)
        contour = extractor.get_smooth_contour(mask, num_points=360)
        normals = extractor.compute_normals(contour)
        curvatures = extractor.compute_curvature(contour)
        
        # 运行三个算法
        result1 = extractor.algorithm1_normal_gradient(gray, contour, normals)
        result2 = extractor.algorithm2_bilinear_correlation(gray, contour, normals)
        result3 = extractor.algorithm3_curvature_gradient(
            gray, contour, normals, curvatures, result1['boundary_strengths']
        )
        
        # 综合评分
        sii = result1['weakest_10_percentile']
        bci = 1 - np.clip(result2['mean_correlation'], 0, 1)
        cri = 1 - result3['mean_risk']
        composite_score = 0.5 * sii + 0.3 * bci + 0.2 * cri
        
        total_danger_regions = (
            result1['num_weak_regions'] + 
            result2['num_breach_regions'] + 
            result3['num_high_risk_regions']
        )
        
        # T 分期预测
        if sii < 0.15:
            predicted_stage = 'T4'
            confidence = 'High'
            explanation = f'Boundary gradient very weak (SII:{sii:.2f}), highly suspected serosal invasion'
        elif sii < 0.25:
            predicted_stage = 'T4'
            confidence = 'Medium'
            explanation = f'Boundary gradient weak (SII:{sii:.2f}), possible serosal invasion'
        elif sii < 0.35:
            predicted_stage = 'T3-T4'
            confidence = 'Medium'
            explanation = f'Boundary partially blurred (SII:{sii:.2f}), further examination recommended'
        elif sii < 0.45:
            predicted_stage = 'T3'
            confidence = 'Medium'
            explanation = f'Local weak points exist (SII:{sii:.2f}), tends to T3'
        else:
            predicted_stage = 'T2'
            confidence = 'Medium'
            explanation = f'Boundary clear and intact (SII:{sii:.2f}), tends to T2'
        
        results = {
            'sii': float(sii),
            'bci': float(bci),
            'cri': float(cri),
            'composite_score': float(composite_score),
            'predicted_t_stage': predicted_stage,
            'confidence': confidence,
            'explanation': explanation,
            'total_danger_regions': total_danger_regions,
        }
        
        # 生成可视化
        viz_base64 = generate_visualization_base64(
            image, gray, contour, result1, result2, result3, results
        )
        
        return AnalysisResponse(
            success=True,
            patient_id=request.patient_id,
            predicted_stage=predicted_stage,
            confidence=confidence,
            sii=float(sii),
            bci=float(bci),
            cri=float(cri),
            composite_score=float(composite_score),
            explanation=explanation,
            total_danger_regions=total_danger_regions,
            visualization_base64=viz_base64
        )
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return AnalysisResponse(
            success=False,
            patient_id=request.patient_id,
            error=str(e)
        )


if __name__ == "__main__":
    import uvicorn
    print("Starting Explainable AI API server...")
    print(f"Images directory: {IMAGES_DIR}")
    print(f"Annotations directory: {ANNOTATIONS_DIR}")
    uvicorn.run(app, host="0.0.0.0", port=8001)

