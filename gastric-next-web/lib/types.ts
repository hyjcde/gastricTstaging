export interface ConceptState {
  c1: number; // Serosa Continuity (0-100)
  c2: number; // Stiffness (0-100)
  c3: number; // Blood Flow (0-100)
  c4: number; // Lymph Node Morphology (0-100)
}

export interface DiagnosisResult {
  tStage: string;
  tDesc: string;
  isDanger: boolean;
  nStage: string;
  nDesc: string; // 淋巴结转移详细描述
  nColor: string; // Hex or Tailwind class
  confidence: number;
  reportText: string;
}

export const DEFAULT_CONCEPTS: ConceptState = {
  c1: 85,
  c2: 78,
  c3: 60,
  c4: 30,
};

