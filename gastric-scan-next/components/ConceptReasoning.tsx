"use client";

import React, { useCallback } from 'react';
import { CONCEPT_CONFIGS, getConceptBarGradient } from '@/lib/medical-config';
import { ConceptState } from '@/types';
import { Activity, RotateCcw, ShieldAlert, Sliders, ChevronDown, ChevronUp } from 'lucide-react';
import { useSettings } from '@/contexts/SettingsContext';
import { RadarChart } from './RadarChart';

interface ConceptReasoningProps {
  state: ConceptState;
  onChange: (key: keyof ConceptState, value: number) => void;
  onReset?: () => void;
}

export const ConceptReasoning: React.FC<ConceptReasoningProps> = React.memo(({ state, onChange, onReset }) => {
  const { t, language } = useSettings();
  const [showTME, setShowTME] = React.useState(false);
  
  // 快速调节按钮
  const quickAdjust = useCallback((key: keyof ConceptState, delta: number) => {
    const current = state[key] ?? 50;
    const newVal = Math.max(0, Math.min(100, current + delta));
    onChange(key, newVal);
  }, [state, onChange]);
  
  const renderSlider = (key: keyof ConceptState) => {
    const config = CONCEPT_CONFIGS[key as string];
    if (!config) return null;

    const val = state[key] ?? 50;
    const barGradient = getConceptBarGradient(val, config.thresholds);
    
    // 判断是否超过阈值
    const isHigh = val > config.thresholds.warning;
    const isDanger = val > config.thresholds.danger;

    return (
      <div className="group py-2.5 px-2 rounded-lg hover:bg-white/5 transition-colors">
        <div className="flex justify-between items-center mb-2">
          <span className="text-xs font-bold text-gray-300 group-hover:text-white transition-colors uppercase tracking-tight">
            {config.label[language as 'zh' | 'en']}
          </span>
          <div className="flex items-center gap-2">
            {/* 快速调节按钮 */}
            <div className="flex items-center gap-0.5 opacity-0 group-hover:opacity-100 transition-opacity">
              <button 
                onClick={() => quickAdjust(key, -10)}
                className="w-6 h-6 flex items-center justify-center text-gray-500 hover:text-white hover:bg-white/10 rounded text-sm font-bold"
              >
                -
              </button>
              <button 
                onClick={() => quickAdjust(key, 10)}
                className="w-6 h-6 flex items-center justify-center text-gray-500 hover:text-white hover:bg-white/10 rounded text-sm font-bold"
              >
                +
              </button>
            </div>
            {/* 数值显示 */}
            <span className={`text-sm font-mono font-bold min-w-[3ch] text-right ${
              isDanger ? 'text-red-400' : isHigh ? 'text-amber-400' : 'text-gray-400'
            }`}>
              {val}
            </span>
            <span className="text-xs text-gray-600">%</span>
          </div>
        </div>
        
        {/* 滑块轨道 */}
        <div className="relative h-6 flex items-center select-none group/track">
          <input 
            type="range" 
            min="0" 
            max="100" 
            value={val}
            onChange={(e) => onChange(key, parseInt(e.target.value))}
            className="absolute inset-0 w-full h-full opacity-0 cursor-pointer z-20"
          />
          
          {/* 轨道背景 */}
          <div className="w-full h-2 bg-[#1a1a1a] rounded-full overflow-hidden relative shadow-inner border border-white/5">
            {/* 填充条 */}
            <div 
              className={`h-full bg-gradient-to-r ${barGradient} transition-all duration-150 ease-out`} 
              style={{ width: `${val}%` }}
            />
            {/* 刻度线 */}
            <div className="absolute inset-0 flex justify-between px-0.5 pointer-events-none">
              {[25, 50, 75].map(tick => (
                <div 
                  key={tick} 
                  className="w-px h-full bg-white/10"
                  style={{ marginLeft: `${tick}%` }}
                />
              ))}
            </div>
          </div>
          
          {/* 滑块手柄 */}
          <div 
            className={`absolute h-4 w-4 rounded-full shadow-lg border-2 pointer-events-none transition-all duration-75 ease-out ${
              isDanger ? 'bg-red-500 border-red-300' : 
              isHigh ? 'bg-amber-500 border-amber-300' : 
              'bg-white border-gray-300'
            } group-hover/track:scale-110`}
            style={{ left: `calc(${val}% - 8px)` }}
          />
        </div>
        
        {/* 标签 */}
        <div className="flex justify-between text-[9px] text-gray-600 font-mono mt-1">
          <span>{config.minLabel}</span>
          <span>{config.maxLabel}</span>
        </div>
      </div>
    );
  };

  const renderSelect = (
    key: keyof ConceptState,
    label: string,
    options: { value: number; label: string }[]
  ) => {
    const val = state[key] ?? options[0]?.value ?? 0;

    return (
      <div className="py-2 px-2 rounded-lg hover:bg-white/5 transition-colors">
        <div className="text-[11px] font-bold text-gray-300 mb-2 uppercase tracking-tight">{label}</div>
        <div className="flex flex-wrap gap-1">
          {options.map((opt) => (
            <button
              key={opt.value}
              onClick={() => onChange(key, opt.value)}
              className={`text-[10px] py-1.5 px-2.5 rounded-lg border transition-all ${
                val === opt.value
                  ? "bg-blue-500/20 text-blue-400 border-blue-500/40 shadow-[0_0_10px_rgba(59,130,246,0.15)]"
                  : "bg-white/5 text-gray-500 border-white/5 hover:border-white/20 hover:bg-white/10 hover:text-gray-300"
              }`}
            >
              {opt.label}
            </button>
          ))}
        </div>
      </div>
    );
  };

  const renderToggle = (key: keyof ConceptState, label: string) => {
    const val = state[key] ?? 0;

    return (
      <div className="py-2 px-2 flex items-center justify-between rounded-lg hover:bg-white/5 transition-colors">
        <span className="text-[11px] font-bold text-gray-300 uppercase tracking-tight">{label}</span>
        <div className="flex bg-black/40 rounded-lg p-0.5 border border-white/5">
          <button
            onClick={() => onChange(key, 0)}
            className={`px-4 py-1.5 rounded-md text-[10px] font-bold transition-all ${
              val === 0
                ? "bg-gray-700 text-gray-200 shadow-sm"
                : "text-gray-600 hover:text-gray-400"
            }`}
          >
            {language === 'zh' ? '无' : 'NO'}
          </button>
          <button
            onClick={() => onChange(key, 1)}
            className={`px-4 py-1.5 rounded-md text-[10px] font-bold transition-all ${
              val === 1
                ? "bg-red-500/80 text-white shadow-[0_0_10px_rgba(239,68,68,0.3)]"
                : "text-gray-600 hover:text-gray-400"
            }`}
          >
            {language === 'zh' ? '有' : 'YES'}
          </button>
        </div>
      </div>
    );
  };

  return (
    <div className="flex flex-col h-full w-full bg-panel-bg">
      {/* Header */}
      <div className="h-11 shrink-0 border-b border-white/5 flex items-center justify-between px-4 bg-panel-bg">
        <span className="flex items-center gap-2 text-xs font-bold text-gray-300 uppercase tracking-widest">
          <Sliders size={14} className="text-blue-500" /> 
          {language === 'zh' ? '病理特征' : 'Pathology Features'}
        </span>
        <button 
          onClick={onReset} 
          className="flex items-center gap-1.5 text-xs text-gray-600 hover:text-white transition-colors px-2.5 py-1.5 rounded hover:bg-white/10"
          title="Reset"
        >
          <RotateCcw size={12} />
          <span className="hidden sm:inline">{language === 'zh' ? '重置' : 'Reset'}</span>
        </button>
      </div>
      
      <div className="flex-1 overflow-y-auto min-h-0 custom-scrollbar">
        {/* Radar Chart - 紧凑版 */}
        <div className="p-2 border-b border-white/5">
          <div className="flex justify-center">
            <div className="w-[50%] max-w-[160px]">
              <RadarChart 
                data={[state.c1 ?? 50, state.c2 ?? 50, state.c3 ?? 50, state.c4 ?? 50]} 
                labels={[
                  CONCEPT_CONFIGS.c1.label[language as 'zh' | 'en'], 
                  CONCEPT_CONFIGS.c2.label[language as 'zh' | 'en'], 
                  CONCEPT_CONFIGS.c3.label[language as 'zh' | 'en'], 
                  CONCEPT_CONFIGS.c4.label[language as 'zh' | 'en']
                ]}
                color={(state.c1 ?? 50) > CONCEPT_CONFIGS.c1.thresholds.danger ? '#ef4444' : '#3b82f6'}
              />
            </div>
          </div>
        </div>

        {/* IHC Markers - 主要指标 */}
        <div className="p-2">
          <div className="flex items-center gap-1.5 px-2 mb-2 text-xs font-bold text-blue-400/80 uppercase tracking-wider">
            <Activity size={12} />
            {language === 'zh' ? '免疫组化' : 'IHC Markers'}
          </div>
          {renderSlider('c1')}
          {renderSlider('c2')}
          {renderSlider('c3')}
          {renderSlider('c4')}
        </div>

        {/* TME Markers - 可折叠 */}
        <div className="border-t border-white/5">
          <button 
            onClick={() => setShowTME(!showTME)}
            className="w-full flex items-center justify-between px-4 py-2.5 text-xs font-bold text-emerald-400/80 uppercase tracking-wider hover:bg-white/5 transition-colors"
          >
            <div className="flex items-center gap-1.5">
              <Activity size={12} />
              {language === 'zh' ? '免疫微环境 (TME)' : 'TME Status'}
            </div>
            {showTME ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
          </button>
          {showTME && (
            <div className="p-2 pt-0 animate-in slide-in-from-top-2 duration-200">
              {renderSlider('c5')}
              {renderSlider('c6')}
              {renderSlider('c7')}
            </div>
          )}
        </div>

        {/* Pathology Type & Invasion */}
        <div className="p-2 border-t border-white/5">
          <div className="flex items-center gap-1.5 px-2 mb-2 text-xs font-bold text-purple-400/80 uppercase tracking-wider">
            <ShieldAlert size={12} />
            {language === 'zh' ? '病理分型' : 'Pathology'}
          </div>
          
          {renderSelect("differentiation", language === 'zh' ? "分化程度" : "Differentiation", [
            { value: 1, label: language === 'zh' ? "高分化" : "Well" },
            { value: 2, label: language === 'zh' ? "中分化" : "Mod" },
            { value: 3, label: language === 'zh' ? "中-低" : "Mod-Poor" },
            { value: 4, label: language === 'zh' ? "低分化" : "Poor" },
          ])}

          {renderSelect("lauren", "Lauren", [
            { value: 1, label: language === 'zh' ? "肠型" : "Intestinal" },
            { value: 0, label: language === 'zh' ? "弥漫型" : "Diffuse" },
            { value: 4, label: language === 'zh' ? "混合" : "Mixed" },
          ])}

          <div className="mt-2 space-y-1">
            {renderToggle("vascularInvasion", language === 'zh' ? "脉管侵犯" : "Vascular Inv")}
            {renderToggle("neuralInvasion", language === 'zh' ? "神经侵犯" : "Neural Inv")}
          </div>
        </div>
      </div>
    </div>
  );
});

ConceptReasoning.displayName = 'ConceptReasoning';
