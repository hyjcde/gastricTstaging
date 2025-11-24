import { CONCEPT_CONFIGS } from './medical-config';
import { ConceptState, Patient } from '@/types';

export interface DiagnosisResult {
  tStage: string;
  nStage: string;
  probabilities: {
    t4: number;
    t3: number;
    t2: number; // T1/T2
    n3: number;
    n2: number;
    n1: number;
    n0: number;
  };
  confidence: {
    t: number;
    n: number;
    overall: number;
  };
  scores: {
    t: number;
    n: number;
  };
  flags: {
    isT4: boolean;
    hasMetastasis: boolean;
    highRisk: boolean;
  };
}

export function calculateDiagnosis(state: ConceptState): DiagnosisResult {
  // ---------------------------------------------------------
  // Enhanced Logic for Probabilities (Based on updated CBM)
  // ---------------------------------------------------------
  
  // T-Stage Logic
  const proliferationScore = state.c1 * 0.4 + state.c3 * 0.3;
  const invasionScore = (state.vascularInvasion ? 30 : 0) + (state.neuralInvasion ? 20 : 0);
  const diffVal = state.differentiation || 2;
  const differentiationPenalty = (diffVal - 1) * 8; 
  const tScore = Math.min(100, proliferationScore * 0.5 + invasionScore + differentiationPenalty);
  
  const probT4 = Math.max(0, Math.min(100, tScore));
  const probT3 = Math.max(0, Math.min(100, (100 - probT4) * 0.7));
  const probT2 = 100 - probT4 - probT3;

  const isT4 = probT4 > 60;
  const tStage = isT4 ? "T4a" : (probT3 > 45 ? "T3" : "T1/T2");
  const tConf = Math.floor(Math.max(probT4, probT3, probT2));

  // N-Stage Logic
  const immuneScore = state.c4 * 0.5 + state.c2 * 0.3;
  const microEnvScore = (state.c6 > state.c7) ? 20 : 0; 
  const laurenVal = state.lauren ?? 1;
  const laurenRisk = (laurenVal === 0) ? 30 : (laurenVal === 4 ? 15 : 0);
  const nScore = Math.min(100, immuneScore + microEnvScore + laurenRisk);
  
  const probN3 = Math.max(0, Math.min(100, nScore * 0.8));
  const probN2 = Math.max(0, Math.min(100, (nScore - 30) * 0.6));
  const probN1 = Math.max(0, Math.min(100, (nScore - 20) * 0.5));
  const probN0 = 100 - probN3 - probN2 - probN1;
  
  const nStage = probN3 > 50 ? "N3" : (probN2 > 40 ? "N2" : (probN1 > 30 ? "N1" : "N0"));
  const nConf = Math.floor(Math.max(probN0, probN1, probN2, probN3));
  
  const hasMetastasis = nStage !== "N0";
  const highRisk = isT4 || state.c4 > 60 || state.c3 > 60 || state.vascularInvasion === 1;
  const stageConfidence = Math.floor((tConf + nConf) / 2);

  return {
    tStage,
    nStage,
    probabilities: {
      t4: probT4,
      t3: probT3,
      t2: probT2,
      n3: probN3,
      n2: probN2,
      n1: probN1,
      n0: probN0
    },
    confidence: {
      t: tConf,
      n: nConf,
      overall: stageConfidence
    },
    scores: {
      t: tScore,
      n: nScore
    },
    flags: {
      isT4,
      hasMetastasis,
      highRisk
    }
  };
}

export function getFeatureDescriptions(state: ConceptState, language: 'zh' | 'en') {
  const replaceVal = (text: string, val: number) => text.replace('{val}', val.toString());
  const getDesc = (key: 'c1' | 'c2' | 'c3' | 'c4') => {
    const config = CONCEPT_CONFIGS[key];
    const val = state[key];
    const descs = config.descriptions[language];
    
    if (val >= config.thresholds.danger) return replaceVal(descs.high, val);
    if (val >= config.thresholds.warning) return replaceVal(descs.mid, val);
    return replaceVal(descs.low, val);
  };

  return {
    ki67: getDesc('c1'),
    cps: getDesc('c2'),
    pd1: getDesc('c3'),
    foxp3: getDesc('c4'),
  };
}

