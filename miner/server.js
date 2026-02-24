import express from 'express';
import cors from 'cors';
import fs from 'fs';
import path from 'path';
import dotenv from 'dotenv';
import xlsx from 'xlsx';
import { DOMParser } from '@xmldom/xmldom';
import tj from '@mapbox/togeojson';

dotenv.config();

const app = express();
const port = process.env.PORT ? Number(process.env.PORT) : 8000;

// Enable CORS and JSON parsing
app.use(cors());
app.use(express.json());

// In-memory data storage
let minesData = []; // Array of GeoJSON features
let ndviData = {};  // Object mapping FID -> Array of {year, value}
let ndbiData = {};
let ndwiData = {};
let ndsiData = {};

// --- Helper functions for Excel parsing ---
function detectColumns(headerRow, valueRegex) {
  const header = headerRow.map(h => String(h || '').trim());
  const fidCol = header.find(h => /^(fid|fid_1)$/i.test(h));
  const yearCol = header.find(h => /^year$/i.test(h));
  const valCol = header.find(h => valueRegex.test(h));
  const yearHeaders = header.filter(h => /(19|20)\d{2}/.test(h));
  return { fidCol, yearCol, valCol, yearHeaders, header };
}

function rowsFromSheet(sheet, valueRegex) {
  const aoa = xlsx.utils.sheet_to_json(sheet, { header: 1, defval: null });
  if (!aoa.length) return [];
  const headerRow = aoa[0];
  const { fidCol, yearCol, valCol, yearHeaders, header } = detectColumns(headerRow, valueRegex);
  const dataRows = aoa.slice(1);

  const rows = [];
  if (fidCol && yearCol && valCol) {
    // tidy format
    const idxFID = header.indexOf(fidCol);
    const idxYear = header.indexOf(yearCol);
    const idxVal = header.indexOf(valCol);
    for (const r of dataRows) {
      const fid = Number(r[idxFID]);
      const year = Number(r[idxYear]);
      const val = r[idxVal] != null ? Number(r[idxVal]) : null;
      if (!Number.isFinite(fid) || !Number.isFinite(year) || !Number.isFinite(val)) continue;
      rows.push({ fid, year, value: val });
    }
  } else if (fidCol && yearHeaders.length) {
    // wide format
    const idxFID = header.indexOf(fidCol);
    const yearIdxMap = yearHeaders.reduce((acc, y) => { acc[y] = header.indexOf(y); return acc; }, {});
    for (const r of dataRows) {
      const fid = Number(r[idxFID]);
      if (!Number.isFinite(fid)) continue;
      for (const yStr of yearHeaders) {
        // Extract year from header like "2023" or "NDVI_2023"
        const yMatch = yStr.match(/(19|20)\d{2}/);
        const year = yMatch ? Number(yMatch[0]) : null;
        if (!year) continue;
        const val = r[yearIdxMap[yStr]] != null ? Number(r[yearIdxMap[yStr]]) : null;
        if (Number.isFinite(val)) {
          rows.push({ fid, year, value: val });
        }
      }
    }
  }
  return rows;
}

async function loadIndexData(filePath, valueRegex) {
  const fullPath = path.resolve(process.cwd(), filePath);
  const dataMap = {};
  if (fs.existsSync(fullPath)) {
    try {
      const workbook = xlsx.readFile(fullPath);
      const sheetName = workbook.SheetNames[0];
      const sheet = workbook.Sheets[sheetName];
      const rows = rowsFromSheet(sheet, valueRegex);
      
      // Group by FID
      for (const r of rows) {
        if (!dataMap[r.fid]) dataMap[r.fid] = [];
        dataMap[r.fid].push({ year: r.year, value: r.value });
      }
      
      // Sort by year for each FID
      for (const fid in dataMap) {
        dataMap[fid].sort((a, b) => a.year - b.year);
      }
      console.log(`Loaded data from ${path.basename(filePath)} for ${Object.keys(dataMap).length} mines.`);
    } catch (e) {
      console.error(`Failed to load ${filePath}:`, e);
    }
  } else {
    console.warn(`File not found: ${filePath}`);
  }
  return dataMap;
}

