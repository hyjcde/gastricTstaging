import { ConceptState, DiagnosisResult } from "./types";

export function calculateDiagnosis(state: ConceptState): DiagnosisResult {
  // Simulated Logic based on Concept Bottleneck Model (CBM) weights
  
  // T-Stage is heavily weighted on C1 (Serosa) and C2 (Stiffness)
  const tScore = state.c1 * 0.6 + state.c2 * 0.4;

  let tStage = "T1/T2";
  let tDesc = "局限于肌层";
  let isDanger = false;

  if (tScore > 80) {
    tStage = "T4a";
    tDesc = "浆膜受侵 (Serosa Invaded)";
    isDanger = true;
  } else if (tScore > 50) {
    tStage = "T3";
    tDesc = "穿透浆膜下层";
    isDanger = true;
  }

  // N-Stage weighted on C3 (Blood) and C4 (Nodes)
  // 淋巴结转移预测：基于淋巴结形态(C4)和血流信号(C3)
  const nScore = state.c4 * 0.7 + state.c3 * 0.3;
  let nStage = "N0";
  let nDesc = "无区域淋巴结转移";
  let nColor = "text-success"; // Using Tailwind class names for logic

  // 详细的N分期判断
  if (nScore >= 80) {
    nStage = "N3";
    nDesc = "7个或以上区域淋巴结转移";
    nColor = "text-danger";
  } else if (nScore >= 65) {
    nStage = "N2";
    nDesc = "3-6个区域淋巴结转移";
    nColor = "text-danger";
  } else if (nScore >= 50) {
    nStage = "N1";
    nDesc = "1-2个区域淋巴结转移";
    nColor = "text-warning";
  } else {
    nStage = "N0";
    nDesc = "无区域淋巴结转移";
    nColor = "text-success";
  }

  // Confidence Calculation
  const confidence = Math.min(
    98,
    Math.floor(((tScore + nScore) / 2) * 0.8 + 20)
  );

  // Generate Report Text
  let text = `基于多模态特征分析：\n`;
  if (state.c1 > 60)
    text += `• 灰度图显示浆膜层回声线中断 (置信度 ${state.c1}%)，提示T4期风险较高。\n`;
  else text += `• 浆膜层回声连续性良好，未见明显突破征象。\n`;

  if (state.c2 > 60) text += `• 弹性成像提示病灶区域质地坚硬。\n`;

  // 淋巴结转移相关描述
  if (state.c4 > 70) {
    text += `• 区域淋巴结明显肿大，形态饱满，皮髓质分界不清，提示高度怀疑转移 (${nStage}: ${nDesc})。\n`;
  } else if (state.c4 > 50) {
    text += `• 区域淋巴结轻度肿大，形态饱满，提示可能转移 (${nStage}: ${nDesc})。\n`;
  } else if (state.c3 > 60) {
    text += `• 区域淋巴结血流信号丰富，需警惕转移可能 (${nStage}: ${nDesc})。\n`;
  } else {
    text += `• 区域淋巴结未见明显肿大，形态正常 (${nStage}: ${nDesc})。\n`;
  }

  text += `\n综上，AI模型建议分期为 ${tStage}，淋巴结转移分期 ${nStage} (${nDesc})。建议结合EUS和病理检查进一步确认。`;

  return {
    tStage,
    tDesc,
    isDanger,
    nStage,
    nDesc,
    nColor,
    confidence,
    reportText: text,
  };
}

