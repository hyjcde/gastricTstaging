"use client";

import React from "react";
import { ConceptState, DEFAULT_CONCEPTS } from "@/lib/types";

interface ConceptSlidersProps {
  values: ConceptState;
  onChange: (key: keyof ConceptState, value: number) => void;
}

export const ConceptSliders: React.FC<ConceptSlidersProps> = ({
  values,
  onChange,
}) => {
  const renderSlider = (
    key: keyof ConceptState,
    label: string,
    minLabel: string,
    maxLabel: string
  ) => {
    const val = values[key];
    const isIntervened = Math.abs(val - DEFAULT_CONCEPTS[key]) > 10;

    return (
      <div className="bg-slate-50 rounded-xl p-4 mb-4 border border-transparent hover:bg-white hover:border-slate-200 hover:shadow-sm transition-all">
        <div className="flex justify-between mb-3 text-sm font-semibold text-slate-700">
          <span>{label}</span>
          <span
            className={`text-[10px] uppercase tracking-wider px-1.5 py-0.5 rounded bg-warning text-white transition-all duration-300 ${
              isIntervened ? "opacity-100 translate-y-0" : "opacity-0 translate-y-1"
            }`}
          >
            人工干预
          </span>
        </div>
        <input
          type="range"
          min="0"
          max="100"
          value={val}
          onChange={(e) => onChange(key, parseInt(e.target.value))}
        />
        <div className="flex justify-between mt-2 text-xs text-slate-500 font-mono">
          <span>{minLabel}</span>
          <span className="font-bold text-sidebar">{val}%</span>
          <span>{maxLabel}</span>
        </div>
      </div>
    );
  };

  return (
    <div className="bg-white rounded-2xl border border-slate-200 shadow-md flex flex-col overflow-hidden h-full transition-all hover:shadow-lg hover:border-slate-300">
      <div className="px-5 py-4 border-b border-slate-200 font-semibold text-sm text-sidebar flex justify-between items-center bg-gradient-to-b from-white to-slate-50">
        <span>病理概念推理链 (CBM Reasoning)</span>
        <span className="text-xs bg-primary text-white px-2 py-0.5 rounded-full">
          可交互
        </span>
      </div>
      <div className="p-5 flex-1 overflow-y-auto">
        <p className="text-sm text-slate-500 mb-5">
          AI 基于视觉语言模型提取以下关键特征。拖动滑块可进行
          <strong>反事实推演</strong>，验证诊断逻辑。
        </p>

        {renderSlider("c1", "浆膜层连续性中断", "完整 (Continuous)", "中断 (Interrupted)")}
        {renderSlider("c2", "胃壁僵硬度 (弹性成像)", "软 (Soft)", "硬 (Stiff)")}
        {renderSlider("c3", "多普勒血流信号", "乏血 (Poor)", "丰富 (Rich)")}
        {renderSlider("c4", "区域淋巴结形态", "正常 (Normal)", "肿大/融合 (Enlarged)")}
      </div>
    </div>
  );
};