// --- Initialization function ---
async function initData() {
  // 1. Load KML and convert to GeoJSON
  const kmlPath = path.resolve(process.cwd(), 'yunnan.kml');
  if (fs.existsSync(kmlPath)) {
    try {
      const kmlContent = fs.readFileSync(kmlPath, 'utf-8');
      const kmlDom = new DOMParser().parseFromString(kmlContent);
      const converted = tj.kml(kmlDom);
      
      if (converted && converted.features && Array.isArray(converted.features)) {
        minesData = converted.features;
        // Post-processing to ensure numeric fields are numbers and normalize status
        minesData.forEach(f => {
            if (f.properties) {
                // Ensure FID_1 is number if possible
                if (f.properties.FID_1) f.properties.FID_1 = Number(f.properties.FID_1);
                
                // Ensure Area is number
                const area = f.properties.TBTYMJ || f.properties.TBTYMJ_1 || f.properties.SHAPE_Area;
                if (area) f.properties.area = Number(area);
                
                // Normalize Status
                const status = String(f.properties.HFZLQK || '').trim();
                if (status.includes('未治理')) f.properties.status_normalized = 'untreated';
                else if (status.includes('已') || status.includes('治理') || status.includes('复垦')) f.properties.status_normalized = 'treated';
                else f.properties.status_normalized = 'unknown';
            }
        });
        console.log(`Loaded ${minesData.length} mines from yunnan.kml.`);
        if (minesData.length > 0) console.log('Sample properties:', minesData[0].properties);
      }
    } catch (e) {
      console.error('Failed to parse KML:', e);
    }
  } else {
    console.warn('yunnan.kml not found.');
  }

  // 2. Load Indices Data
  ndviData = await loadIndexData('NDVI_2year.xlsx', /^(ndvi|ndvi_value)$/i);
  ndbiData = await loadIndexData('NDBI_by_fid_2year_avg.xlsx', /^(ndbi|ndbi_value|mean_ndbi|mean)$/i);
  ndwiData = await loadIndexData('NDWI_by_fid_2year_avg.xlsx', /^(ndwi|ndwi_value|mean_ndwi|mean)$/i);
  ndsiData = await loadIndexData('NDSI_by_fid_2year_avg.xlsx', /^(ndsi|ndsi_value|mean_ndsi|mean)$/i);
}

// Initialize data synchronously or await it
initData();

// --- API Endpoints ---

