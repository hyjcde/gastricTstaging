"use client";

import React, { createContext, useContext, useState, ReactNode } from 'react';
import { Language, dictionary } from '@/lib/i18n';
import { DatasetType, CohortYear, TreatmentType } from '@/lib/config';

interface SettingsContextType {
  language: Language;
  setLanguage: (lang: Language) => void;
  dataset: DatasetType;
  setDataset: (ds: DatasetType) => void;
  cohortYear: CohortYear;
  setCohortYear: (year: CohortYear) => void;
  treatmentType: TreatmentType;
  setTreatmentType: (type: TreatmentType) => void;
  t: typeof dictionary['en'];
}

const SettingsContext = createContext<SettingsContextType | undefined>(undefined);

export const SettingsProvider = ({ children }: { children: ReactNode }) => {
  const [language, setLanguage] = useState<Language>('zh'); // Default to Chinese per request
  const [dataset, setDataset] = useState<DatasetType>('original');
  const [cohortYear, setCohortYear] = useState<CohortYear>('2025'); // Default to 2025 (can be '2019', '2024', or '2025')
  const [treatmentType, setTreatmentType] = useState<TreatmentType>('surgery'); // Default to surgery (can be 'surgery' or 'nac')

  const t = dictionary[language];

  return (
    <SettingsContext.Provider value={{ language, setLanguage, dataset, setDataset, cohortYear, setCohortYear, treatmentType, setTreatmentType, t }}>
      {children}
    </SettingsContext.Provider>
  );
};

export const useSettings = () => {
  const context = useContext(SettingsContext);
  if (!context) {
    throw new Error('useSettings must be used within a SettingsProvider');
  }
  return context;
};

