---
title: Data Preprocessing Scripts
description: Usage guide and workflow for every preprocessing script maintained under `scripts/`.
---

# 数据预处理脚本集合

本项目将所有与数据清洗、格式转换、提取定义、批量裁剪等预处理相关的脚本统一维护在 `scripts/` 目录下。为便于科研/工程复现，以下按照功能分类列出所有脚本、依赖与典型调用方式。

## 1. 先决条件

- **Python 3.10+**（推荐使用已有虚拟环境）
- **依赖库**：
  ```bash
  pip install pandas numpy matplotlib pydicom nibabel
  ```
  只要脚本在 `scripts/` 目录现有依赖，如 `pandas`、`numpy` 就可以直接工作。
- **运行位置**：所有脚本预计从项目根目录运行（`/Users/huangyijun/Projects/胃癌T分期`），若脚本中使用相对路径请注意当前工作目录。

## 2. 转换/格式清洗类

| 脚本 | 描述 | 示例 |
| --- | --- | --- |
| `convert_data.py` | 通用转换入口，可用于将原始 Excel/CSV 转为统一格式。 | `python scripts/convert_data.py --input raw.xlsx --output cleaned.json` |
| `convert_clinical_data.py`（及 `..._2019.py` / `..._2024.py` / `..._2024_nac.py` / `..._2019_nac.py`） | 针对不同 cohort 的分期表做字段清洗、编码一致性处理（性别、分化程度等），输出 `gastric-scan-next/data/clinical_data*.json`。 | `python scripts/convert_clinical_data_2024.py` |
| `inspect_excel.py` | 可视化检查 Excel 中的空值、列名一致性（辅助确认列名变化）。 | `python scripts/inspect_excel.py 2025胃癌临床整理.xlsx` |
| `patient_split.py` | 根据已有 clinical data 和 annotations 生成 train/val/test 分割，当前配置写入 `splits/`。 | `python scripts/patient_split.py --ratio 0.8 0.1 0.1` |

## 3. 图像裁剪与增强类

| 脚本 | 描述 | 示例 |
| --- | --- | --- |
| `crop_tool.py` | 简单交互/批量裁剪 DICOM/JPG，供后续模型推理；调节 ROI 和输出目录。 | `python scripts/crop_tool.py --input dataset/images --output dataset/cropped` |
| `batch_crop.py` | 批量调用 `crop_tool`，按目录结构批量裁切；可用于多 center 数据。 | `python scripts/batch_crop.py --dir 2024年胃癌直接手术/DICOM1` |
| `crop_year_dataset.py` | 根据 2025 pipeline 的 ROI 批量裁剪 2019/2024 的 `images`、`overlays`、`annotations`，写入 `Cropped` 目录，用于前端 `dataset=cropped`。 | `python scripts/crop_year_dataset.py --year 2019` |
| `batch_convert.py` | 转换 DICOM → PNG/JPG 并统一保存，常用于前端资源准备。 | `python scripts/batch_convert.py --source DICOM --target images` |
| `cleanup_nii_only_images.py` | 清理仅包含 `.nii` 的目录（例如转换后残留文件），保持数据目录干净。 | `python scripts/cleanup_nii_only_images.py` |

## 4. 影像/标注分析 & 可视化

| 脚本 | 描述 | 示例 |
| --- | --- | --- |
| `regenerate_overlays.py` / `regenerate_overlays_from_json.py` | 从 JSON 重新生成 overlay 图谱，用于 segmentation 可视化或生成透明图层。 | `python scripts/regenerate_overlays.py --input annotations --output overlays` |
| `visualize_overlays.py` | 快速把 overlay 和原图叠加以 PNG 方式输出，便于检查对齐质量。 | `python scripts/visualize_overlays.py patient_id` |
| `process_2019_project.py` / `process_2024_project.py` / `process_2024_nac_project.py` / (and `_nac` variants) | 高层流程脚本，会调用上述多个工具（alignment、overlay、NII 转换），用于完整 preprocessing pipeline。 | `python scripts/process_2024_project.py` |
| `process_2019_nac_project.py` / `process_2024_nac_project.py` | NAC 专用流程，包含 overlay/alignment/annotation 处理。 | `python scripts/process_2019_nac_project.py` |

## 5. Annotation / Concept Extraction

| 脚本 | 描述 | 示例 |
| --- | --- | --- |
| `extract_pathology_concepts.py` | 从 `2025胃癌临床整理.xlsx` 提取 Ki-67、CPS、PD-1、FoxP3、CD3/CD4/CD8 等实际值，输出 `scripts/extracted_pathology_concepts.json`。 | `python scripts/extract_pathology_concepts.py` |
| `merge_clinical_features.py` | 将抽取的 `concept_features` 合并进目标 JSON（`gastric-scan-next/data/clinical_data.json` 等）。 | `python scripts/merge_clinical_features.py` |
| `check_concept_quality.py` | 随机抽样对比 clinics JSON 中的 pathology 文本与提取值，方便质控。 | `python scripts/check_concept_quality.py --count 10` |
| `update_concepts_pipeline.py` | 打包上述流程，依序运行 Extract → Merge；可加入 CI。 | `python scripts/update_concepts_pipeline.py` |

## 6. 其他辅助脚本

| 脚本 | 描述 |
| --- | --- |
| `process_project.py` | 以已有数据目录为基础，将多个处理阶段串联起来，用于整体更新。 |
| `process_2019_data.py` / `process_2024_data.py` / `process_2019_nac_project.py` | 同上，按年份/治疗类型分道处理。 |
| `regenerate_overlays.py` | 重建 overlay 图像。 |
| `batch_crop.py` 等 | 见二、三部分。 |

## 7. 推荐使用流程

1. **更新 Excel → JSON**：`python scripts/extract_pathology_concepts.py` 生成提取内容。
2. **合并入前端数据**：`python scripts/merge_clinical_features.py` 把 concept_features 写回 `gastric-scan-next/data/`。
3. **验证**：`python scripts/check_concept_quality.py --count 5`。
4. **一次执行**：`python scripts/update_concepts_pipeline.py` 可自动完成上述三步。

对于影像类预处理，按需运行 `process_2024_project.py` / `batch_convert.py` 等，可参考脚本注释调整参数。

## 8. 建议

- 将常用命令写入 `Makefile` 或 CI workflow，例如：
  ```make
  update-concepts:
  	python scripts/update_concepts_pipeline.py
  ```
- 如果 Excel 更新，先跑 `extract`，再 `merge`，最后重新部署前端或刷新缓存。
- 影像目录变化时，先 `batch_convert` 然后 `regenerate_overlays`，保持 overlay 与原图对齐。

如需进一步细化某个脚本的参数（例如 `process_2024_project.py` 的 `--cohort` / `--treatment`），可以在脚本头部查阅 `argparse` 部分；也可以告诉我，我帮你把说明补到这里。

