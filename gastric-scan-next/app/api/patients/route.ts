import { NextRequest, NextResponse } from 'next/server';
import fs from 'fs';
import path from 'path';
import { getDatasetPaths, DatasetType, CohortYear, TreatmentType, getClinicalDataPath } from '@/lib/config';

export async function GET(request: NextRequest) {
  try {
    const { searchParams } = new URL(request.url);
    const datasetParam = searchParams.get('dataset');
    const cohortYearParam = searchParams.get('cohort') || '2025';
    const treatmentTypeParam = searchParams.get('treatment') || 'surgery';
    const dataset: DatasetType = (datasetParam === 'cropped') ? 'cropped' : 'original';
    const cohortYear: CohortYear = (cohortYearParam === '2019') ? '2019' : (cohortYearParam === '2024') ? '2024' : '2025';
    const treatmentType: TreatmentType = (treatmentTypeParam === 'nac') ? 'nac' : 'surgery';

    const paths = getDatasetPaths(dataset, cohortYear, treatmentType);

    if (!fs.existsSync(paths.images)) {
      return NextResponse.json({ error: 'Dataset directory not found' }, { status: 404 });
    }

    // Load Clinical Data based on cohort year and treatment type
    let clinicalData: Record<string, any> = {};
    try {
        const clinicalDataPath = getClinicalDataPath(cohortYear, treatmentType);
        if (fs.existsSync(clinicalDataPath)) {
            const fileContent = fs.readFileSync(clinicalDataPath, 'utf-8');
            clinicalData = JSON.parse(fileContent);
        }
    } catch (e) {
        console.warn("Failed to load clinical data", e);
    }

    const files = fs.readdirSync(paths.images);
    const jpgFiles = files.filter(file => file.toLowerCase().endsWith('.jpg'));

    // Filter files based on treatment type for 2025
    let filteredFiles = jpgFiles;
    if (cohortYear === '2025') {
      if (treatmentType === 'nac') {
        // Only include Chemo files for NAC
        filteredFiles = jpgFiles.filter(f => f.startsWith('Chemo_'));
      } else {
        // Only include Surgery files for surgery
        filteredFiles = jpgFiles.filter(f => f.startsWith('Surgery_'));
      }
    } else {
      // For 2019 and 2024, filter based on filename prefix
      if (treatmentType === 'nac') {
        filteredFiles = jpgFiles.filter(f => f.startsWith('NAC_'));
      } else {
        filteredFiles = jpgFiles.filter(f => f.startsWith('Surgery_'));
      }
    }

    // Get lists of available overlay files to validate URLs
    let availableOverlays = new Set<string>();
    let availableTransparentOverlays = new Set<string>();
    let availableAnnotations = new Set<string>();

    try {
        if (fs.existsSync(paths.overlays)) {
            const files = fs.readdirSync(paths.overlays);
            files.forEach(f => availableOverlays.add(f));
        }
    } catch (e) { console.warn("Failed to list overlays directory", e); }

    try {
        if (fs.existsSync(paths.overlaysTransparent)) {
            const files = fs.readdirSync(paths.overlaysTransparent);
            files.forEach(f => availableTransparentOverlays.add(f));
        }
    } catch (e) { console.warn("Failed to list transparent overlays directory", e); }
    
    try {
        if (fs.existsSync(paths.annotations)) {
            const files = fs.readdirSync(paths.annotations);
            files.forEach(f => availableAnnotations.add(f));
        }
    } catch (e) { console.warn("Failed to list annotations directory", e); }

    const patients = filteredFiles.map(filename => {
      // Filename format for 2025: Group_Phase_PatientID.jpg or Group_Phase_PatientID (X).jpg
      // Filename format for 2019: Surgery_2019_1-1-2(13).jpg
      const nameParts = filename.split('_');
      let group = nameParts[0] || "Unknown";
      let phase = nameParts.length > 1 ? nameParts[1] : "Unknown";
      let pureId = "";
      
      if (cohortYear === '2019' || cohortYear === '2024') {
          // 2019/2024年格式: Surgery_2019_1-800-6.jpg 或 NAC_2019_1-437-1.jpg 或 Surgery_2024_1-1375062-3.jpg
          // 判断是直接手术还是新辅助治疗
          if (nameParts[0] === 'NAC') {
              group = "NAC";
          } else {
              group = "Surgery";
          }
          phase = cohortYear;
          
          // 提取ID部分: "1-800-6.jpg" 或 "1-437-1.jpg"
          let idPart = nameParts.length > 2 ? nameParts.slice(2).join('_') : nameParts[nameParts.length-1];
          idPart = idPart.replace(/\.jpg$/i, ''); // 移除扩展名
          idPart = idPart.replace(/\([^)]*\)/g, ''); // 移除括号内容，如 "(15)"
          
          // 提取病人ID
          const parts = idPart.split('-');
          if (parts.length >= 3) {
              // 新格式: "1-800-6" -> 取中间 "800" (病人ID)
              pureId = parts[1];
          } else if (parts.length === 2) {
              // 旧格式: "127-3" -> 取第一个 "127" (可能是病人ID，也可能是队列-序列)
              // 这里需要根据实际情况判断，暂时取第一个
              pureId = parts[0];
          } else {
              // 单个数字
              pureId = parts[0];
          }
      } else {
          // 2025年格式: Group_Phase_PatientID.jpg
          // Group可能是 "Chemo" (NAC) 或 "Surgery" (直接手术)
          // 判断是直接手术还是新辅助治疗
          if (nameParts[0] === 'Chemo') {
              group = "NAC";
          } else if (nameParts[0] === 'Surgery') {
              group = "Surgery";
          }
          
          // Extract Patient ID
          // Last part: "1452405.jpg" or "1452405 (3).jpg"
          let lastPart = nameParts.length > 2 ? nameParts.slice(2).join('_') : nameParts[nameParts.length-1];
          // Remove extension
          lastPart = lastPart.replace(/\.jpg$/i, ''); // "1452405" or "1452405 (3)"
          
          // Clean up brackets for ID matching: "1452405 (3)" -> "1452405"
          const patientIdMatch = lastPart.match(/^(\d+)/);
          pureId = patientIdMatch ? patientIdMatch[1] : lastPart;
      }
      
      // Encode filename for URL (handle special characters like parentheses)
      const encodedFilename = encodeURIComponent(filename);
      
      // Determine overlay filenames
      // Try exact case replacement first
      let overlayFilename = filename.replace(".jpg", "_overlay.jpg");
      // If not found, try case-insensitive replacement if needed, or just stick to standard naming convention
      
      const encodedOverlayFilename = encodeURIComponent(overlayFilename);
      const jsonFilename = filename.replace(".jpg", ".json");
      const encodedJsonFilename = encodeURIComponent(jsonFilename);
      
      // Check file existence
      const hasOverlay = availableOverlays.has(overlayFilename);
      const hasTransparentOverlay = availableTransparentOverlays.has(overlayFilename);
      const hasAnnotation = availableAnnotations.has(jsonFilename);

      return {
        id: filename,
        id_short: filename.replace(".jpg", ""), 
        patient_id: pureId,
        group,
        phase,
        // New URL format: /api/images/[dataset]/[type]/[filename]?cohort=[year]&treatment=[type]
        image_url: `/api/images/${dataset}/images/${encodedFilename}?cohort=${cohortYear}&treatment=${treatmentType}`,
        overlay_url: hasOverlay ? `/api/images/${dataset}/overlays/${encodedOverlayFilename}?cohort=${cohortYear}&treatment=${treatmentType}` : "",
        overlay_transparent_url: hasTransparentOverlay ? `/api/images/${dataset}/lymph_node_analysis/${encodedOverlayFilename}?cohort=${cohortYear}&treatment=${treatmentType}` : "",
        json_url: hasAnnotation ? `/api/images/${dataset}/annotations/${encodedJsonFilename}?cohort=${cohortYear}&treatment=${treatmentType}` : "",
        clinical: clinicalData[pureId] || null
      };
    });

    // Sort patients: Priority to those with clinical data, then by ID
    patients.sort((a, b) => {
      // 1. Clinical data presence
      const hasClinicalA = !!a.clinical;
      const hasClinicalB = !!b.clinical;
      
      if (hasClinicalA && !hasClinicalB) return -1;
      if (!hasClinicalA && hasClinicalB) return 1;
      
      // 2. Sort by ID
      return a.id.localeCompare(b.id, undefined, { numeric: true, sensitivity: 'base' });
    });

    return NextResponse.json(patients);
  } catch (error) {
    console.error("Error reading patients:", error);
    return NextResponse.json({ error: 'Internal Server Error' }, { status: 500 });
  }
}
