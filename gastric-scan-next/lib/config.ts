import path from 'path';

// Dataset Roots
export const DATASET_ORIGINAL_ROOT = path.resolve(process.cwd(), '../Gastric_Cancer_Dataset');
export const DATASET_CROPPED_ROOT = path.resolve(process.cwd(), '../Gastric_Cancer_Dataset_Cropped');
export const DATASET_2019_CROPPED_ROOT = path.resolve(process.cwd(), '../2019年直接手术/Cropped');
export const DATASET_2024_CROPPED_ROOT = path.resolve(process.cwd(), '../Gastric_Cancer_Dataset_2024_Cropped');
export const DATASET_2019_ROOT = path.resolve(process.cwd(), '../2019年直接手术');

export type DatasetType = 'original' | 'cropped';
export type CohortYear = '2019' | '2024' | '2025';
export type TreatmentType = 'surgery' | 'nac'; // surgery: 直接手术, nac: 新辅助治疗

export function getDatasetPaths(dataset: DatasetType, cohortYear: CohortYear = '2025', treatmentType: TreatmentType = 'surgery') {
  // 新辅助治疗数据路径
  if (treatmentType === 'nac') {
    if (cohortYear === '2019') {
      const root = path.resolve(process.cwd(), '../Gastric_Cancer_Dataset_2019_nac');
      return {
        root,
        images: path.join(root, 'images'),
        overlays: path.join(root, 'overlays'),
        overlaysTransparent: path.join(root, 'lymph_node_analysis'),
        annotations: path.join(root, 'annotations')
      };
    }
    if (cohortYear === '2024') {
      const root = path.resolve(process.cwd(), '../Gastric_Cancer_Dataset_2024_nac');
      return {
        root,
        images: path.join(root, 'images'),
        overlays: path.join(root, 'overlays'),
        overlaysTransparent: path.join(root, 'lymph_node_analysis'),
        annotations: path.join(root, 'annotations')
      };
    }
    if (cohortYear === '2025') {
      // 2025年NAC数据也在Gastric_Cancer_Dataset中，但文件名以Chemo_开头
      // 或者需要检查是否有单独的NAC目录
      const root = dataset === 'cropped' ? DATASET_CROPPED_ROOT : DATASET_ORIGINAL_ROOT;
      return {
        root,
        images: path.join(root, 'images'),
        overlays: path.join(root, 'overlays'),
        overlaysTransparent: path.join(root, 'lymph_node_analysis'),
        annotations: path.join(root, 'annotations')
      };
    }
  }
  
  // 直接手术数据路径
  if (cohortYear === '2019') {
    const root = dataset === 'cropped'
      ? DATASET_2019_CROPPED_ROOT
      : path.resolve(process.cwd(), '../Gastric_Cancer_Dataset_2019');
    return {
      root,
      images: path.join(root, 'images'),
      overlays: path.join(root, 'overlays'),
      overlaysTransparent: path.join(root, 'lymph_node_analysis'),
      annotations: path.join(root, 'annotations')
    };
  }
  
  if (cohortYear === '2024') {
    const root = dataset === 'cropped'
      ? DATASET_2024_CROPPED_ROOT
      : path.resolve(process.cwd(), '../Gastric_Cancer_Dataset_2024');
    return {
      root,
      images: path.join(root, 'images'),
      overlays: path.join(root, 'overlays'),
      overlaysTransparent: path.join(root, 'lymph_node_analysis'),
      annotations: path.join(root, 'annotations')
    };
  }
  
  // 2025年数据路径（默认）
  const root = dataset === 'cropped' ? DATASET_CROPPED_ROOT : DATASET_ORIGINAL_ROOT;
  return {
    root,
    images: path.join(root, 'images'),
    overlays: path.join(root, 'overlays'),
    overlaysTransparent: path.join(root, 'lymph_node_analysis'),
    annotations: path.join(root, 'annotations')
  };
}

export function getClinicalDataPath(cohortYear: CohortYear = '2025', treatmentType: TreatmentType = 'surgery'): string {
  // 新辅助治疗临床数据路径
  if (treatmentType === 'nac') {
    if (cohortYear === '2019') {
      return path.join(process.cwd(), 'data', 'clinical_data_2019_nac.json');
    }
    if (cohortYear === '2024') {
      return path.join(process.cwd(), 'data', 'clinical_data_2024_nac.json');
    }
  }
  
  // 直接手术临床数据路径
  if (cohortYear === '2019') {
    return path.join(process.cwd(), 'data', 'clinical_data_2019.json');
  }
  if (cohortYear === '2024') {
    return path.join(process.cwd(), 'data', 'clinical_data_2024.json');
  }
  return path.join(process.cwd(), 'data', 'clinical_data.json');
}
