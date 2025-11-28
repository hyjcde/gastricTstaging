
export interface ConceptState {
  c1: number; // Ki67 (0-100)
  c2: number; // CPS (0-100)
  c3: number; // PD-1 (0-100)
  c4: number; // FoxP3 (0-100)
  c5: number; // CD3 (0-100)
  c6: number; // CD4 (0-100)
  c7: number; // CD8 (0-100)
  differentiation: number; // 1=Well, 2=Mod, 3=Mod-Poor, 4=Poor, 5=Unknown
  lauren: number; // 1=Intestinal, 0=Diffuse, 4=Unknown
  vascularInvasion: number; // 0=No, 1=Yes
  neuralInvasion: number; // 0=No, 1=Yes
}

export interface DiagnosisResult {
  tStage: string;
  tDesc: string;
  isDanger: boolean;
  nStage: string;
  nDesc: string;
  nColor: string;
  confidence: number;
  reportText: string;
}

export const DEFAULT_CONCEPTS: ConceptState = {
  c1: 50, // Ki67 default
  c2: 50, // CPS default
  c3: 50, // PD-1 default
  c4: 50, // FoxP3 default
  c5: 50, // CD3 default
  c6: 50, // CD4 default
  c7: 50, // CD8 default
  differentiation: 2,
  lauren: 1,
  vascularInvasion: 0,
  neuralInvasion: 0,
};