// Get Global Statistics
app.get('/api/stats', (req, res) => {
  // 1. Mine Area Statistics & Global Aggregations
    let totalArea = 0;
    let treatedCount = 0;
    let untreatedCount = 0;
    let smallMines = 0;  // < 1 km^2
    let mediumMines = 0; // 1-2 km^2
    let largeMines = 0;  // > 2 km^2
    
    // Aggregations for User Requested Data
    const miningMethodStats = {}; // KCFS
    const closingYearStats = {}; // GBND
    const restorationStatusStats = {}; // HFZLQK (Simplified)
    const restorationMethodStats = {}; // NXFFS
    const damageTypeStats = {}; // STWT
    const landTypeStats = {}; // NXFFX

    // Helper for area calculation (Shoelace formula for planar projection approximation)
    const calculateArea = (coords) => {
      if (!coords || coords.length < 1) return 0;
      let area = 0;
      const ring = coords[0]; // Outer ring
      if (ring.length < 3) return 0;

      // Approximate conversion to meters
      // Center lat for scale
      const centerLat = ring[0][1] * Math.PI / 180;
      const mPerDegLat = 111319.9;
      const mPerDegLon = 111319.9 * Math.cos(centerLat);

      for (let i = 0; i < ring.length - 1; i++) {
        const [x1, y1] = ring[i];
        const [x2, y2] = ring[i + 1];
        area += (x1 * mPerDegLon * y2 * mPerDegLat) - (y1 * mPerDegLat * x2 * mPerDegLon);
      }
      return Math.abs(area / 2);
    };

    minesData.forEach(f => {
      const p = f.properties || {};
      
      // --- Area & Size ---
      let area = Number(p.TBTYMJ || p.TBTYMJ_1 || 0);
      if ((!area || area <= 0) && f.geometry) {
         if (f.geometry.type === 'Polygon') {
            area = calculateArea(f.geometry.coordinates);
         } else if (f.geometry.type === 'MultiPolygon') {
            f.geometry.coordinates.forEach(poly => { area += calculateArea(poly); });
         }
      }
      totalArea += area;

      // Categorize by size (1 km2 = 1,000,000 m2)
      if (area < 1000000) {
        smallMines++;
      } else if (area >= 1000000 && area <= 2000000) {
        mediumMines++;
      } else {
        largeMines++;
      }

      // --- Mining Method (KCFS) ---
      const method = String(p.KCFS || '未知').trim();
      miningMethodStats[method] = (miningMethodStats[method] || 0) + 1;

      // --- Closing Year (GBND) ---
      let year = String(p.GBND || '未知').trim();
      // Try to extract YYYY
      const yearMatch = year.match(/20\d{2}/);
      if (yearMatch) year = yearMatch[0] + '年';
      closingYearStats[year] = (closingYearStats[year] || 0) + 1;

      // --- Restoration Status (HFZLQK) ---
      const statusRaw = String(p.HFZLQK || '').trim();
      let statusSimple = '未知';
      if (statusRaw.includes('未治理')) {
        statusSimple = '未治理';
        untreatedCount++;
      } else if (statusRaw.includes('已') || statusRaw.includes('治理') || statusRaw.includes('复垦')) {
        statusSimple = '已恢复治理';
        treatedCount++;
      } else {
        // Fallback
        statusSimple = statusRaw || '未知';
        if (statusSimple !== '未知') untreatedCount++; 
      }
      
      restorationStatusStats[statusSimple] = (restorationStatusStats[statusSimple] || 0) + 1;

      // --- Restoration Method (NXFFS) ---
      const restMethod = String(p.NXFFS || '未知').trim();
      restorationMethodStats[restMethod] = (restorationMethodStats[restMethod] || 0) + 1;

      // --- Damage Type (STWT) ---
      const damageType = String(p.STWT || '未知').trim();
      damageTypeStats[damageType] = (damageTypeStats[damageType] || 0) + 1;

      // --- Land Type After (NXFFX) ---
      const landType = String(p.NXFFX || '未知').trim();
      landTypeStats[landType] = (landTypeStats[landType] || 0) + 1;
    });

    // Format Data for Frontend
    // 1. Mining Method (Top 5)
    const miningMethodList = Object.entries(miningMethodStats)
      .sort((a, b) => b[1] - a[1])
      .map(([name, value]) => ({ name, value }));

    // 2. Restoration Method (Top 5)
    const restorationMethodList = Object.entries(restorationMethodStats)
      .sort((a, b) => b[1] - a[1])
      .map(([name, count]) => ({ name, count }));

    // 3. Land Type (Top 5)
    const landTypeList = Object.entries(landTypeStats)
      .sort((a, b) => b[1] - a[1])
      .slice(0, 6) // Top 6
      .map(([name, value]) => ({ name, value }));
      
    // 4. Closing Year (Top 5)
    const closingYearList = Object.entries(closingYearStats)
      .sort((a, b) => b[1] - a[1])
      .slice(0, 5)
      .map(([name, value]) => ({ name, value }));

    // 2. NDVI Statistics (Keep existing logic)
    let totalNdvi = 0;
    let totalTrend = 0;
    let ndviCount = 0;
    let trendCount = 0;

    Object.values(ndviData).forEach(records => {
      if (!records.length) return;
      const vals = records.map(r => r.value);
      const mean = vals.reduce((a, b) => a + b, 0) / vals.length;
      totalNdvi += mean;
      ndviCount++;
      if (records.length >= 2) {
          const years = records.map(r => r.year);
          const n = records.length;
          const sumX = years.reduce((a, b) => a + b, 0);
          const sumY = vals.reduce((a, b) => a + b, 0);
          const sumXY = years.reduce((acc, x, i) => acc + x * vals[i], 0);
          const sumXX = years.reduce((acc, x) => acc + x * x, 0);
          const denom = n * sumXX - sumX * sumX;
          const slope = denom !== 0 ? (n * sumXY - sumX * sumY) / denom : 0;
          totalTrend += slope;
          trendCount++;
      }
    });

    const avgNdvi = ndviCount > 0 ? (totalNdvi / ndviCount) : 0;
    const avgTrend = trendCount > 0 ? (totalTrend / trendCount) : 0;

    res.json({
      mineTotal: minesData.length,
      mineAreaTotal: totalArea,
      treatedCount,
      untreatedCount,
      areaStats: {
        small: smallMines,   // < 1km2
        medium: mediumMines, // 1-2km2
        large: largeMines    // > 2km2
      },
      // New Stats
      miningMethodList,
      restorationMethodList,
      landTypeList,
      closingYearList,
      // Keep NDVI for compatibility if needed, though we might replace UI
      ndviStats: {
        mean: Number(avgNdvi.toFixed(3)),
        trend: Number(avgTrend.toFixed(5))
      }
    });
  });

