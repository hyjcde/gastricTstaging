#!/usr/bin/env python3
"""
将视频文件与患者静态图数据关联
生成包含视频URL的患者数据JSON
"""

import os
import json
import re
from pathlib import Path
from collections import defaultdict

# 路径配置
PROJECT_ROOT = Path("/Users/huangyijun/Projects/胃癌T分期")
VIDEO_OUTPUT_ROOT = PROJECT_ROOT / "gastric-scan-next/public/videos"
PATIENT_DATA_PATH = PROJECT_ROOT / "gastric-scan-next/public/data/patients.json"
OUTPUT_PATH = PROJECT_ROOT / "gastric-scan-next/public/data/patients_with_videos.json"


def extract_patient_id(filename: str) -> str:
    """
    从文件名提取患者ID
    例如: "1048931-1.mp4" -> "1048931"
          "Z0069343-2.mp4" -> "Z0069343"
    """
    # 移除扩展名
    name = Path(filename).stem
    # 提取ID部分 (去掉 -1, -2 等后缀)
    match = re.match(r'^([A-Za-z]?\d+)', name)
    if match:
        return match.group(1)
    return name


def extract_patient_id_from_image(id_short: str) -> str:
    """
    从图像的 id_short 提取患者ID
    例如: "1048931_pT3N1_001" -> "1048931"
          "Z0069343_pT2N0_002" -> "Z0069343"
    """
    # 尝试匹配 ID_pTxNx_xxx 格式
    match = re.match(r'^([A-Za-z]?\d+)_', id_short)
    if match:
        return match.group(1)
    # 尝试直接匹配数字ID
    match = re.match(r'^([A-Za-z]?\d+)', id_short)
    if match:
        return match.group(1)
    return id_short


def scan_videos() -> dict:
    """
    扫描所有转码后的视频文件
    返回: {patient_id: [video_info, ...]}
    """
    video_map = defaultdict(list)
    
    # 扫描直接手术组
    direct_surgery_path = VIDEO_OUTPUT_ROOT / "direct_surgery"
    if direct_surgery_path.exists():
        for mp4_file in direct_surgery_path.glob("*.mp4"):
            patient_id = extract_patient_id(mp4_file.name)
            video_map[patient_id].append({
                "url": f"/videos/direct_surgery/{mp4_file.name}",
                "filename": mp4_file.name,
                "treatment": "direct_surgery",
                "water_filled": False
            })
        
        # 喝水子目录
        water_path = direct_surgery_path / "water_filled"
        if water_path.exists():
            for mp4_file in water_path.glob("*.mp4"):
                patient_id = extract_patient_id(mp4_file.name)
                video_map[patient_id].append({
                    "url": f"/videos/direct_surgery/water_filled/{mp4_file.name}",
                    "filename": mp4_file.name,
                    "treatment": "direct_surgery",
                    "water_filled": True
                })
    
    # 扫描新辅助治疗组
    neoadjuvant_path = VIDEO_OUTPUT_ROOT / "neoadjuvant"
    if neoadjuvant_path.exists():
        for mp4_file in neoadjuvant_path.glob("*.mp4"):
            patient_id = extract_patient_id(mp4_file.name)
            video_map[patient_id].append({
                "url": f"/videos/neoadjuvant/{mp4_file.name}",
                "filename": mp4_file.name,
                "treatment": "neoadjuvant",
                "water_filled": False
            })
        
        # 喝水子目录
        water_path = neoadjuvant_path / "water_filled"
        if water_path.exists():
            for mp4_file in water_path.glob("*.mp4"):
                patient_id = extract_patient_id(mp4_file.name)
                video_map[patient_id].append({
                    "url": f"/videos/neoadjuvant/water_filled/{mp4_file.name}",
                    "filename": mp4_file.name,
                    "treatment": "neoadjuvant",
                    "water_filled": True
                })
    
    # 对每个患者的视频按文件名排序
    for patient_id in video_map:
        video_map[patient_id].sort(key=lambda x: x["filename"])
    
    return dict(video_map)


def link_videos_to_patients():
    """
    将视频关联到患者数据
    """
    print("=" * 50)
    print("🔗 患者视频关联工具")
    print("=" * 50)
    
    # 扫描视频
    print("\n📹 扫描视频文件...")
    video_map = scan_videos()
    print(f"   找到 {len(video_map)} 个患者的视频")
    
    total_videos = sum(len(v) for v in video_map.values())
    print(f"   共计 {total_videos} 个视频文件")
    
    # 读取患者数据
    print("\n📊 读取患者数据...")
    if not PATIENT_DATA_PATH.exists():
        print(f"   ⚠️ 患者数据文件不存在: {PATIENT_DATA_PATH}")
        print("   将创建仅包含视频的数据文件")
        patients = []
    else:
        with open(PATIENT_DATA_PATH, 'r', encoding='utf-8') as f:
            patients = json.load(f)
        print(f"   找到 {len(patients)} 条患者记录")
    
    # 关联视频
    print("\n🔗 关联视频...")
    linked_count = 0
    patient_ids_with_videos = set()
    
    for patient in patients:
        id_short = patient.get('id_short', '')
        patient_id = extract_patient_id_from_image(id_short)
        
        if patient_id in video_map:
            patient['video_urls'] = video_map[patient_id]
            patient_ids_with_videos.add(patient_id)
            linked_count += 1
    
    print(f"   ✅ 成功关联 {linked_count} 条记录")
    print(f"   📹 涉及 {len(patient_ids_with_videos)} 个患者")
    
    # 检查未匹配的视频
    unmatched_videos = set(video_map.keys()) - patient_ids_with_videos
    if unmatched_videos:
        print(f"\n   ⚠️ {len(unmatched_videos)} 个患者的视频未找到对应图像:")
        for pid in sorted(unmatched_videos)[:10]:
            print(f"      - {pid}")
        if len(unmatched_videos) > 10:
            print(f"      ... 还有 {len(unmatched_videos) - 10} 个")
    
    # 保存结果
    print(f"\n💾 保存到: {OUTPUT_PATH}")
    with open(OUTPUT_PATH, 'w', encoding='utf-8') as f:
        json.dump(patients, f, ensure_ascii=False, indent=2)
    
    # 同时生成视频索引文件
    video_index_path = PROJECT_ROOT / "gastric-scan-next/public/data/video_index.json"
    print(f"💾 保存视频索引: {video_index_path}")
    with open(video_index_path, 'w', encoding='utf-8') as f:
        json.dump(video_map, f, ensure_ascii=False, indent=2)
    
    print("\n" + "=" * 50)
    print("✅ 完成!")
    print("=" * 50)
    
    return patients, video_map


if __name__ == "__main__":
    link_videos_to_patients()

