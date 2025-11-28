import { ConceptState, DiagnosisResult } from "./types";

export function calculateDiagnosis(state: ConceptState): DiagnosisResult {
  // Simulated Logic based on Concept Bottleneck Model (CBM) weights
  
  // T-Stage (T分期) 推理逻辑
  // 强关联：Ki-67(c1), PD-1(c3), 分化程度(differentiation), 脉管侵犯(vascularInvasion)
  const proliferationScore = state.c1 * 0.4 + state.c3 * 0.3; // 增殖与免疫逃逸
  const invasionScore = (state.vascularInvasion ? 30 : 0) + (state.neuralInvasion ? 20 : 0);
  const differentiationPenalty = (state.differentiation - 1) * 10; // 分化越差(数值越大)，风险越高
  
  const tScore = proliferationScore * 0.5 + invasionScore + differentiationPenalty;

  let tStage = "T1/T2";
  let tDesc = "局限于肌层";
  let isDanger = false;

  if (tScore > 75) {
    tStage = "T4a";
    tDesc = "浆膜受侵 (Serosa Invaded)";
    isDanger = true;
  } else if (tScore > 45) {
    tStage = "T3";
    tDesc = "穿透浆膜下层";
    isDanger = true;
  }

  // N-Stage (淋巴结分期) 推理逻辑
  // 强关联：FoxP3(c4), CD4/CD8比值(c6, c7), Lauren分型, CPS(c2)
  const immuneScore = state.c4 * 0.5 + state.c2 * 0.3; // 免疫抑制环境
  const microEnvScore = (state.c6 > state.c7) ? 20 : 0; // CD4 > CD8 提示预后不良
  const laurenRisk = (state.lauren === 0) ? 25 : (state.lauren === 4 ? 15 : 0); // 弥漫型风险最高

  const nScore = immuneScore + microEnvScore + laurenRisk;

  let nStage = "N0";
  let nDesc = "无区域淋巴结转移";
  let nColor = "text-success"; // Using Tailwind class names for logic

  // 详细的N分期判断
  if (nScore >= 75) {
    nStage = "N3";
    nDesc = "7个或以上区域淋巴结转移";
    nColor = "text-danger";
  } else if (nScore >= 55) {
    nStage = "N2";
    nDesc = "3-6个区域淋巴结转移";
    nColor = "text-danger";
  } else if (nScore >= 35) {
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
  let text = `基于多模态病理特征分析：\n`;
  
  // T分期描述
  if (state.c1 > 60)
    text += `• Ki-67指数较高 (${state.c1}%)，提示细胞增殖活跃，T分期升级风险增加。\n`;
  if (state.vascularInvasion)
    text += `• 存在脉管侵犯 (LVI)，显著增加肿瘤浸润深度及远处转移风险。\n`;
  if (state.differentiation >= 3)
    text += `• 分化程度较差 (${state.differentiation >= 4 ? '低分化' : '中-低分化'})，恶性程度高。\n`;

  // N分期描述
  if (state.c4 > 60) {
    text += `• FoxP3 高表达 (${state.c4}%)，提示免疫抑制微环境，利于淋巴结转移 (${nStage})。\n`;
  }
  if (state.lauren === 0) {
    text += `• Lauren 分型为弥漫型，淋巴结转移概率显著高于肠型。\n`;
  }
  if (state.c2 > 50) {
    text += `• CPS 评分 (${state.c2}) 提示免疫逃逸机制活跃。\n`;
  }

  if (nStage === "N0" && tStage === "T1/T2") {
    text += `• 免疫微环境相对稳定 (CD8浸润尚可)，目前指征倾向于早期局限性病变。\n`;
  }

  text += `\n综上，CBM模型建议分期为 ${tStage}，淋巴结转移分期 ${nStage} (${nDesc})。建议结合影像学特征综合研判。`;

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
