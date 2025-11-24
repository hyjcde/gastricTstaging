import { ConceptState, DEFAULT_STATE, Patient, ConceptFeatures } from '@/types';

/**
 * 将字符串格式的概念值转换为数字
 */
function parseConceptValue(value?: string): number {
  if (!value) return 0;
  
  // 移除百分号和空格
  const cleaned = value.toString().replace(/%/g, '').trim();
  
  // 尝试解析为数字
  const num = parseFloat(cleaned);
  if (!isNaN(num)) {
    return Math.max(0, Math.min(100, num));
  }
  
  // 如果无法解析，返回0
  return 0;
}

/**
 * 将字符串格式的分化程度转换为数字
 */
function parseDifferentiation(value?: string): number {
  if (!value) return 3; // 默认中-低分化
  
  const cleaned = value.toString().trim().toLowerCase();
  
  if (cleaned.includes('1') || cleaned.includes('well') || cleaned.includes('高分化')) return 1;
  if (cleaned.includes('2') || cleaned.includes('mod') || cleaned.includes('中分化')) return 2;
  if (cleaned.includes('3') || cleaned.includes('mod-poor') || cleaned.includes('中-低')) return 3;
  if (cleaned.includes('4') || cleaned.includes('poor') || cleaned.includes('低分化')) return 4;
  
  return 5; // Unknown
}

/**
 * 将字符串格式的 Lauren 分型转换为数字
 */
function parseLauren(value?: string): number {
  if (!value) return 1; // 默认肠型
  
  const cleaned = value.toString().trim().toLowerCase();
  
  if (cleaned.includes('0') || cleaned.includes('diffuse') || cleaned.includes('弥漫')) return 0;
  if (cleaned.includes('1') || cleaned.includes('intestinal') || cleaned.includes('肠型')) return 1;
  if (cleaned.includes('4') || cleaned.includes('mixed') || cleaned.includes('混合')) return 4;
  
  return 1; // 默认肠型
}

/**
 * 将字符串格式的侵犯状态转换为数字（0或1）
 */
function parseInvasion(value?: string): number {
  if (!value) return 0;
  
  const cleaned = value.toString().trim().toLowerCase();
  
  if (cleaned.includes('yes') || cleaned.includes('有') || cleaned.includes('1') || cleaned.includes('+')) {
    return 1;
  }
  
  return 0;
}

/**
 * 从患者的临床数据中提取 ConceptState
 * 如果患者有 concept_features，使用它们；否则返回默认状态
 */
export function getConceptStateFromPatient(patient: Patient | null): ConceptState {
  if (!patient?.clinical?.concept_features) {
    return DEFAULT_STATE;
  }

  const features = patient.clinical.concept_features;

  return {
    c1: parseConceptValue(features.ki67),
    c2: parseConceptValue(features.cps),
    c3: parseConceptValue(features.pd1),
    c4: parseConceptValue(features.foxp3),
    c5: parseConceptValue(features.cd3),
    c6: parseConceptValue(features.cd4),
    c7: parseConceptValue(features.cd8),
    differentiation: parseDifferentiation(features.differentiation),
    lauren: parseLauren(features.lauren),
    vascularInvasion: parseInvasion(features.vascular),
    neuralInvasion: parseInvasion(features.neural),
  };
}

