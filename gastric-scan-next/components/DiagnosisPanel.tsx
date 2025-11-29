"use client";

import React from 'react';
import { useSettings } from '@/contexts/SettingsContext';
import { calculateDiagnosis, generateNarrativeReport, generateSummaryPoints, getFeatureDescriptions } from '@/lib/diagnosis';
import { ConceptState, Patient } from '@/types';
import { Activity, AlignLeft, BarChart2, ChevronDown, FileText, Maximize2, Ruler, Tag, Terminal, User, X, Download, FileDown } from 'lucide-react';
import React, { useEffect, useMemo, useState } from 'react';
import { exportReportToPDF, exportSinglePatientToCSV } from '@/lib/export-utils';
import toast from 'react-hot-toast';

interface DiagnosisPanelProps {
  state: ConceptState;
  patient: Patient | null;
  onExpandedChange?: (expanded: boolean) => void;
}

export const DiagnosisPanel: React.FC<DiagnosisPanelProps> = React.memo(({ state, patient, onExpandedChange }) => {
  const { t, language } = useSettings();
  const [reportText, setReportText] = useState('');
  const [isExpanded, setIsExpanded] = useState(false);
  const [activeTab, setActiveTab] = useState<'diagnosis' | 'clinical'>('diagnosis');

  const toggleExpanded = () => {
    const newExpanded = !isExpanded;
    setIsExpanded(newExpanded);
    onExpandedChange?.(newExpanded);
  };

  const diagnosis = useMemo(() => calculateDiagnosis(state, patient), [state, patient]);
  const { tStage, nStage, probabilities, confidence, scores, flags, validation, reasoning } = diagnosis;
  
  const descriptions = useMemo(() => getFeatureDescriptions(state, language as 'zh' | 'en'), [state, language]);

  const conceptFeatures = useMemo(() => {
    if (patient?.clinical?.concept_features) {
      return patient.clinical.concept_features;
    }
    return null;
  }, [patient?.clinical]);

  const formatConceptValue = (value?: string) => value ?? (language === 'zh' ? '未记录' : 'N/A');
  const actualFeatureRows = useMemo(() => {
    if (!conceptFeatures) return [];
    return [
      { label: language === 'zh' ? 'Ki-67（实际）' : 'Ki-67 (actual)', value: formatConceptValue(conceptFeatures.ki67) },
      { label: language === 'zh' ? 'CPS（实际）' : 'CPS (actual)', value: formatConceptValue(conceptFeatures.cps) },
      { label: language === 'zh' ? 'PD-1（实际）' : 'PD-1 (actual)', value: formatConceptValue(conceptFeatures.pd1) },
      { label: language === 'zh' ? 'FoxP3（实际）' : 'FoxP3 (actual)', value: formatConceptValue(conceptFeatures.foxp3) },
      { label: language === 'zh' ? 'CD3（实际）' : 'CD3 (actual)', value: formatConceptValue(conceptFeatures.cd3) },
      { label: language === 'zh' ? 'CD4（实际）' : 'CD4 (actual)', value: formatConceptValue(conceptFeatures.cd4) },
      { label: language === 'zh' ? 'CD8（实际）' : 'CD8 (actual)', value: formatConceptValue(conceptFeatures.cd8) },
      { label: language === 'zh' ? '脉管/血管' : 'Vascular/lymphatic', value: formatConceptValue(conceptFeatures.vascular) },
      { label: language === 'zh' ? '神经侵犯' : 'Neural invasion', value: formatConceptValue(conceptFeatures.neural) },
      { label: language === 'zh' ? '分化程度' : 'Differentiation', value: formatConceptValue(conceptFeatures.differentiation) },
      { label: language === 'zh' ? 'Lauren 分型' : 'Lauren class', value: formatConceptValue(conceptFeatures.lauren) }
    ];
  }, [conceptFeatures, language]);

  const structuredReportSections = useMemo(() => {
    const imagingFindings = [
      descriptions.ki67,
      descriptions.cps,
      descriptions.pd1,
      descriptions.foxp3,
      state.vascularInvasion ? (language === 'zh' ? '伴脉管侵犯。' : 'Vascular invasion present.') : '',
      state.neuralInvasion ? (language === 'zh' ? '伴神经侵犯。' : 'Neural invasion present.') : ''
    ].filter(Boolean).join(' ');

    const tumorSizeData = patient?.clinical?.tumorSize;
    const lesionSizeValue =
      tumorSizeData?.length && tumorSizeData?.thickness
        ? `${tumorSizeData.length} × ${tumorSizeData.thickness} cm${
            tumorSizeData.length && tumorSizeData.thickness
              ? ` (${(tumorSizeData.length * tumorSizeData.thickness).toFixed(1)} cm²)`
              : ''
          }`
        : language === 'zh'
          ? '待补充'
          : 'Pending measurement';

    const lymphStatusText = flags.hasMetastasis
      ? language === 'zh'
        ? `提示区域淋巴结转移（${nStage}），参考 FoxP3/Lauren/CPS 综合风险。`
        : `Regional nodal spread suspected (${nStage}), supported by FoxP3/Lauren/CPS risk.`
      : language === 'zh'
        ? '未见明确淋巴结转移高危信号（N0）。'
        : 'No definitive high-risk nodal signals (N0).';

    const stageText = language === 'zh'
      ? `CBM模型推断 ${tStage}${nStage}（置信度 ${confidence.overall}%）。`
      : `CBM Model infers ${tStage}${nStage} with ${confidence.overall}% confidence.`;

    const recommendationText = flags.highRisk
      ? language === 'zh'
        ? '建议尽快完善病理亚型检测，评估新辅助化疗获益。'
        : 'Recommend completing pathology subtyping and assessing neoadjuvant benefit.'
      : language === 'zh'
        ? '倾向早期病变，建议内镜下切除或腹腔镜手术评估。'
        : 'Suggests early lesion; consider ESD or laparoscopic assessment.';

    return [
      {
        key: 'findings',
        label: language === 'zh' ? '病理特征' : 'Pathological Features',
        value: imagingFindings
      },
      {
        key: 'size',
        label: language === 'zh' ? '病灶尺寸' : 'Lesion size',
        value: lesionSizeValue
      },
      {
        key: 'nodes',
        label: language === 'zh' ? '淋巴结评估' : 'Lymph node assessment',
        value: lymphStatusText
      },
      {
        key: 'stage',
        label: language === 'zh' ? '分期推断' : 'Stage inference',
        value: stageText
      },
      {
        key: 'recommendation',
        label: language === 'zh' ? '建议后续' : 'Recommended action',
        value: recommendationText
      }
    ];
  }, [
    descriptions,
    language,
    patient?.clinical?.tumorSize,
    tStage,
    nStage,
    confidence.overall,
    flags.hasMetastasis,
    flags.highRisk,
    state.vascularInvasion,
    state.neuralInvasion
  ]);

  const smartSummaryPoints = useMemo(() => 
    generateSummaryPoints(state, diagnosis, patient, language as 'zh' | 'en'),
    [state, diagnosis, patient, language]
  );

  useEffect(() => {
    if (!patient) {
      setReportText(t.diagnosis.waiting);
      return;
    }

    const lines = generateNarrativeReport(state, diagnosis, patient, language as 'zh' | 'en');
    const fullText = lines.join("\n");
    let i = 0;
    setReportText('');
    const timer = setInterval(() => {
        if (i < fullText.length) {
            setReportText(prev => prev + fullText.charAt(i));
            i++;
        } else {
            clearInterval(timer);
        }
    }, 2);

    return () => clearInterval(timer);
  }, [patient, state, language, diagnosis, t]);

  const renderBar = (label: string, prob: number, color: string) => (
    <div className="flex items-center gap-2 text-[10px] font-mono mb-1.5">
        <span className="w-8 text-gray-500 text-right">{label}</span>
        <div className="flex-1 h-1.5 bg-[#222] rounded-full overflow-hidden">
            <div className={`h-full ${color} transition-all duration-500`} style={{ width: `${prob}%` }}></div>
        </div>
        <span className="w-6 text-gray-400 text-right">{Math.floor(prob)}%</span>
    </div>
  );

  // Risk Gauge Render Function - 紧凑版
  const renderRiskGauge = (score: number) => {
      const color = score > 80 ? 'text-red-500' : score > 50 ? 'text-amber-500' : 'text-emerald-500';
      
      return (
          <div className="flex flex-col items-center">
              <div className="relative w-14 h-7 overflow-hidden">
                  <svg viewBox="0 0 100 50" className="absolute top-0 left-1/2 -translate-x-1/2 w-14 h-7 overflow-visible">
                      <path d="M 10 50 A 40 40 0 0 1 90 50" fill="none" stroke="#333" strokeWidth="10" strokeLinecap="round" />
                      <path 
                        d="M 10 50 A 40 40 0 0 1 90 50" 
                        fill="none" 
                        stroke={score > 80 ? '#ef4444' : score > 50 ? '#f59e0b' : '#10b981'} 
                        strokeWidth="10" 
                        strokeLinecap="round"
                        strokeDasharray="126"
                        strokeDashoffset={126 - (126 * score / 100)}
                        className="transition-all duration-500 ease-out"
                      />
                  </svg>
                  <div className={`absolute bottom-0 left-1/2 -translate-x-1/2 text-xs font-bold ${color}`}>
                      {score}
                  </div>
              </div>
              <div className="text-[7px] text-gray-600 uppercase mt-0.5">Risk</div>
          </div>
      )
  }

  return (
    <div className="flex flex-col h-full w-full bg-bg-dark relative">
      {/* Fullscreen Modal */}
      {isExpanded && (
        <div 
          className="fixed bg-black/95 backdrop-blur-md flex items-center justify-center p-0" 
          style={{ 
            top: '64px', 
            left: 0, 
            right: 0, 
            bottom: 0,
            width: '100vw',
            height: 'calc(100vh - 64px)',
            zIndex: 99999
          }}
        >
            <div 
              className="w-full h-full bg-bg-dark border-x-0 border-t-0 border-b-0 border-neutral-700 shadow-2xl flex flex-col overflow-hidden" 
            >
                {/* Header */}
                <div className="h-20 shrink-0 border-b border-neutral-800 flex items-center justify-between px-8 bg-linear-to-r from-neutral-900 via-neutral-800 to-neutral-900 shadow-lg">
                    <div className="flex items-center gap-4">
                        <div className="p-2 bg-emerald-500/20 rounded-lg border border-emerald-500/30">
                            <FileText size={20} className="text-emerald-400" /> 
                        </div>
                        <div>
                            <div className="text-sm font-bold text-gray-200 uppercase tracking-widest">
                                {t.diagnosis.report_header || "Detailed Medical Report"}
                            </div>
                            <div className="text-xs text-gray-500 mt-0.5">
                                {patient?.id_short || 'N/A'} • {new Date().toLocaleString(language === 'zh' ? 'zh-CN' : 'en-US')}
                            </div>
                        </div>
                    </div>
                    <div className="flex items-center gap-2">
                        <button
                            onClick={async () => {
                                if (!patient) {
                                    toast.error(language === 'zh' ? '请先选择患者' : 'Please select a patient first');
                                    return;
                                }
                                try {
                                    toast.loading(language === 'zh' ? '正在导出 PDF...' : 'Exporting PDF...', { id: 'export-pdf' });
                                    await exportReportToPDF(
                                        'diagnosis-report-content',
                                        `report_${patient.id_short}_${Date.now()}.pdf`
                                    );
                                    toast.success(language === 'zh' ? 'PDF 导出成功' : 'PDF exported successfully', { id: 'export-pdf' });
                                } catch (error) {
                                    console.error('Export failed:', error);
                                    toast.error(language === 'zh' ? 'PDF 导出失败' : 'Failed to export PDF', { id: 'export-pdf' });
                                }
                            }}
                            className="p-2.5 hover:bg-blue-500/20 rounded-lg transition-colors text-blue-400 hover:text-blue-300 border border-blue-500/30 hover:border-blue-500/50"
                            title={language === 'zh' ? '导出 PDF' : 'Export PDF'}
                        >
                            <FileDown size={18} />
                        </button>
                        <button
                            onClick={() => {
                                if (!patient) {
                                    toast.error(language === 'zh' ? '请先选择患者' : 'Please select a patient first');
                                    return;
                                }
                                try {
                                    exportSinglePatientToCSV(patient, state, diagnosis, `patient_${patient.id_short}_${Date.now()}.csv`);
                                    toast.success(language === 'zh' ? 'CSV 导出成功' : 'CSV exported successfully');
                                } catch (error) {
                                    console.error('Export failed:', error);
                                    toast.error(language === 'zh' ? 'CSV 导出失败' : 'Failed to export CSV');
                                }
                            }}
                            className="p-2.5 hover:bg-emerald-500/20 rounded-lg transition-colors text-emerald-400 hover:text-emerald-300 border border-emerald-500/30 hover:border-emerald-500/50"
                            title={language === 'zh' ? '导出 CSV' : 'Export CSV'}
                        >
                            <Download size={18} />
                        </button>
                        <button 
                            onClick={toggleExpanded}
                            className="p-2.5 hover:bg-white/10 rounded-lg transition-colors text-gray-400 hover:text-white border border-white/10 hover:border-white/20"
                            title={language === 'zh' ? '关闭' : 'Close'}
                        >
                            <X size={20} />
                        </button>
                    </div>
                </div>
                
                <div className="flex-1 overflow-y-auto custom-scrollbar">
                    <div id="diagnosis-report-content" className="grid grid-cols-3 gap-8 p-10">
                        {/* Left Column: Main Report */}
                        <div className="col-span-2 space-y-6">
                            {/* ... (Patient Info Card - same as before) ... */}
                            {/* Simplified for brevity in this write, assuming standard layout */}
                            <div className="bg-linear-to-br from-neutral-900/90 to-neutral-800/50 p-7 rounded-2xl border border-neutral-700/50 shadow-xl">
                                <div className="flex items-start justify-between mb-5">
                                    <div className="flex-1">
                                        <div className="text-3xl font-bold text-gray-100 font-mono mb-4">{patient?.id_short || 'N/A'}</div>
                                    </div>
                                </div>
                            </div>

                            {/* Stage Prediction Card */}
                            <div className={`bg-linear-to-br ${flags.isT4 || flags.hasMetastasis ? 'from-red-900/40 to-red-800/20' : 'from-emerald-900/40 to-emerald-800/20'} p-8 rounded-2xl border-2 ${flags.isT4 || flags.hasMetastasis ? 'border-red-500/50 shadow-[0_0_30px_rgba(239,68,68,0.2)]' : 'border-emerald-500/50 shadow-[0_0_30px_rgba(16,185,129,0.2)]'} relative overflow-hidden`}>
                                <div className="relative z-10">
                                    <div className="flex items-start justify-between mb-6">
                                        <div className="flex-1">
                                            <div className={`text-7xl font-black tracking-tighter mb-3 ${flags.isT4 || flags.hasMetastasis ? 'text-red-400' : 'text-emerald-400'} drop-shadow-lg`}>
                                                {tStage}{nStage}
                                            </div>
                                            <div className="flex items-center gap-4 text-sm">
                                                <div className="text-gray-400">
                                                    {language === 'zh' ? '综合置信度' : 'Overall Confidence'}: 
                                                </div>
                                                <div className="px-3 py-1 bg-white/10 rounded-lg border border-white/20">
                                                    <span className="text-emerald-400 font-bold text-lg">{confidence.overall}%</span>
                                                </div>
                                            </div>
                                        </div>
                                        <div className="ml-6">
                                            {renderRiskGauge(Math.floor((scores.t + scores.n)/2))}
                                        </div>
                                    </div>
                                </div>
                            </div>

                            {/* Feature Analysis */}
                            <div className="bg-linear-to-br from-neutral-900/90 to-neutral-800/50 p-7 rounded-2xl border border-neutral-700/50 shadow-xl">
                                <div className="flex items-center gap-2 mb-6">
                                    <BarChart2 size={18} className="text-blue-400" />
                                    <div className="text-sm font-bold text-gray-300 uppercase tracking-wider">{language === 'zh' ? '特征分析' : 'Feature Analysis'}</div>
                                </div>
                                <div className="grid grid-cols-2 gap-4">
                                    {[
                                        { label: 'Ki-67', value: state.c1, color: '#ef4444' },
                                        { label: 'CPS', value: state.c2, color: '#f59e0b' },
                                        { label: 'PD-1', value: state.c3, color: '#3b82f6' },
                                        { label: 'FoxP3', value: state.c4, color: '#a855f7' }
                                    ].map((feature, idx) => (
                                        <div key={idx} className="p-4 bg-white/5 rounded-xl border border-white/10 space-y-3">
                                            <div className="flex items-center justify-between">
                                                <span className="text-sm text-gray-300 font-medium">{feature.label}</span>
                                                <span className="text-lg text-gray-200 font-bold font-mono">{Math.floor(feature.value)}%</span>
                                            </div>
                                            <div className="h-3 bg-neutral-800 rounded-full overflow-hidden shadow-inner">
                                                <div 
                                                    className="h-full transition-all duration-700 rounded-full"
                                                    style={{ width: `${feature.value}%`, backgroundColor: feature.color }}
                                                ></div>
                                            </div>
                                        </div>
                                    ))}
                                </div>
                            </div>

                            {/* Detailed Report Text */}
                            <div className="bg-linear-to-br from-black/80 to-neutral-900/60 p-7 rounded-2xl border border-neutral-800/50 shadow-xl">
                                <div className="flex items-center gap-2 mb-5">
                                    <Terminal size={18} className="text-emerald-400" />
                                    <div className="text-sm font-bold text-gray-300 uppercase tracking-wider">{language === 'zh' ? '详细报告' : 'Detailed Report'}</div>
                                </div>
                                <div className="bg-black/40 p-6 rounded-lg border border-neutral-700/50">
                                    <pre className="font-mono text-sm leading-relaxed text-gray-300 whitespace-pre-wrap typing-cursor">{reportText}</pre>
                                </div>
                            </div>
                        </div>

                        {/* Right Column: Visualizations */}
                        <div className="space-y-6">
                            <div className="bg-linear-to-br from-neutral-900/80 to-neutral-800/40 p-6 rounded-xl border border-neutral-700/50">
                                <div className="text-xs text-gray-400 uppercase tracking-wider mb-4">{language === 'zh' ? '分期概率分布' : 'Stage Probability'}</div>
                                <div className="space-y-4">
                                    <div>
                                        <div className="text-[10px] text-gray-500 mb-2">T-{language === 'zh' ? '分期' : 'Stage'}</div>
                                        {renderBar('T4', probabilities.t4, 'bg-red-500')}
                                        {renderBar('T3', probabilities.t3, 'bg-amber-500')}
                                        {renderBar('T1-2', probabilities.t2, 'bg-emerald-500')}
                                    </div>
                                    <div className="pt-4 border-t border-neutral-700">
                                        <div className="text-[10px] text-gray-500 mb-2">N-{language === 'zh' ? '分期' : 'Stage'}</div>
                                        {renderBar('N0', probabilities.n0, 'bg-emerald-500')}
                                        {renderBar('N1', probabilities.n1, 'bg-yellow-500')}
                                        {renderBar('N2', probabilities.n2, 'bg-orange-500')}
                                        {renderBar('N3', probabilities.n3, 'bg-red-500')}
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
      )}

      {/* Minimized Panel */}
      <div className="h-9 shrink-0 border-b border-neutral-800 flex items-center justify-between px-3 bg-bg-dark">
        <div className="flex gap-2">
            <button 
                onClick={() => setActiveTab('diagnosis')}
                className={`flex items-center gap-2 text-[11px] font-bold uppercase tracking-widest transition-all px-3 py-1.5 rounded-md ${
                    activeTab === 'diagnosis' 
                        ? 'text-emerald-400 bg-emerald-500/20 border border-emerald-500/40 shadow-[0_0_10px_rgba(16,185,129,0.2)]' 
                        : 'text-gray-500 hover:text-gray-300 hover:bg-white/5'
                }`}
            >
                <FileText size={12} /> 
          {t.diagnosis.title}
            </button>
            <button 
                onClick={() => setActiveTab('clinical')}
                className={`flex items-center gap-2 text-[11px] font-bold uppercase tracking-widest transition-all px-3 py-1.5 rounded-md relative ${
                    activeTab === 'clinical' 
                        ? 'text-blue-400 bg-blue-500/20 border border-blue-500/40 shadow-[0_0_10px_rgba(59,130,246,0.2)]' 
                        : 'text-gray-500 hover:text-gray-300 hover:bg-white/5'
                } ${!patient?.clinical ? 'opacity-60' : ''}`}
                title={!patient?.clinical ? t.diagnosis.no_clinical : t.diagnosis.clinical}
            >
                <Activity size={12} /> 
                {t.diagnosis.clinical.toUpperCase()}
                {patient?.clinical && (
                    <span className="absolute -top-1 -right-1 w-2 h-2 bg-blue-500 rounded-full animate-pulse"></span>
                )}
            </button>
        </div>
        <div className="flex items-center gap-1">
            <button
                onClick={() => {
                    if (!patient) {
                        toast.error(language === 'zh' ? '请先选择患者' : 'Please select a patient first');
                        return;
                    }
                    try {
                        exportSinglePatientToCSV(patient, state, diagnosis, `patient_${patient.id_short}_${Date.now()}.csv`);
                        toast.success(language === 'zh' ? 'CSV 导出成功' : 'CSV exported successfully');
                    } catch (error) {
                        console.error('Export failed:', error);
                        toast.error(language === 'zh' ? 'CSV 导出失败' : 'Failed to export CSV');
                    }
                }}
                className="p-1 hover:bg-emerald-500/20 rounded transition-colors text-gray-500 hover:text-emerald-400"
                title={language === 'zh' ? '导出 CSV' : 'Export CSV'}
            >
                <Download size={12} />
            </button>
            <button 
                onClick={toggleExpanded}
                className="p-1 hover:bg-white/10 rounded transition-colors text-gray-500 hover:text-emerald-400"
                title="Expand Report"
            >
                <Maximize2 size={12} />
            </button>
        </div>
      </div>

      <div className="flex-1 flex flex-col min-h-0">
        {activeTab === 'diagnosis' ? (
            <>
                {/* Probabilities Section - Compact 2 Columns */}
                <div className="shrink-0 p-3 border-b border-neutral-800 bg-neutral-900/30 grid grid-cols-2 gap-4">
                {/* Column 1: T-Stage */}
                <div>
                    <div className="flex items-center gap-2 mb-2">
                        <BarChart2 size={10} className="text-blue-400" />
                        <span className="text-[9px] font-bold text-gray-500 uppercase tracking-wider">T-Stage</span>
                    </div>
                    {renderBar('T4', probabilities.t4, 'bg-red-500')}
                    {renderBar('T3', probabilities.t3, 'bg-amber-500')}
                    {renderBar('T1-2', probabilities.t2, 'bg-emerald-500')}
                </div>
                
                {/* Column 2: N-Stage */}
                <div>
                    <div className="flex items-center gap-2 mb-2">
                        <BarChart2 size={10} className="text-purple-400" />
                        <span className="text-[9px] font-bold text-gray-500 uppercase tracking-wider">N-Stage</span>
                    </div>
                    {renderBar('N0', probabilities.n0, 'bg-emerald-500')}
                    {renderBar('N1', probabilities.n1, 'bg-yellow-500')}
                    {renderBar('N2', probabilities.n2, 'bg-orange-500')}
                    {renderBar('N3', probabilities.n3, 'bg-red-500')}
                </div>
                </div>

                {/* Prediction Header - 术前评估模式 */}
                <div className="shrink-0 p-3 border-b border-neutral-800 bg-neutral-900/50 relative overflow-hidden">
                  {/* 顶部状态条 - 根据紧迫程度显示颜色 */}
                  <div className={`absolute top-0 left-0 w-full h-1 ${
                    diagnosis.preoperativeAdvice?.urgency === 'urgent' ? 'bg-red-500 animate-pulse' : 
                    diagnosis.preoperativeAdvice?.urgency === 'priority' ? 'bg-amber-500' : 'bg-emerald-500'
                  } shadow-[0_0_15px_currentColor]`}></div>
                        
                  <div className="flex items-center justify-between w-full">
                    {/* Left: AI Prediction - 临床分期 */}
                    <div className="flex flex-col items-center flex-1">
                      <div className="text-[8px] font-mono uppercase text-gray-500 mb-0.5">
                        {language === 'zh' ? '临床分期预测' : 'Clinical Stage'}
                      </div>
                      <div className={`text-2xl font-black tracking-tighter ${flags.isT4 || flags.hasMetastasis ? 'text-amber-400' : 'text-emerald-400'}`}>
                        c{tStage}{nStage}
                      </div>
                      <div className="text-[8px] font-mono text-gray-500">
                        {language === 'zh' ? '置信度' : 'Confidence'}: {confidence.overall}%
                      </div>
                    </div>

                    {/* Middle: Urgency Badge */}
                    <div className="flex flex-col items-center px-3">
                      <div className={`px-2 py-1 rounded text-[9px] font-bold uppercase ${
                        diagnosis.preoperativeAdvice?.urgency === 'urgent' ? 'bg-red-500/20 text-red-400 border border-red-500/30' : 
                        diagnosis.preoperativeAdvice?.urgency === 'priority' ? 'bg-amber-500/20 text-amber-400 border border-amber-500/30' : 
                        'bg-emerald-500/20 text-emerald-400 border border-emerald-500/30'
                      }`}>
                        {diagnosis.preoperativeAdvice?.urgency === 'urgent' 
                          ? (language === 'zh' ? '紧急' : 'URGENT')
                          : diagnosis.preoperativeAdvice?.urgency === 'priority' 
                            ? (language === 'zh' ? '优先' : 'PRIORITY')
                            : (language === 'zh' ? '常规' : 'ROUTINE')}
                      </div>
                      {diagnosis.preoperativeAdvice?.mdtRequired && (
                        <div className="text-[7px] text-amber-400 mt-1">MDT</div>
                      )}
                    </div>

                    {/* Right: Risk Gauge */}
                    <div>
                      {renderRiskGauge(Math.floor((scores.t + scores.n)/2))}
                    </div>
                  </div>

                  {/* 病理对比 - 仅在有病理数据时显示（术后回顾模式） */}
                  {validation?.groundTruth && (
                    <div className="mt-2 pt-2 border-t border-neutral-700/50">
                      <div className="flex items-center justify-between">
                        <div className="text-xs text-gray-500 uppercase">
                          {language === 'zh' ? '术后病理对照' : 'Post-op Pathology'}
                        </div>
                        <div className="flex items-center gap-2">
                          <span className="text-sm font-mono font-bold text-blue-400">
                            p{validation.groundTruth.t}{validation.groundTruth.n}
                          </span>
                          <span className={`text-xs px-2 py-0.5 rounded font-bold ${
                            validation.discrepancy === 'none' ? 'bg-emerald-500/20 text-emerald-400' : 
                            validation.discrepancy === 'minor' ? 'bg-yellow-500/20 text-yellow-400' : 
                            'bg-red-500/20 text-red-400'
                          }`}>
                            {validation.discrepancy === 'none' ? '✓' : validation.discrepancy === 'minor' ? '≈' : '≠'}
                          </span>
                        </div>
                      </div>
                      {validation.discrepancy === 'major' && (
                        <div className="text-xs text-red-400 mt-1 font-medium">
                          {language === 'zh' ? '⚠️ 存在显著差异' : '⚠️ Major discrepancy'}
                        </div>
                      )}
                    </div>
                  )}
                </div>

                {/* 术前决策建议 - 核心模块 */}
                {diagnosis.preoperativeAdvice && (
                  <div className="shrink-0 border-b border-neutral-800 bg-neutral-900/30">
                    <details className="group" open>
                      <summary className="px-3 py-2.5 cursor-pointer flex items-center justify-between text-xs font-bold text-gray-400 uppercase tracking-wider hover:bg-white/5">
                        <span className="flex items-center gap-2">
                          <FileText size={14} className="text-blue-400" />
                          {language === 'zh' ? '术前决策建议' : 'Preop Advice'}
                        </span>
                        <ChevronDown size={14} className="group-open:rotate-180 transition-transform" />
                      </summary>
                      <div className="px-3 pb-3 space-y-3">
                        {/* 综合评估 */}
                        <div className="text-xs p-2.5 bg-blue-500/10 border border-blue-500/20 rounded">
                          <div className="text-blue-300 leading-relaxed">
                            {diagnosis.preoperativeAdvice.overallAssessment}
                          </div>
                        </div>
                        
                        {/* 建议检查 */}
                        <div className="text-xs">
                          <div className="text-amber-400 mb-1.5 flex items-center gap-1.5 font-medium">
                            <Ruler size={12} />
                            {language === 'zh' ? '建议完善检查:' : 'Recommended Workup:'}
                          </div>
                          {diagnosis.preoperativeAdvice.recommendedWorkup.map((item, i) => (
                            <div key={i} className="text-gray-400 py-0.5 pl-4">• {item}</div>
                          ))}
                        </div>
                        
                        {/* 治疗考量 */}
                        <div className="text-xs">
                          <div className="text-emerald-400 mb-1.5 flex items-center gap-1.5 font-medium">
                            <Activity size={12} />
                            {language === 'zh' ? '治疗考量:' : 'Treatment Options:'}
                          </div>
                          {diagnosis.preoperativeAdvice.treatmentConsiderations.map((item, i) => (
                            <div key={i} className="text-gray-400 py-0.5 pl-4">• {item}</div>
                          ))}
                        </div>
                        
                        {/* 不确定性说明 */}
                        <div className="text-[11px] pt-2 border-t border-neutral-800 text-gray-500">
                          <div className="flex items-center gap-1.5 mb-1">
                            <Tag size={11} />
                            {language === 'zh' ? '注意事项:' : 'Notes:'}
                          </div>
                          {diagnosis.preoperativeAdvice.uncertaintyNotes.map((note, i) => (
                            <div key={i} className="py-0.5 pl-4 text-gray-500">• {note}</div>
                          ))}
                        </div>
                      </div>
                    </details>
                  </div>
                )}

                {/* 推理依据 (Collapsible) - 次要信息 */}
                {reasoning && (
                  <div className="shrink-0 border-b border-neutral-800 bg-neutral-900/30">
                    <details className="group">
                      <summary className="px-3 py-2.5 cursor-pointer flex items-center justify-between text-xs font-bold text-gray-400 uppercase tracking-wider hover:bg-white/5">
                        <span className="flex items-center gap-2">
                          <Activity size={14} />
                          {language === 'zh' ? '分期推理依据' : 'Staging Rationale'}
                        </span>
                        <ChevronDown size={14} className="group-open:rotate-180 transition-transform" />
                      </summary>
                      <div className="px-3 pb-3 space-y-3">
                        {/* 高危因素汇总 */}
                        {(reasoning.tStageFactors.some(f => f.impact === 'negative') || 
                          reasoning.nStageFactors.some(f => f.impact === 'negative')) && (
                          <div className="text-xs p-2.5 bg-red-500/10 border border-red-500/20 rounded mb-2">
                            <div className="text-red-400 font-medium mb-1.5">
                              {language === 'zh' ? '高危因素:' : 'Risk Factors:'}
                            </div>
                            <div className="flex flex-wrap gap-1.5">
                              {[...reasoning.tStageFactors, ...reasoning.nStageFactors]
                                .filter(f => f.impact === 'negative')
                                .map((f, i) => (
                                  <span key={i} className="px-2 py-1 bg-red-500/20 text-red-300 rounded text-[11px]">
                                    {f.factor.split(' ')[0]}
                                  </span>
                                ))}
                            </div>
                          </div>
                        )}
                        
                        {/* T-Stage Factors */}
                        <div className="text-xs">
                          <div className="text-gray-500 mb-1.5 font-medium">T{language === 'zh' ? '分期因素' : '-Stage'}:</div>
                          {reasoning.tStageFactors.slice(0, 4).map((f, i) => (
                            <div key={i} className={`flex items-start gap-1.5 py-0.5 ${
                              f.impact === 'negative' ? 'text-red-400' : 
                              f.impact === 'positive' ? 'text-emerald-400' : 'text-gray-400'
                            }`}>
                              <span className="shrink-0">{f.impact === 'negative' ? '↑' : f.impact === 'positive' ? '↓' : '→'}</span>
                              <span>{f.factor}</span>
                            </div>
                          ))}
                        </div>
                        {/* N-Stage Factors */}
                        <div className="text-xs">
                          <div className="text-gray-500 mb-1.5 font-medium">N{language === 'zh' ? '分期因素' : '-Stage'}:</div>
                          {reasoning.nStageFactors.slice(0, 4).map((f, i) => (
                            <div key={i} className={`flex items-start gap-1.5 py-0.5 ${
                              f.impact === 'negative' ? 'text-red-400' : 
                              f.impact === 'positive' ? 'text-emerald-400' : 'text-gray-400'
                            }`}>
                              <span className="shrink-0">{f.impact === 'negative' ? '↑' : f.impact === 'positive' ? '↓' : '→'}</span>
                              <span>{f.factor}</span>
                            </div>
                          ))}
                        </div>
                      </div>
                    </details>
                  </div>
                )}

                {/* Terminal - 详细报告 */}
                <div className="flex-1 bg-black p-3 font-mono text-xs leading-relaxed text-gray-400 overflow-y-auto min-h-0 relative group custom-scrollbar" onClick={toggleExpanded}>
                <div className="absolute top-2 right-2 opacity-20 group-hover:opacity-50 transition-opacity cursor-pointer">
                    <Maximize2 size={12} />
                </div>
                <pre className="whitespace-pre-wrap typing-cursor cursor-pointer">{reportText}</pre>
                </div>
            </>
        ) : patient?.clinical ? (
            <div className="flex-1 overflow-y-auto p-4 space-y-4 animate-in fade-in duration-300 custom-scrollbar">
                 {/* Demographics */}
                 <div className="bg-linear-to-br from-neutral-900/50 to-neutral-800/30 p-3 rounded-lg border border-white/5 hover:border-blue-500/30 transition-colors">
                    <div className="text-[10px] text-gray-500 uppercase tracking-wider mb-1 flex items-center gap-1"><User size={10}/> {t.diagnosis.demographics}</div>
                    <div className="text-sm text-gray-200 font-mono">
                        {patient.clinical.sex}, {patient.clinical.age}y
                    </div>
                    {patient.clinical.location && (
                        <div className="text-[10px] text-gray-500 mt-1">{patient.clinical.location}</div>
                    )}
                 </div>

                 {/* Tumor Size */}
                 <div className="bg-linear-to-br from-neutral-900/50 to-neutral-800/30 p-3 rounded-lg border border-white/5 hover:border-blue-500/30 transition-colors">
                    <div className="text-[10px] text-gray-500 uppercase tracking-wider mb-1 flex items-center gap-1"><Ruler size={10}/> {t.diagnosis.tumor_size}</div>
                    <div className="text-sm text-gray-200 font-mono">
                        {patient.clinical.tumorSize.length ?? 'N/A'} × {patient.clinical.tumorSize.thickness ?? 'N/A'} cm
                    </div>
                 </div>

                 {/* Biomarkers */}
                 <div className="bg-linear-to-br from-neutral-900/50 to-neutral-800/30 p-3 rounded-lg border border-white/5">
                    <div className="text-[10px] text-gray-500 uppercase tracking-wider mb-2 flex items-center gap-1"><Activity size={10}/> {t.diagnosis.biomarkers}</div>
                    <div className="space-y-2">
                        <div className="flex justify-between items-center text-xs p-2 rounded bg-neutral-800/30">
                            <span className="text-gray-400">CEA</span>
                            <div className="flex items-center gap-2">
                                <span className={`font-mono font-bold ${patient.clinical.biomarkers.cea_positive ? 'text-red-400' : 'text-emerald-400'}`}>
                                    {patient.clinical.biomarkers.cea ?? 'N/A'} ng/ml
                                </span>
                                {patient.clinical.biomarkers.cea_positive && (
                                    <span className="text-[8px] bg-red-500/20 text-red-400 px-1.5 py-0.5 rounded border border-red-500/30">+</span>
                                )}
                            </div>
                        </div>
                        <div className="flex justify-between items-center text-xs p-2 rounded bg-neutral-800/30">
                            <span className="text-gray-400">CA19-9</span>
                            <div className="flex items-center gap-2">
                                <span className={`font-mono font-bold ${patient.clinical.biomarkers.ca199_positive ? 'text-red-400' : 'text-emerald-400'}`}>
                                    {patient.clinical.biomarkers.ca199 ?? 'N/A'} U/ml
                                </span>
                                {patient.clinical.biomarkers.ca199_positive && (
                                    <span className="text-[8px] bg-red-500/20 text-red-400 px-1.5 py-0.5 rounded border border-red-500/30">+</span>
                                )}
                            </div>
                        </div>
                    </div>
                 </div>

                 {/* Pathology */}
                 <div className="bg-linear-to-br from-neutral-900/50 to-neutral-800/30 p-3 rounded-lg border border-white/5">
                    <div className="text-[10px] text-gray-500 uppercase tracking-wider mb-2 flex items-center gap-1"><AlignLeft size={10}/> {t.diagnosis.pathology}</div>
                    <div className="space-y-1.5 text-xs text-gray-300">
                        <div className="flex gap-2 items-center">
                            <span className="text-gray-500 w-14 text-right">{language === 'zh' ? '类型:' : 'Type:'}</span> 
                            <span className="flex-1 font-mono">{patient.clinical.pathology.type || 'N/A'}</span>
                        </div>
                        <div className="flex gap-2 items-center">
                            <span className="text-gray-500 w-14 text-right">{language === 'zh' ? '分化:' : 'Diff:'}</span> 
                            <span className="flex-1">{patient.clinical.pathology.differentiation}</span>
                        </div>
                        <div className="flex gap-2 items-center">
                            <span className="text-gray-500 w-14 text-right">Lauren:</span> 
                            <span className="flex-1">{patient.clinical.pathology.lauren || 'N/A'}</span>
                        </div>
                    </div>
                 </div>
                 
                 {/* Ground Truth */}
                 <div className="bg-linear-to-br from-blue-900/20 to-blue-800/10 p-3 rounded-lg border border-blue-500/30">
                    <div className="text-[10px] text-gray-400 uppercase tracking-wider mb-2 flex items-center gap-1"><Tag size={10} className="text-blue-400"/> {t.diagnosis.ground_truth}</div>
                    <div className="flex justify-between items-center font-mono text-sm font-bold">
                       <div className="flex flex-col items-center">
                           <div className="text-[9px] text-gray-500 mb-0.5">T-{language === 'zh' ? '分期' : 'Stage'}</div>
                           <div className="text-blue-400">pT{patient.clinical.pathology.pT || 'N/A'}</div>
                       </div>
                       <div className="flex flex-col items-center">
                           <div className="text-[9px] text-gray-500 mb-0.5">N-{language === 'zh' ? '分期' : 'Stage'}</div>
                           <div className="text-blue-400">pN{patient.clinical.pathology.pN || 'N/A'}</div>
                       </div>
                       <div className="flex flex-col items-center">
                           <div className="text-[9px] text-gray-500 mb-0.5">M-{language === 'zh' ? '分期' : 'Stage'}</div>
                           <div className="text-blue-400">pM{patient.clinical.pathology.pM || 'N/A'}</div>
                       </div>
                       <div className="flex flex-col items-center">
                           <div className="text-[9px] text-gray-500 mb-0.5">{language === 'zh' ? '分期' : 'Stage'}</div>
                           <div className="text-white bg-blue-600/30 px-2 py-1 rounded border border-blue-500/50">{language === 'zh' ? '第' : 'Stage'} {patient.clinical.pathology.pStage || 'N/A'}{language === 'zh' ? '期' : ''}</div>
                       </div>
                    </div>
                 </div>
            </div>
        ) : (
                <div className="flex-1 flex flex-col items-center justify-center p-8 text-center">
                    <div className="text-sm font-bold text-gray-400 mb-2 uppercase tracking-wider">{t.diagnosis.no_clinical}</div>
                </div>
        )}
      </div>
    </div>
  );
});

DiagnosisPanel.displayName = 'DiagnosisPanel';
