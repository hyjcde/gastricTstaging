"use client";

import React, { useState } from 'react';
import { Filter, X, ChevronDown } from 'lucide-react';
import { Patient } from '@/types';
import { calculateDiagnosis } from '@/lib/diagnosis';
import { getConceptStateFromPatient } from '@/lib/patient-utils';
import { useSettings } from '@/contexts/SettingsContext';

export interface FilterOptions {
  tStage: string[]; // e.g., ['T1/T2', 'T3', 'T4a']
  nStage: string[]; // e.g., ['N0', 'N1', 'N2', 'N3']
  confidenceMin: number; // 0-100
  hasClinical: boolean | null; // null = all, true = has clinical, false = no clinical
  highRisk: boolean | null; // null = all, true = high risk only
  treatmentType: 'all' | 'surgery' | 'nac'; // 治疗类型
}

const DEFAULT_FILTERS: FilterOptions = {
  tStage: [],
  nStage: [],
  confidenceMin: 0,
  hasClinical: null,
  highRisk: null,
  treatmentType: 'all',
};

interface AdvancedFiltersProps {
  patients: Patient[];
  onFilterChange: (filteredPatients: Patient[]) => void;
  isOpen: boolean;
  onToggle: () => void;
}

export const AdvancedFilters: React.FC<AdvancedFiltersProps> = ({
  patients,
  onFilterChange,
  isOpen,
  onToggle,
}) => {
  const { t } = useSettings();
  const [filters, setFilters] = useState<FilterOptions>(DEFAULT_FILTERS);

  const applyFilters = (newFilters: FilterOptions) => {
    const filtered = patients.filter(patient => {
      // 获取患者的概念状态并计算诊断
      const conceptState = getConceptStateFromPatient(patient);
      const diagnosis = calculateDiagnosis(conceptState);

      // T分期过滤
      if (newFilters.tStage.length > 0 && !newFilters.tStage.includes(diagnosis.tStage)) {
        return false;
      }

      // N分期过滤
      if (newFilters.nStage.length > 0 && !newFilters.nStage.includes(diagnosis.nStage)) {
        return false;
      }

      // 置信度过滤
      if (diagnosis.confidence.overall < newFilters.confidenceMin) {
        return false;
      }

      // 临床数据过滤
      if (newFilters.hasClinical !== null) {
        const hasClinical = !!patient.clinical;
        if (newFilters.hasClinical !== hasClinical) {
          return false;
        }
      }

      // 高风险过滤
      if (newFilters.highRisk !== null) {
        if (newFilters.highRisk !== diagnosis.flags.highRisk) {
          return false;
        }
      }

      // 治疗类型过滤
      if (newFilters.treatmentType !== 'all') {
        const isNAC = patient.group === 'NAC' || patient.id.startsWith('NAC_');
        if (newFilters.treatmentType === 'nac' && !isNAC) {
          return false;
        }
        if (newFilters.treatmentType === 'surgery' && isNAC) {
          return false;
        }
      }

      return true;
    });

    onFilterChange(filtered);
  };

  const handleFilterChange = <K extends keyof FilterOptions>(key: K, value: FilterOptions[K]) => {
    const newFilters = { ...filters, [key]: value };
    setFilters(newFilters);
    applyFilters(newFilters);
  };

  const toggleTStage = (stage: string) => {
    const newTStages = filters.tStage.includes(stage)
      ? filters.tStage.filter(s => s !== stage)
      : [...filters.tStage, stage];
    handleFilterChange('tStage', newTStages);
  };

  const toggleNStage = (stage: string) => {
    const newNStages = filters.nStage.includes(stage)
      ? filters.nStage.filter(s => s !== stage)
      : [...filters.nStage, stage];
    handleFilterChange('nStage', newNStages);
  };

  const resetFilters = () => {
    setFilters(DEFAULT_FILTERS);
    onFilterChange(patients);
  };

  const hasActiveFilters = 
    filters.tStage.length > 0 ||
    filters.nStage.length > 0 ||
    filters.confidenceMin > 0 ||
    filters.hasClinical !== null ||
    filters.highRisk !== null ||
    filters.treatmentType !== 'all';

  return (
    <div className="border-b border-white/5 bg-[#0b0b0d]">
      {/* Filter Header */}
      <button
        onClick={onToggle}
        className="w-full px-3 py-2 flex items-center justify-between hover:bg-white/5 transition-colors"
      >
        <div className="flex items-center gap-2">
          <Filter size={12} className="text-gray-500" />
          <span className="text-[11px] font-bold text-gray-300 uppercase tracking-widest">
            {t.filters.title}
          </span>
          {hasActiveFilters && (
            <span className="text-[8px] bg-blue-500 text-white px-1.5 py-0.5 rounded-full">
              {[
                filters.tStage.length,
                filters.nStage.length,
                filters.confidenceMin > 0 ? 1 : 0,
                filters.hasClinical !== null ? 1 : 0,
                filters.highRisk !== null ? 1 : 0,
                filters.treatmentType !== 'all' ? 1 : 0,
              ].reduce((a, b) => a + b, 0)}
            </span>
          )}
        </div>
        <ChevronDown
          size={12}
          className={`text-gray-500 transition-transform ${isOpen ? 'rotate-180' : ''}`}
        />
      </button>

      {/* Filter Content */}
      {isOpen && (
        <div className="px-3 pb-3 space-y-3 border-t border-white/5 pt-3">
          {/* T分期过滤 */}
          <div>
            <label className="text-[10px] font-bold text-gray-400 uppercase mb-1.5 block">
              {t.filters.tStage}
            </label>
            <div className="flex flex-wrap gap-1.5">
              {['T1/T2', 'T3', 'T4a'].map(stage => (
                <button
                  key={stage}
                  onClick={() => toggleTStage(stage)}
                  className={`text-[9px] px-2 py-1 rounded border transition-all ${
                    filters.tStage.includes(stage)
                      ? 'bg-blue-500 text-white border-blue-600'
                      : 'bg-[#18181b] text-gray-400 border-white/10 hover:border-blue-500/50'
                  }`}
                >
                  {stage}
                </button>
              ))}
            </div>
          </div>

          {/* N分期过滤 */}
          <div>
            <label className="text-[10px] font-bold text-gray-400 uppercase mb-1.5 block">
              {t.filters.nStage}
            </label>
            <div className="flex flex-wrap gap-1.5">
              {['N0', 'N1', 'N2', 'N3'].map(stage => (
                <button
                  key={stage}
                  onClick={() => toggleNStage(stage)}
                  className={`text-[9px] px-2 py-1 rounded border transition-all ${
                    filters.nStage.includes(stage)
                      ? 'bg-blue-500 text-white border-blue-600'
                      : 'bg-[#18181b] text-gray-400 border-white/10 hover:border-blue-500/50'
                  }`}
                >
                  {stage}
                </button>
              ))}
            </div>
          </div>

          {/* 置信度过滤 */}
          <div>
            <label className="text-[10px] font-bold text-gray-400 uppercase mb-1.5 block">
              {t.filters.minConfidence}: {filters.confidenceMin}%
            </label>
            <input
              type="range"
              min="0"
              max="100"
              value={filters.confidenceMin}
              onChange={(e) => handleFilterChange('confidenceMin', parseInt(e.target.value))}
              className="w-full h-1 bg-[#18181b] rounded-lg appearance-none cursor-pointer accent-blue-500"
            />
          </div>

          {/* 临床数据过滤 */}
          <div>
            <label className="text-[10px] font-bold text-gray-400 uppercase mb-1.5 block">
              {t.filters.clinicalData}
            </label>
            <div className="flex gap-1.5">
              {[
                { value: null, label: t.filters.all },
                { value: true, label: t.filters.hasData },
                { value: false, label: t.filters.noData },
              ].map(opt => (
                <button
                  key={String(opt.value)}
                  onClick={() => handleFilterChange('hasClinical', opt.value)}
                  className={`text-[9px] px-2 py-1 rounded border transition-all flex-1 ${
                    filters.hasClinical === opt.value
                      ? 'bg-blue-500 text-white border-blue-600'
                      : 'bg-[#18181b] text-gray-400 border-white/10 hover:border-blue-500/50'
                  }`}
                >
                  {opt.label}
                </button>
              ))}
            </div>
          </div>

          {/* 高风险过滤 */}
          <div>
            <label className="text-[10px] font-bold text-gray-400 uppercase mb-1.5 block">
              {t.filters.riskLevel}
            </label>
            <div className="flex gap-1.5">
              {[
                { value: null, label: t.filters.all },
                { value: true, label: t.filters.highRisk },
                { value: false, label: t.filters.lowRisk },
              ].map(opt => (
                <button
                  key={String(opt.value)}
                  onClick={() => handleFilterChange('highRisk', opt.value)}
                  className={`text-[9px] px-2 py-1 rounded border transition-all flex-1 ${
                    filters.highRisk === opt.value
                      ? 'bg-blue-500 text-white border-blue-600'
                      : 'bg-[#18181b] text-gray-400 border-white/10 hover:border-blue-500/50'
                  }`}
                >
                  {opt.label}
                </button>
              ))}
            </div>
          </div>

          {/* 治疗类型过滤 */}
          <div>
            <label className="text-[10px] font-bold text-gray-400 uppercase mb-1.5 block">
              {t.filters.treatmentType}
            </label>
            <div className="flex gap-1.5">
              {[
                { value: 'all', label: t.filters.all },
                { value: 'surgery', label: t.filters.surgery },
                { value: 'nac', label: t.filters.nac },
              ].map(opt => (
                <button
                  key={opt.value}
                  onClick={() => handleFilterChange('treatmentType', opt.value as FilterOptions['treatmentType'])}
                  className={`text-[9px] px-2 py-1 rounded border transition-all flex-1 ${
                    filters.treatmentType === opt.value
                      ? 'bg-blue-500 text-white border-blue-600'
                      : 'bg-[#18181b] text-gray-400 border-white/10 hover:border-blue-500/50'
                  }`}
                >
                  {opt.label}
                </button>
              ))}
            </div>
          </div>

          {/* 重置按钮 */}
          {hasActiveFilters && (
            <button
              onClick={resetFilters}
              className="w-full text-[9px] px-2 py-1.5 rounded border border-white/10 bg-[#18181b] text-gray-400 hover:bg-white/5 hover:text-gray-300 transition-all flex items-center justify-center gap-1"
            >
              <X size={10} />
              {t.filters.reset}
            </button>
          )}
        </div>
      )}
    </div>
  );
};

