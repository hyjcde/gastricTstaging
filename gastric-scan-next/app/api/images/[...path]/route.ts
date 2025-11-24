import { NextRequest, NextResponse } from 'next/server';
import fs from 'fs';
import path from 'path';
import { getDatasetPaths, DatasetType, CohortYear, TreatmentType } from '@/lib/config';

export async function GET(
  request: NextRequest,
  { params }: { params: Promise<{ path: string[] }> }
) {
  const resolvedParams = await params;
  const pathSegments = resolvedParams.path;
  const { searchParams } = new URL(request.url);
  const cohortYearParam = searchParams.get('cohort') || '2025';
  const treatmentTypeParam = searchParams.get('treatment') || 'surgery';
  const cohortYear: CohortYear = (cohortYearParam === '2019') ? '2019' : (cohortYearParam === '2024') ? '2024' : '2025';
  const treatmentType: TreatmentType = (treatmentTypeParam === 'nac') ? 'nac' : 'surgery';
  
  // Expecting: [dataset, type, filename] e.g. /api/images/original/images/file.jpg
  // Or fallback: [type, filename] (default to original)
  
  let dataset: DatasetType = 'original';
  let type = '';
  let filename = '';

  if (pathSegments && pathSegments.length === 3) {
      // New format: /api/images/[dataset]/[type]/[filename]
      const ds = pathSegments[0];
      if (ds === 'original' || ds === 'cropped') {
          dataset = ds as DatasetType;
      }
      type = pathSegments[1];
      filename = pathSegments[2];
  } else if (pathSegments && pathSegments.length === 2) {
      // Old format fallback: /api/images/[type]/[filename]
      type = pathSegments[0];
      filename = pathSegments[1];
  } else {
    return NextResponse.json({ error: 'Invalid path' }, { status: 400 });
  }

  const paths = getDatasetPaths(dataset, cohortYear, treatmentType);
  let targetDir = '';

  switch (type) {
    case 'images':
      targetDir = paths.images;
      break;
    case 'overlays':
      targetDir = paths.overlays;
      break;
    case 'lymph_node_analysis':
      targetDir = paths.overlaysTransparent;
      break;
    case 'annotations':
      targetDir = paths.annotations;
      break;
    default:
      return NextResponse.json({ error: 'Invalid type' }, { status: 400 });
  }

  // Security check: prevent directory traversal
  // Decode URL-encoded filename (e.g., %2813%29 -> (13))
  const decodedFilename = decodeURIComponent(filename);
  const safeFilename = path.basename(decodedFilename);
  const filePath = path.join(targetDir, safeFilename);

  if (!fs.existsSync(filePath)) {
      return NextResponse.json({ error: `File not found: ${safeFilename}`, path: filePath }, { status: 404 });
  }

  const fileBuffer = fs.readFileSync(filePath);
  
  // Determine Content-Type
  let contentType = 'application/octet-stream';
  if (filename.toLowerCase().endsWith('.jpg') || filename.toLowerCase().endsWith('.jpeg')) {
    contentType = 'image/jpeg';
  } else if (filename.toLowerCase().endsWith('.png')) {
    contentType = 'image/png';
  } else if (filename.toLowerCase().endsWith('.json')) {
    contentType = 'application/json';
  }

  return new NextResponse(fileBuffer, {
    headers: {
      'Content-Type': contentType,
      'Cache-Control': 'public, max-age=31536000, immutable',
    },
  });
}
