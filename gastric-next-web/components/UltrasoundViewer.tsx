"use client";

import React, { useState } from "react";
import { Eye, RotateCcw } from "lucide-react";

interface UltrasoundViewerProps {
  onReset: () => void;
  imageUrl?: string; // Optional prop for real data integration
}

export const UltrasoundViewer: React.FC<UltrasoundViewerProps> = ({
  onReset,
  imageUrl,
}) => {
  const [showHeatmap, setShowHeatmap] = useState(false);

  return (
    <div className="bg-white rounded-2xl border border-slate-200 shadow-md flex flex-col overflow-hidden h-full transition-all hover:shadow-lg hover:border-slate-300">
      <div className="px-5 py-4 border-b border-slate-200 font-semibold text-sm text-sidebar flex justify-between items-center bg-gradient-to-b from-white to-slate-50">
        <span>多模态超声影像 (Multimodal US)</span>
        <div className="w-4 h-4 rounded-full border-2 border-current opacity-50" />
      </div>
      
      <div className="p-5 flex-1 flex flex-col">
        <div className="relative w-full h-[320px] bg-black rounded-xl overflow-hidden flex justify-center border-2 border-neutral-800">
          {/* Scan Info Overlay */}
          <div className="absolute top-2 left-4 text-white/70 font-mono text-xs z-20 leading-relaxed">
            FREQ: 7.5MHz<br />
            DEPTH: 6.0cm<br />
            GAIN: 85<br />
            MI: 0.9
          </div>

          {/* Image Area */}
          {imageUrl ? (
            // Real Image Mode
            <div className="relative w-full h-full">
               {/* eslint-disable-next-line @next/next/no-img-element */}
              <img 
                src={imageUrl} 
                alt="Ultrasound Scan" 
                className="w-full h-full object-contain"
              />
              {/* Heatmap Overlay for Real Image */}
              <div
                className={`absolute inset-0 bg-gradient-radial from-red-500/60 to-transparent mix-blend-color-dodge transition-opacity duration-500 pointer-events-none ${
                  showHeatmap ? "opacity-100" : "opacity-0"
                }`}
                style={{ background: 'radial-gradient(circle at 48% 45%, rgba(255, 50, 50, 0.6), transparent 20%)' }}
              />
            </div>
          ) : (
            // Simulation Mode (CSS Art)
            <div className="scan-sector w-full h-full relative overflow-hidden">
              <div className="scan-noise absolute top-[10%] left-1/2 -translate-x-1/2 w-[80%] h-[80%]" />
              <div className="tumor-roi absolute top-[40%] left-[45%] w-[60px] h-[45px]" />
              <div
                className={`heatmap-layer absolute inset-0 transition-opacity duration-500 pointer-events-none ${
                  showHeatmap ? "opacity-100" : "opacity-0"
                }`}
              />
            </div>
          )}
        </div>

        {/* Controls */}
        <div className="flex gap-3 mt-4">
          <button
            onClick={() => setShowHeatmap(!showHeatmap)}
            className="flex-1 py-2.5 px-4 rounded-lg font-medium text-sm flex items-center justify-center gap-2 transition-colors bg-sidebar text-white hover:bg-slate-700"
          >
            <Eye size={16} />
            {showHeatmap ? "隐藏可解释热图" : "显示可解释热图"}
          </button>
          <button
            onClick={() => {
              setShowHeatmap(false);
              onReset();
            }}
            className="flex-1 py-2.5 px-4 rounded-lg font-medium text-sm flex items-center justify-center gap-2 transition-colors bg-white border border-slate-200 text-slate-700 hover:bg-slate-50 hover:border-slate-300"
          >
            <RotateCcw size={16} />
            重置
          </button>
        </div>

        <div className="mt-6 p-4 bg-slate-100 rounded-lg text-sm text-slate-500">
          <strong>ROI 自动检测：</strong>
          <br />
          系统在胃窦小弯侧识别到低回声病灶，边界模糊，建议重点关注浆膜层连续性。
        </div>
      </div>
    </div>
  );
};