export function generateNarrativeReport(
  state: ConceptState, 
  diagnosis: DiagnosisResult, 
  patient: Patient | null, 
  language: 'zh' | 'en'
): string[] {
  const { tStage, nStage, confidence, flags } = diagnosis;
  const lines: string[] = [];
  const timeStr = new Date().toISOString().split('T')[1].substring(0, 8);
  const clin = patient?.clinical;

  const descriptions = getFeatureDescriptions(state, language);

  if (language === 'en') {
    lines.push(`PATIENT ID: ${patient?.id_short ?? 'N/A'}`);
    if (clin) {
        lines.push(`DEMOGRAPHICS: ${clin.sex}, ${clin.age}y | Loc: ${clin.location}`);
    }
    lines.push(`ACQUIRED : ${timeStr} UTC`);
    lines.push(`----------------------------------------`);
    lines.push(`• Ki-67: ${descriptions.ki67}`);
    lines.push(`• CPS: ${descriptions.cps}`);
    lines.push(`• PD-1: ${descriptions.pd1}`);
    lines.push(`• FoxP3: ${descriptions.foxp3}`);
    if (state.vascularInvasion) lines.push(`• Vascular Invasion detected.`);
    if (state.neuralInvasion) lines.push(`• Neural Invasion detected.`);
    lines.push(``);
    lines.push(`T-Stage Assessment: ${tStage} (${confidence.t}% confidence)`);
    lines.push(`N-Stage Assessment: ${nStage} (${confidence.n}% confidence)`);
    
    if (flags.highRisk || flags.hasMetastasis) {
      lines.push(`High-risk flags: consider neoadjuvant protocol.`);
    } else {
      lines.push(`Current signal leans toward localized disease.`);
    }
    lines.push(`>>> FINAL ASSESSMENT: ${tStage}${nStage} (${confidence.overall}% confidence)`);
  } else {
    lines.push(`病人ID: ${patient?.id_short ?? '未知'}`);
    if (clin) {
        lines.push(`基本信息: ${clin.sex === 'Male' ? '男' : '女'}, ${clin.age}岁 | 部位: ${clin.location}`);
    }
    lines.push(`采集时间: ${timeStr} UTC`);
    lines.push(`----------------------------------------`);
    lines.push(`• Ki-67：${descriptions.ki67}`);
    lines.push(`• CPS：${descriptions.cps}`);
    lines.push(`• PD-1：${descriptions.pd1}`);
    lines.push(`• FoxP3：${descriptions.foxp3}`);
    if (state.vascularInvasion) lines.push(`• 存在脉管侵犯 (LVI)`);
    if (state.neuralInvasion) lines.push(`• 存在神经侵犯 (PNI)`);
    lines.push(``);
    lines.push(`T分期评估：${tStage}（置信度 ${confidence.t}%）`);
    lines.push(`N分期评估：${nStage}（置信度 ${confidence.n}%）`);
    if (flags.hasMetastasis) {
      lines.push(`[!] 检测到淋巴结转移风险。风险等级：${nStage === 'N3' ? '高危' : nStage === 'N2' ? '中危' : '低危'}`);
    } else {
      lines.push(`[✓] 未发现显著淋巴结转移特征（N0）。`);
    }
    lines.push(``);
    if (clin) {
        lines.push(`临床相关性分析:`);
        lines.push(`病理提示${clin.pathology.differentiation}腺癌 (${clin.pathology.lauren})。`);
        lines.push(`术后病理金标准: pT${clin.pathology.pT} pN${clin.pathology.pN} pM${clin.pathology.pM} (Stage ${clin.pathology.pStage})`);
        lines.push(``);
    }
    lines.push(`模型综合推断分期 ${tStage}${nStage}，综合置信度 ${confidence.overall}%。`);
    if (flags.highRisk || flags.hasMetastasis) {
      lines.push(`高危提示：建议补充增强CT，并尽快评估是否进入新辅助方案。`);
    } else {
      lines.push(`倾向局限病灶，建议密切随访。`);
    }
    lines.push(`>>> 综合诊断结论：${tStage}${nStage}（置信度 ${confidence.overall}%）`);
  }
  return lines;
}

export function generateSummaryPoints(
  state: ConceptState,
  diagnosis: DiagnosisResult,
  patient: Patient | null,
  language: 'zh' | 'en'
): string[] {
  const { tStage, nStage, flags } = diagnosis;
  
  const inferencePoint = language === 'zh'
    ? `模型结合 Ki-67/CPS/FoxP3/Lauren分型 推断 ${tStage}${nStage}，侵犯与微环境指标支持该结论。`
    : `Model fuses Ki-67/CPS/FoxP3/Lauren dynamics to infer ${tStage}${nStage}, supported by invasion/TME markers.`;

  const clinicalCorrelation = patient?.clinical
    ? language === 'zh'
      ? `病理示${patient.clinical.pathology.differentiation || '腺癌'}（${patient.clinical.pathology.lauren || 'N/A'}），CEA ${patient.clinical.biomarkers.cea ?? 'N/A'}${patient.clinical.biomarkers.cea_positive ? ' +' : ''}。`
      : `Pathology reports ${patient.clinical.pathology.differentiation || 'adenocarcinoma'} (${patient.clinical.pathology.lauren || 'N/A'}); biomarkers CEA ${patient.clinical.biomarkers.cea ?? 'N/A'}${patient.clinical.biomarkers.cea_positive ? ' +' : ''}.`
    : language === 'zh'
      ? '临床/病理数据待补录。'
      : 'Clinical/pathology data pending.';

  const actionPoint = flags.highRisk
    ? language === 'zh'
      ? '高危预警：建议多学科(MDT)讨论，特别是关于新辅助治疗的介入时机。'
      : 'High Risk Alert: Recommend MDT discussion regarding timing of neoadjuvant therapy.'
    : language === 'zh'
      ? '低危提示：建议定期复查监测 Ki-67 及免疫指标变化。'
      : 'Low Risk: Monitor Ki-67 and immune markers regularly.';

  return [inferencePoint, clinicalCorrelation, actionPoint];
}

