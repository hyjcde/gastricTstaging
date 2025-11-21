import React from "react";
import { Activity } from "lucide-react";

export const Header = () => {
  return (
    <header className="bg-white border-b border-slate-200 h-[60px] flex items-center justify-between px-6 shadow-sm z-10 sticky top-0">
      <div className="flex items-center gap-3 font-bold text-xl text-sidebar">
        <div className="w-8 h-8 bg-gradient-to-br from-primary to-accent rounded-lg flex items-center justify-center text-white">
          <Activity size={20} />
        </div>
        GastricScan AI
        <span className="font-normal text-sm ml-1 opacity-70">Pro</span>
      </div>
      <div className="flex gap-5 text-sm text-slate-500">
        <span className="flex items-center">
          <span className="w-2 h-2 bg-success rounded-full inline-block mr-2 shadow-[0_0_0_2px_rgba(16,185,129,0.2)]"></span>
          System Online (14ms)
        </span>
        <span>Model: T-CBN-v4.2</span>
        <span>User: Dr. Zhang</span>
      </div>
    </header>
  );
};

