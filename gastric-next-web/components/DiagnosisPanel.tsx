"use client";

import React, { useEffect, useState, useRef } from "react";
import { DiagnosisResult } from "@/lib/types";
import { FileText } from "lucide-react";

interface DiagnosisPanelProps {
  result: DiagnosisResult;
}

export const DiagnosisPanel: React.FC<DiagnosisPanelProps> = ({ result }) => {
  const [displayedText, setDisplayedText] = useState("");
  const typingTimeoutRef = useRef<NodeJS.Timeout | null>(null);

  // Typewriter effect
  useEffect(() => {
    if (typingTimeoutRef.current) {
      clearTimeout(typingTimeoutRef.current);
    }

    setDisplayedText("");
    let i = 0;
    const fullText = result.reportText;

    const type = () => {
      if (i < fullText.length) {
        setDisplayedText((prev) => prev + fullText.charAt(i));
        i++;
        typingTimeoutRef.current = setTimeout(type, 15);
      }
    };

    type();

    return () => {
      if (typingTimeoutRef.current) clearTimeout(typingTimeoutRef.current);
    };
  }, [result.reportText]);

  return (
    <div className="bg-white rounded-2xl border border-slate-200 shadow-md flex flex-col overflow-hidden h-full transition-all hover:shadow-lg hover:border-slate-300">
      <div className="px-5 py-4 border-b border-slate-200 font-semibold text-sm text-sidebar flex justify-between items-center bg-gradient-to-b from-white to-slate-50">
        <span>智能诊断结论 (Diagnosis)</span>
        <FileText size={16} />
      </div>
      <div className="p-5 flex-1 overflow-y-auto">
        {/* Result Box */}
        <div className="text-center p-6 bg-gradient-to-br from-slate-50 to-slate-200 rounded-xl mb-5 relative">
          <div className="text-xs uppercase tracking-widest text-slate-500 mb-2">
            Predicted T-Stage
          </div>
          <div
            className={`text-5xl font-extrabold leading-none mb-2 bg-clip-text text-transparent bg-gradient-to-br ${
              result.isDanger
                ? "from-red-700 to-red-500"
                : "from-sidebar to-primary"
            }`}
          >
            {result.tStage}
          </div>
          <div className="font-medium text-slate-700">{result.tDesc}</div>

          <div className="mt-5">
            <div className="flex justify-between text-xs mb-1">
              <span>AI Confidence</span>
              <span className="font-bold">{result.confidence}%</span>
            </div>
            <div className="h-1.5 bg-slate-300 rounded-full overflow-hidden w-4/5 mx-auto">
              <div
                className="h-full bg-primary transition-all duration-500 ease-out"
                style={{ width: `${result.confidence}%` }}
              />
            </div>
          </div>
        </div>

        {/* N-Stage & M-Stage Grid */}
        <div className="grid grid-cols-2 gap-3 mb-5">
          <div className="bg-slate-50 p-3 rounded-lg text-center">
            <div className="text-[10px] text-slate-500 mb-1">淋巴结转移 (N-Stage)</div>
            <div className={`font-bold text-lg ${result.nColor}`}>{result.nStage}</div>
            <div className="text-[10px] text-slate-600 mt-1">{result.nDesc}</div>
          </div>
          <div className="bg-slate-50 p-3 rounded-lg text-center">
            <div className="text-[10px] text-slate-500 mb-1">远处转移 (M-Stage)</div>
            <div className="font-bold text-lg text-slate-700">M0</div>
            <div className="text-[10px] text-slate-600 mt-1">无远处转移</div>
          </div>
        </div>

        {/* Report Section */}
        <div className="bg-white border border-slate-200 border-l-4 border-l-primary rounded-lg p-4 min-h-[150px] text-sm leading-relaxed text-slate-700">
          <div className="text-xs uppercase text-slate-400 mb-2 flex items-center gap-1.5">
            <span className="animate-pulse">●</span>
            LLM 生成报告 (Generating...)
          </div>
          <div className="whitespace-pre-wrap typewriter-cursor font-serif">
            {displayedText}
          </div>
        </div>
      </div>
    </div>
  );
};

