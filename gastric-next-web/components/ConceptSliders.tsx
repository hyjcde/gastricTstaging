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
    // const isIntervened = Math.abs(val - DEFAULT_CONCEPTS[key]) > 10;

    return (
      <div className="bg-slate-50 rounded-xl p-3 mb-3 border border-transparent hover:bg-white hover:border-slate-200 hover:shadow-sm transition-all">
        <div className="flex justify-between mb-2 text-xs font-bold text-slate-700">
          <span>{label}</span>
          <span className="font-mono text-blue-600">{val}%</span>
        </div>
        <input
          type="range"
          min="0"
          max="100"
          className="w-full h-1.5 bg-slate-200 rounded-lg appearance-none cursor-pointer accent-blue-500"
          value={val}
          onChange={(e) => onChange(key, parseInt(e.target.value))}
        />
        <div className="flex justify-between mt-1 text-[10px] text-slate-400 font-mono">
          <span>{minLabel}</span>
          <span>{maxLabel}</span>
        </div>
      </div>
    );
  };

  const renderSelect = (
    key: keyof ConceptState,
    label: string,
    options: { value: number; label: string }[]
  ) => {
    const val = values[key];
    return (
      <div className="bg-slate-50 rounded-xl p-3 mb-3 border border-transparent hover:bg-white hover:border-slate-200 hover:shadow-sm transition-all">
        <div className="text-xs font-bold text-slate-700 mb-2">{label}</div>
        <div className="grid grid-cols-1 gap-1">
          {options.map((opt) => (
            <button
              key={opt.value}
              onClick={() => onChange(key, opt.value)}
              className={`text-[10px] py-1.5 px-2 rounded border transition-all text-left ${
                val === opt.value
                  ? "bg-blue-500 text-white border-blue-600 shadow-sm"
                  : "bg-white text-slate-600 border-slate-200 hover:border-blue-300"
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
    const val = values[key];
    return (
      <div className="bg-slate-50 rounded-xl p-3 mb-3 border border-transparent hover:bg-white hover:border-slate-200 hover:shadow-sm transition-all flex items-center justify-between">
        <span className="text-xs font-bold text-slate-700">{label}</span>
        <div className="flex bg-slate-200 rounded-lg p-0.5">
          <button
            onClick={() => onChange(key, 0)}
            className={`px-3 py-1 rounded-md text-[10px] font-bold transition-all ${
              val === 0
                ? "bg-white text-slate-700 shadow-sm"
                : "text-slate-500 hover:text-slate-700"
            }`}
          >
            无
          </button>
          <button
            onClick={() => onChange(key, 1)}
            className={`px-3 py-1 rounded-md text-[10px] font-bold transition-all ${
              val === 1
                ? "bg-red-500 text-white shadow-sm"
                : "text-slate-500 hover:text-slate-700"
            }`}
          >
            有
          </button>
        </div>
      </div>
    );
  };

  return (
    <div className="bg-white rounded-2xl border border-slate-200 shadow-md flex flex-col overflow-hidden h-full">
      <div className="px-5 py-3 border-b border-slate-200 font-bold text-xs text-slate-800 bg-slate-50/50 flex justify-between items-center">
        <span>多模态病理特征 (Pathology Concepts)</span>
      </div>
      <div className="p-4 flex-1 overflow-y-auto custom-scrollbar space-y-1">
        <div className="text-[10px] font-bold text-slate-400 uppercase tracking-wider mb-2 mt-1">免疫组化 (IHC)</div>
        {renderSlider("c1", "Ki-67 指数", "低 (Low)", "高 (High)")}
        {renderSlider("c2", "CPS (Combined Positive Score)", "0", "100")}
        {renderSlider("c3", "PD-1 表达", "阴性", "强阳性")}
        {renderSlider("c4", "FoxP3 浸润密度", "稀疏", "密集")}
        
        <div className="text-[10px] font-bold text-slate-400 uppercase tracking-wider mb-2 mt-4">免疫微环境 (TME)</div>
        {renderSlider("c5", "CD3 T细胞密度", "低", "高")}
        {renderSlider("c6", "CD4 辅助T细胞", "低", "高")}
        {renderSlider("c7", "CD8 细胞毒性T细胞", "低", "高")}

        <div className="text-[10px] font-bold text-slate-400 uppercase tracking-wider mb-2 mt-4">病理分型 & 侵犯</div>
        {renderSelect("differentiation", "分化程度", [
          { value: 1, label: "1: 高分化 (Well Diff)" },
          { value: 2, label: "2: 中分化 (Mod Diff)" },
          { value: 3, label: "3: 中-低分化 (Mod-Poor)" },
          { value: 4, label: "4: 低分化 (Poorly Diff)" },
          { value: 5, label: "5: 不确定 (Undetermined)" },
        ])}

        {renderSelect("lauren", "Lauren 分型", [
          { value: 1, label: "1: 肠型 (Intestinal)" },
          { value: 0, label: "0: 弥漫型 (Diffuse)" },
          { value: 4, label: "4: 不确定/混合 (Mixed/Unk)" },
        ])}

        {renderToggle("vascularInvasion", "脉管侵犯 (LVI)")}
        {renderToggle("neuralInvasion", "神经侵犯 (PNI)")}
      </div>
    </div>
  );
};
