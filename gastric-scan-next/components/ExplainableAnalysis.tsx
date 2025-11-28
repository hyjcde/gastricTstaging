"use client";

import React, { useState, useCallback } from 'react';
import { Patient } from '@/types';
import { useSettings } from '@/contexts/SettingsContext';
import { 
  Activity, 
  AlertTriangle, 
  CheckCircle, 
  Loader2, 
  X,
  TrendingUp,
  Shield,
  Target
} from 'lucide-react';

interface ExplainableAnalysisProps {
  patient: Patient | null;
  isOpen: boolean;
  onClose: () => void;
}

interface AnalysisResult {
  success: boolean;
  patient_id: string;
  predicted_stage?: string;
  confidence?: string;
  sii?: number;
  bci?: number;
  cri?: number;
  composite_score?: number;
  explanation?: string;
  total_danger_regions?: number;
  visualization_base64?: string;
  error?: string;
}

// API 配置
const API_BASE_URL = process.env.NEXT_PUBLIC_EXPLAINABLE_API_URL || 'http://localhost:8001';

export const ExplainableAnalysis: React.FC<ExplainableAnalysisProps> = ({
  patient,
  isOpen,
  onClose
}) => {
  const { language } = useSettings();
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<AnalysisResult | null>(null);
  const [error, setError] = useState<string | null>(null);

  const runAnalysis = useCallback(async () => {
    if (!patient) return;

    setLoading(true);
    setError(null);
    setResult(null);

    try {
      // 从 patient 的 image_url 中提取文件名
      // URL 格式: /api/images/Chemo_2MC_1396900%20(2).jpg?cohort=2025&treatment=nac
      const imageUrl = patient.image_url;
      // 先移除查询参数，再提取文件名
      const urlWithoutParams = imageUrl.split('?')[0];
      const encodedName = urlWithoutParams.split('/').pop() || '';
      // 解码 URL 编码（%20 -> 空格）
      const imageName = decodeURIComponent(encodedName);
      
      const response = await fetch(`${API_BASE_URL}/analyze`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          patient_id: patient.id,
          image_name: imageName
        })
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const data: AnalysisResult = await response.json();
      
      if (data.success) {
        setResult(data);
      } else {
        setError(data.error || 'Analysis failed');
      }
    } catch (err) {
      console.error('Analysis error:', err);
      setError(err instanceof Error ? err.message : 'Failed to connect to analysis server');
    } finally {
      setLoading(false);
    }
  }, [patient]);

  if (!isOpen) return null;

  const getStageColor = (stage?: string) => {
    if (!stage) return 'text-gray-400';
    if (stage.includes('T4')) return 'text-red-400';
    if (stage.includes('T3')) return 'text-orange-400';
    if (stage.includes('T2')) return 'text-yellow-400';
    return 'text-green-400';
  };

  const getConfidenceColor = (confidence?: string) => {
    if (confidence === 'High') return 'text-green-400';
    if (confidence === 'Medium') return 'text-yellow-400';
    return 'text-gray-400';
  };

  const getMetricColor = (value: number, thresholds: [number, number]) => {
    if (value >= thresholds[1]) return 'text-green-400';
    if (value >= thresholds[0]) return 'text-yellow-400';
    return 'text-red-400';
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-sm">
      <div className="bg-[#0a0a0a] border border-white/10 rounded-2xl w-[95vw] max-w-6xl max-h-[90vh] overflow-hidden flex flex-col shadow-2xl">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-white/10 bg-[#111]">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-emerald-500/20 rounded-lg">
              <Activity className="w-5 h-5 text-emerald-400" />
            </div>
            <div>
              <h2 className="text-lg font-bold text-white">
                {language === 'zh' ? '边界可解释性分析' : 'Boundary Explainability Analysis'}
              </h2>
              <p className="text-xs text-gray-400">
                {language === 'zh' 
                  ? '法向梯度边界验证' 
                  : 'Normal-gradient boundary verification'}
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-2 hover:bg-white/10 rounded-lg transition-colors"
          >
            <X className="w-5 h-5 text-gray-400" />
          </button>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-auto p-6">
          {!result && !loading && !error && (
            <div className="flex flex-col items-center justify-center h-full min-h-[400px] gap-6">
              <div className="p-6 bg-emerald-500/10 rounded-full">
                <Activity className="w-16 h-16 text-emerald-400" />
              </div>
              <div className="text-center">
                <h3 className="text-xl font-semibold text-white mb-2">
                  {language === 'zh' ? '准备分析' : 'Ready to Analyze'}
                </h3>
                <p className="text-gray-400 max-w-md">
                  {language === 'zh' 
                    ? '点击下方按钮开始边界分析。算法将验证肿瘤边界的完整性，检测可能的浆膜侵犯。'
                    : 'Click the button below to start boundary analysis. The algorithm will verify tumor boundary integrity and detect potential serosal invasion.'}
                </p>
              </div>
              <button
                onClick={runAnalysis}
                disabled={!patient}
                className="px-8 py-3 bg-emerald-600 hover:bg-emerald-500 text-white font-medium rounded-xl transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
              >
                <Activity className="w-5 h-5" />
                {language === 'zh' ? '开始分析' : 'Start Analysis'}
              </button>
            </div>
          )}

          {loading && (
            <div className="flex flex-col items-center justify-center h-full min-h-[400px] gap-4">
              <Loader2 className="w-12 h-12 text-blue-400 animate-spin" />
              <p className="text-gray-400">
                {language === 'zh' ? '正在分析中...' : 'Analyzing...'}
              </p>
            </div>
          )}

          {error && (
            <div className="flex flex-col items-center justify-center h-full min-h-[400px] gap-4">
              <div className="p-4 bg-red-500/10 rounded-full">
                <AlertTriangle className="w-12 h-12 text-red-400" />
              </div>
              <div className="text-center">
                <h3 className="text-lg font-semibold text-red-400 mb-2">
                  {language === 'zh' ? '分析失败' : 'Analysis Failed'}
                </h3>
                <p className="text-gray-400 max-w-md mb-4">{error}</p>
                <button
                  onClick={runAnalysis}
                  className="px-6 py-2 bg-white/10 hover:bg-white/20 text-white rounded-lg transition-colors"
                >
                  {language === 'zh' ? '重试' : 'Retry'}
                </button>
              </div>
            </div>
          )}

          {result && result.success && (
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              {/* 左侧：可视化图像 */}
              <div className="bg-[#111] rounded-xl border border-white/5 overflow-hidden">
                <div className="px-4 py-3 border-b border-white/5 flex items-center gap-2">
                  <Target className="w-4 h-4 text-blue-400" />
                  <span className="text-sm font-medium text-gray-300">
                    {language === 'zh' ? '风险可视化' : 'Risk Visualization'}
                  </span>
                </div>
                <div className="p-2">
                  {result.visualization_base64 && (
                    <img 
                      src={`data:image/png;base64,${result.visualization_base64}`}
                      alt="Analysis Visualization"
                      className="w-full h-auto rounded-lg"
                    />
                  )}
                </div>
              </div>

              {/* 右侧：分析结果 */}
              <div className="space-y-4">
                {/* 预测结果卡片 */}
                <div className="bg-gradient-to-br from-[#111] to-[#0a0a0a] rounded-xl border border-white/5 p-5">
                  <div className="flex items-center justify-between mb-4">
                    <h3 className="text-sm font-bold text-gray-400 uppercase tracking-wider">
                      {language === 'zh' ? '预测结果' : 'Prediction'}
                    </h3>
                    <div className={`flex items-center gap-1 text-xs ${getConfidenceColor(result.confidence)}`}>
                      <CheckCircle className="w-3 h-3" />
                      {result.confidence} Confidence
                    </div>
                  </div>
                  <div className="flex items-baseline gap-2">
                    <span className={`text-4xl font-bold ${getStageColor(result.predicted_stage)}`}>
                      {result.predicted_stage}
                    </span>
                    <span className="text-gray-500 text-sm">Stage</span>
                  </div>
                  <p className="mt-3 text-sm text-gray-400 leading-relaxed">
                    {result.explanation}
                  </p>
                </div>

                {/* 指标卡片 */}
                <div className="grid grid-cols-2 gap-3">
                  {/* SII */}
                  <div className="bg-[#111] rounded-xl border border-white/5 p-4">
                    <div className="flex items-center gap-2 mb-2">
                      <Shield className="w-4 h-4 text-blue-400" />
                      <span className="text-xs text-gray-400">SII</span>
                    </div>
                    <div className={`text-2xl font-bold ${getMetricColor(result.sii || 0, [0.25, 0.4])}`}>
                      {(result.sii || 0).toFixed(3)}
                    </div>
                    <div className="text-[10px] text-gray-500 mt-1">
                      {language === 'zh' ? '浆膜完整性' : 'Serosal Integrity'}
                    </div>
                  </div>

                  {/* BCI */}
                  <div className="bg-[#111] rounded-xl border border-white/5 p-4">
                    <div className="flex items-center gap-2 mb-2">
                      <Activity className="w-4 h-4 text-purple-400" />
                      <span className="text-xs text-gray-400">BCI</span>
                    </div>
                    <div className={`text-2xl font-bold ${getMetricColor(result.bci || 0, [0.5, 0.7])}`}>
                      {(result.bci || 0).toFixed(3)}
                    </div>
                    <div className="text-[10px] text-gray-500 mt-1">
                      {language === 'zh' ? '边界相关性' : 'Boundary Correlation'}
                    </div>
                  </div>

                  {/* CRI */}
                  <div className="bg-[#111] rounded-xl border border-white/5 p-4">
                    <div className="flex items-center gap-2 mb-2">
                      <TrendingUp className="w-4 h-4 text-orange-400" />
                      <span className="text-xs text-gray-400">CRI</span>
                    </div>
                    <div className={`text-2xl font-bold ${getMetricColor(result.cri || 0, [0.7, 0.85])}`}>
                      {(result.cri || 0).toFixed(3)}
                    </div>
                    <div className="text-[10px] text-gray-500 mt-1">
                      {language === 'zh' ? '曲率风险' : 'Curvature Risk'}
                    </div>
                  </div>

                  {/* Danger Zones */}
                  <div className="bg-[#111] rounded-xl border border-white/5 p-4">
                    <div className="flex items-center gap-2 mb-2">
                      <AlertTriangle className="w-4 h-4 text-red-400" />
                      <span className="text-xs text-gray-400">
                        {language === 'zh' ? '危险区域' : 'Danger Zones'}
                      </span>
                    </div>
                    <div className={`text-2xl font-bold ${
                      (result.total_danger_regions || 0) > 5 ? 'text-red-400' :
                      (result.total_danger_regions || 0) > 2 ? 'text-yellow-400' : 'text-green-400'
                    }`}>
                      {result.total_danger_regions || 0}
                    </div>
                    <div className="text-[10px] text-gray-500 mt-1">
                      {language === 'zh' ? '检测到的可疑区域' : 'Detected suspicious areas'}
                    </div>
                  </div>
                </div>

                {/* 综合评分 */}
                <div className="bg-[#111] rounded-xl border border-white/5 p-4">
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-xs text-gray-400">
                      {language === 'zh' ? '综合评分' : 'Composite Score'}
                    </span>
                    <span className={`text-lg font-bold ${getMetricColor(result.composite_score || 0, [0.4, 0.6])}`}>
                      {(result.composite_score || 0).toFixed(3)}
                    </span>
                  </div>
                  <div className="w-full h-2 bg-white/5 rounded-full overflow-hidden">
                    <div 
                      className={`h-full rounded-full transition-all ${
                        (result.composite_score || 0) >= 0.6 ? 'bg-green-500' :
                        (result.composite_score || 0) >= 0.4 ? 'bg-yellow-500' : 'bg-red-500'
                      }`}
                      style={{ width: `${(result.composite_score || 0) * 100}%` }}
                    />
                  </div>
                </div>

                {/* 重新分析按钮 */}
                <button
                  onClick={runAnalysis}
                  className="w-full px-4 py-3 bg-white/5 hover:bg-white/10 text-gray-300 rounded-xl transition-colors flex items-center justify-center gap-2"
                >
                  <Activity className="w-4 h-4" />
                  {language === 'zh' ? '重新分析' : 'Re-analyze'}
                </button>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

