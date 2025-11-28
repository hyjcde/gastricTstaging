# MM-GCS: Multimodal Gastric Cancer Staging System

**多模态胃癌分期系统** | Research-grade workstation for gastric cancer T/N-staging using Multimodal Ultrasound and Concept Bottleneck Models.

## 📋 项目简介 / Overview

本项目是一个基于深度学习的胃癌术前超声诊断辅助系统，采用**跨域视觉-语言预训练**与**多模态融合**技术，实现对胃癌浸润深度（T分期）与淋巴结转移（N分期）的精准预测。系统集成了概念瓶颈模型（Concept Bottleneck Models, CBM），支持交互式概念推理和可解释性分析，为临床医生提供科研级的工作站界面。

This project is a deep learning-based workstation for preoperative gastric cancer staging using ultrasound imaging. It employs **cross-domain vision-language pre-training** and **multimodal fusion** techniques to accurately predict T-stage (tumor invasion depth) and N-stage (lymph node metastasis). The system integrates Concept Bottleneck Models (CBM) with interactive concept reasoning and explainability analysis, providing a research-grade interface for clinicians.

## ✨ 核心功能 / Key Features

### 🎨 用户界面 / User Interface
- **深色模式工作站界面** (Dark Mode Workstation UI): 专为放射科阅片室优化的界面设计，减少长时间使用的视觉疲劳
- **响应式布局** (Responsive Layout): 适配不同屏幕尺寸，支持多显示器工作流
- **国际化支持** (i18n Support): 中英文双语界面，便于国际学术交流

### 📊 数据集成 / Data Integration
- **实时数据读取** (Real-time Data Integration): 直接从 `../Gastric_Cancer_Dataset` 读取患者数据
- **多队列支持** (Multi-cohort Support): 支持 2019、2024 年回顾性队列及 2025 年前瞻性验证队列
- **临床数据融合** (Clinical Data Fusion): 整合年龄、性别、肿瘤标志物（CEA、CA19-9）等多模态信息

### 🔬 概念推理 / Concept Reasoning
- **交互式概念滑块** (Interactive Concept Sliders): 对病理特征（浆膜、硬度、边界等）进行反事实分析
- **实时诊断更新** (Real-time Diagnosis Update): 调整概念值后即时更新 T/N 分期预测
- **阈值可视化** (Threshold Visualization): 通过颜色编码（绿/黄/红）直观显示概念风险等级

### 📈 可视化分析 / Visualization
- **多模态图像查看器** (Multimodal Viewer): 
  - 原始 B 模式图像 (Original B-Mode)
  - 分割叠加图 (Segmentation Overlay)
  - XAI 热力图 (Explainability Heatmap)
- **雷达图分析** (Radar Chart): 多维度概念特征的可视化对比
- **统计面板** (Statistics Panel): 队列级别的统计信息展示

### 📄 报告生成 / Reporting
- **AI 报告生成** (VLM Reporting): 模拟多模态 AI 报告生成
- **PDF 导出** (PDF Export): 支持一键导出诊断报告，包含图像、预测结果和可解释性分析
- **报告管理** (Report Management): 历史报告查看和管理功能

### 🎯 可解释性 / Explainability
- **Grad-CAM++ 热力图** (Grad-CAM++ Heatmaps): 可视化模型关注的图像区域
- **SHAP 值分析** (SHAP Analysis): 量化临床特征对预测结果的贡献度
- **概念-诊断关联** (Concept-Diagnosis Correlation): 展示概念值与最终诊断的关联性

## 🛠️ 技术栈 / Tech Stack

### 前端框架 / Frontend
- **Next.js 16** (App Router): React 框架，支持服务端渲染和 API 路由
- **React 19**: 最新版本的 React 库
- **TypeScript**: 类型安全的 JavaScript 超集

### 样式与 UI / Styling & UI
- **Tailwind CSS v4**: 实用优先的 CSS 框架
- **Lucide React**: 现代图标库
- **Recharts**: 数据可视化图表库

### 功能库 / Utilities
- **react-window**: 虚拟滚动，优化大量数据渲染性能
- **html2canvas & jspdf**: PDF 报告生成
- **react-hot-toast**: 用户通知提示

### 后端 / Backend
- **Next.js API Routes**: 基于 Node.js 的文件系统 API
- **文件系统读取**: 直接读取本地数据集目录

## 🚀 快速开始 / Quick Start

### 环境要求 / Prerequisites
- Node.js >= 18.0.0
- npm >= 9.0.0 或 yarn >= 1.22.0

### 安装依赖 / Install Dependencies

```bash
cd gastric-scan-next
npm install
```

### 运行开发服务器 / Run Development Server

```bash
npm run dev
```

