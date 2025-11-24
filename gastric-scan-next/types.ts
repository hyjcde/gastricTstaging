export interface ConceptState {
  c1: number; // Ki-67 proliferation index surrogate (0-100)
  c2: number; // CPS (combined positive score) surrogate (0-100)
  c3: number; // PD-1 expression surrogate (0-100)
  c4: number; // FoxP3 / immune regulation surrogate (0-100)
  c5: number; // CD3 density (0-100)
  c6: number; // CD4 density (0-100)
  c7: number; // CD8 density (0-100)
  differentiation: number; // 1=Well, 2=Mod, 3=Mod-Poor, 4=Poor, 5=Unknown
  lauren: number; // 1=Intestinal, 0=Diffuse, 4=Unknown
  vascularInvasion: number; // 0=No, 1=Yes
  neuralInvasion: number; // 0=No, 1=Yes
}

export const DEFAULT_STATE: ConceptState = {
  // Ki-67 通常在 20-80% 之间，胃癌中位数常在 40-60%
  c1: 45, 
  // CPS 评分通常在 0-100 之间，但大多数阴性或低表达（<10），阳性（>1）有临床意义
  c2: 5, 
  // PD-1 表达通常较低，除非富集淋巴细胞浸润
  c3: 10, 
  // FoxP3 代表 Treg，通常在肿瘤浸润淋巴细胞中占比不高（5-20%）
  c4: 15, 
  // CD3 是总 T 细胞，通常密度中等
  c5: 40, 
  // CD4/CD8
  c6: 30, 
  c7: 25, 
  // 分化程度：最常见的是中分化或低分化
  differentiation: 3, // 3: Mod-Poor
  // Lauren 分型：肠型略多于弥漫型，或各半
  lauren: 1, // 1: Intestinal
  vascularInvasion: 0,
  neuralInvasion: 0
};

export interface ConceptFeatures {
  ki67?: string;
  cps?: string;
  pd1?: string;
  foxp3?: string;
  cd3?: string;
  cd4?: string;
  cd8?: string;
  vascular?: string;
  neural?: string;
  differentiation?: string;
  lauren?: string;
}

export interface ClinicalData {
  age: number | null;
  sex: string;
  tumorSize: {
    length: number | null;
    thickness: number | null;
  };
  location: string;
  biomarkers: {
    cea: number | null;
    ca199: number | null;
    cea_positive: boolean;
    ca199_positive: boolean;
  };
  pathology: {
    type: string;
    differentiation: string;
    lauren: string;
    pT: string;
    pN: string;
    pM: string;
    pStage: string;
  };
  concept_features?: ConceptFeatures;
}

export interface Patient {
  id: string;
  id_short: string;
  patient_id: string; // Pure numeric ID for matching
  group: string;
  phase: string;
  image_url: string;
  overlay_url: string;
  overlay_transparent_url?: string;
  json_url: string;
  clinical?: ClinicalData;
}