// Get all mines as GeoJSON
app.get('/api/geojson', (req, res) => {
  res.json({
    type: 'FeatureCollection',
    features: minesData
  });
});

// Search mines
app.get('/api/mines/search', (req, res) => {
  const q = req.query.q;
  if (!q) return res.status(400).json({ error: 'Missing query parameter q' });
  
  const qStr = String(q).toLowerCase();
  const fid = parseInt(q, 10);
  
  let found = null;
  
  // Try exact FID match first
  if (!isNaN(fid)) {
    found = minesData.find(f => f.properties && f.properties.FID_1 === fid);
  }
  
  // If not found, try name match
  if (!found) {
    found = minesData.find(f => {
      if (!f.properties) return false;
      const name = f.properties.mine_name || f.properties.name || '';
      return name.toLowerCase().includes(qStr);
    });
  }
  
  if (!found) return res.status(404).json({ error: 'Mine not found' });
  
  res.json(found);
});

// Helper to calculate stats
function calculateStats(data) {
  if (!data || data.length === 0) return { mean: 0, trend: 0, mk_trend: '无数据' };
  
  const values = data.map(d => d.value);
  const years = data.map(d => d.year);
  
  const mean = values.reduce((a, b) => a + b, 0) / values.length;
  
  const n = values.length;
  if (n < 2) return { mean: Number(mean.toFixed(3)), trend: 0, mk_trend: '无趋势 (数据不足)' };
  
  const sumX = years.reduce((a, b) => a + b, 0);
  const sumY = values.reduce((a, b) => a + b, 0);
  const sumXY = years.reduce((acc, x, i) => acc + x * values[i], 0);
  const sumXX = years.reduce((acc, x) => acc + x * x, 0);
  const denom = n * sumXX - sumX * sumX;
  const slope = denom !== 0 ? (n * sumXY - sumX * sumY) / denom : 0;
  
  const mkTrend = slope > 0.0005 ? '上升趋势' : (slope < -0.0005 ? '下降趋势' : '无趋势');
  
  return {
    mean: Number(mean.toFixed(3)),
    trend: Number(slope.toFixed(5)),
    mk_trend: mkTrend
  };
}

// Get Indices Data (NDVI, NDBI, NDWI)
app.get('/api/mines/indices', (req, res) => {
  const { fid } = req.query;
  if (!fid) return res.status(400).json({ error: 'Missing FID parameter' });
  
  const fidNum = Number(fid);
  
  const ndviRaw = ndviData[fidNum] || [];
  const ndbiRaw = ndbiData[fidNum] || [];
  const ndwiRaw = ndwiData[fidNum] || [];
  const ndsiRaw = ndsiData[fidNum] || [];
  
  const ndviStats = calculateStats(ndviRaw);
  const ndbiStats = calculateStats(ndbiRaw);
  const ndwiStats = calculateStats(ndwiRaw);
  const ndsiStats = calculateStats(ndsiRaw);
  
  res.json({
    fid: fidNum,
    ndvi: { data: ndviRaw, ...ndviStats },
    ndbi: { data: ndbiRaw, ...ndbiStats },
    ndwi: { data: ndwiRaw, ...ndwiStats },
    ndsi: { data: ndsiRaw, ...ndsiStats }
  });
});

// Get NDVI data and trend (Legacy/Specific)
app.get('/api/mines/ndvi', (req, res) => {
  const { fid } = req.query;
  if (!fid) return res.status(400).json({ error: 'Missing FID parameter' });
  
  const fidNum = Number(fid);
  const data = ndviData[fidNum];
  
  if (!data || data.length === 0) {
    return res.status(404).json({ error: 'No NDVI data for this FID' });
  }
  
  const stats = calculateStats(data);

  res.json({
    fid: fidNum,
    ndvi_data: data, // Keep naming for compatibility if needed, but data has .value now
    ndvi_mean: stats.mean,
    ndvi_trend: stats.trend,
    mk_trend: stats.mk_trend
  });
});

app.listen(port, () => {
  console.log(`Server running at http://localhost:${port}`);
  console.log('Mode: Local File System (No Database)');
});
