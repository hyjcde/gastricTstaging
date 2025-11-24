# MM-GCS: Multimodal Gastric Cancer Staging System

Research-grade workstation for gastric cancer T-staging using Multimodal Ultrasound and Concept Bottleneck Models.

## Features

- **Dark Mode Workstation UI**: Optimized for radiology reading rooms.
- **Real-time Data Integration**: Reads directly from `../Gastric_Cancer_Dataset`.
- **Concept Reasoning**: Interactive sliders to perform counterfactual analysis on pathological features (Serosa, Stiffness, etc.).
- **VLM Reporting**: Simulated multimodal AI report generation.
- **Multimodal Viewer**: Support for switching between Original B-Mode, Segmentation Overlay, and XAI Heatmap.

## Tech Stack

- **Framework**: Next.js 15 (App Router)
- **Styling**: Tailwind CSS v4
- **Icons**: Lucide React
- **Backend**: Next.js API Routes (Node.js fs module)

## Setup & Run

1. Install dependencies:
   ```bash
   npm install
   ```

2. Run development server:
   ```bash
   npm run dev
   ```

3. Open [http://localhost:3000](http://localhost:3000)

## Directory Structure

- `/app/api`: Backend API routes to read the dataset.
- `/components`: UI Components (PatientList, Viewer, Reasoning, etc.).
- `/lib`: Configuration and helpers.