访问 [http://localhost:3000](http://localhost:3000) 查看应用。

### 构建生产版本 / Build for Production

```bash
npm run build
npm start
```

### 代码检查 / Linting

```bash
npm run lint
```

## 📁 项目结构 / Project Structure

```
gastric-scan-next/
├── app/                          # Next.js App Router 目录
│   ├── api/                      # API 路由
│   │   ├── images/[...path]/    # 图像文件服务
│   │   └── patients/             # 患者数据 API
│   ├── profile/                  # 患者详情页
│   ├── reports/                  # 报告管理页面
│   │   ├── [reportId]/           # 单个报告详情
│   │   └── report-data.ts       # 报告数据定义
│   ├── layout.tsx                # 根布局
│   ├── page.tsx                  # 主页
│   └── providers.tsx             # React Context Providers
│
├── components/                   # React 组件
│   ├── ConceptReasoning.tsx     # 概念推理面板
│   ├── DiagnosisPanel.tsx        # 诊断结果面板
│   ├── PatientList.tsx          # 患者列表（支持虚拟滚动）
│   ├── UltrasoundViewer.tsx     # 超声图像查看器
│   ├── RadarChart.tsx           # 雷达图组件
│   ├── StatisticsPanel.tsx      # 统计面板
│   └── ...
│
├── contexts/                     # React Context
│   └── SettingsContext.tsx      # 设置上下文（主题、语言等）
│
├── lib/                          # 工具库
│   ├── config.ts                # 应用配置
│   ├── diagnosis.ts             # 诊断计算逻辑
│   ├── export-utils.ts          # PDF 导出工具
│   ├── image-utils.ts           # 图像处理工具
│   ├── medical-config.ts        # 医学概念配置
│   └── patient-utils.ts         # 患者数据处理
│
├── data/                         # 静态数据文件
│   ├── clinical_data.json       # 临床数据
│   ├── clinical_data_2019.json  # 2019 年队列数据
│   └── ...
│
├── public/                       # 静态资源
│   └── demo-scan.jpg            # 示例图像
│
└── types.ts                      # TypeScript 类型定义
```

## 📖 使用指南 / User Guide

### 基本工作流 / Basic Workflow

1. **选择患者** (Select Patient): 在左侧患者列表中选择要分析的患者
2. **查看图像** (View Images): 在图像查看器中切换不同的视图模式
3. **调整概念** (Adjust Concepts): 使用概念滑块进行交互式推理
4. **查看诊断** (View Diagnosis): 在诊断面板中查看 T/N 分期预测结果
5. **导出报告** (Export Report): 生成并导出 PDF 诊断报告

### 概念推理 / Concept Reasoning

系统支持以下病理概念的可视化调整：
- **Ki-67 指数** (Ki-67 Index): 细胞增殖标志物
- **CPS 评分** (CPS Score): 联合阳性评分
- **浆膜侵犯** (Serosa Invasion): T4 分期关键指标
- **硬度** (Stiffness): 组织弹性特征
- **边界清晰度** (Boundary Clarity): 肿瘤边界特征
- **回声特征** (Echo Pattern): 超声回声模式

每个概念都有三个风险等级（低/中/高），通过颜色编码直观显示。

## 🔧 开发指南 / Development Guide

### 代码规范 / Code Style
- 使用 TypeScript 严格模式
- 遵循 ESLint 配置规则
- 组件使用函数式组件和 Hooks

### 性能优化 / Performance
- 使用 `next/image` 组件优化图片加载
- 实现虚拟滚动处理大量数据
- 使用 React.memo 和 useMemo 优化渲染

### 添加新功能 / Adding Features
1. 在 `lib/medical-config.ts` 中添加新的概念配置
2. 在 `types.ts` 中更新类型定义
3. 在相关组件中实现 UI 逻辑

## 📚 相关文档 / Related Documentation

- [前端改进方案](./FRONTEND_IMPROVEMENTS.md): 详细的前端优化建议和实施计划
- [实现总结](./IMPLEMENTATION_SUMMARY.md): 系统实现的技术细节
- [优化总结](./OPTIMIZATION_SUMMARY.md): 性能优化实践
- [测试总结](./TESTING_SUMMARY.md): 测试策略和结果
- [研究思路](../docs/思路.md): 完整的研究方法论和实验设计

## 🎓 研究背景 / Research Context

本项目是**基于跨域视觉-语言预训练与多模态融合的胃癌超声术前T/N分期深度学习框架**的前端实现。系统采用：

1. **跨域预训练**: 利用 GIST 数据构建视觉-语言预训练模型
2. **多模态融合**: 结合超声图像和临床特征进行诊断
3. **概念瓶颈模型**: 提供可解释的中间概念层
4. **前瞻性验证**: 在独立队列上验证模型性能

详细的研究方法请参考 [研究思路文档](../docs/思路.md)。

## 📝 许可证 / License

本项目为研究用途，请遵循相关学术规范使用。

## 👥 贡献 / Contributing

欢迎提交 Issue 和 Pull Request 来改进本项目。

---

**注意**: 本系统为科研用途，不应用于临床诊断决策。所有诊断结果仅供参考，最终诊断需由专业医生确认。
