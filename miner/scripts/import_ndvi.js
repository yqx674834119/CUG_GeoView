import dotenv from 'dotenv';
import mysql from 'mysql2/promise';
import xlsx from 'xlsx';
import path from 'path';
import fs from 'fs';

dotenv.config();

const dbConfig = {
  host: process.env.DB_HOST || process.env.MYSQL_HOST || 'localhost',
  user: process.env.DB_USER || process.env.MYSQL_USER || 'root',
  password: process.env.DB_PASSWORD ?? process.env.MYSQL_PASSWORD ?? '',
  database: process.env.DB_NAME || process.env.MYSQL_DB || process.env.MYSQL_DATABASE || 'mine_db',
  port: process.env.DB_PORT ? Number(process.env.DB_PORT) : (process.env.MYSQL_PORT ? Number(process.env.MYSQL_PORT) : 3306),
};

function detectColumns(headerRow) {
  const header = headerRow.map(h => String(h || '').trim());
  const fidCol = header.find(h => /^(fid|fid_1)$/i.test(h));
  const yearCol = header.find(h => /^year$/i.test(h));
  const ndviCol = header.find(h => /^(ndvi|ndvi_value)$/i.test(h));
  // 允许如 "2023", "2023年", "NDVI_2023", "2023_NDVI"
  const yearHeaders = header.filter(h => /(19|20)\d{2}/.test(h));
  return { fidCol, yearCol, ndviCol, yearHeaders, header };
}

function rowsFromSheet(sheet) {
  const aoa = xlsx.utils.sheet_to_json(sheet, { header: 1, defval: null });
  if (!aoa.length) return [];
  const headerRow = aoa[0];
  const { fidCol, yearCol, ndviCol, yearHeaders, header } = detectColumns(headerRow);
  const dataRows = aoa.slice(1);

  const rows = [];
  if (fidCol && yearCol && ndviCol) {
    // tidy format: FID, year, ndvi_value
    const idxFID = header.indexOf(fidCol);
    const idxYear = header.indexOf(yearCol);
    const idxNDVI = header.indexOf(ndviCol);
    for (const r of dataRows) {
      const fid = Number(r[idxFID]);
      const year = Number(r[idxYear]);
      const val = r[idxNDVI] != null ? Number(r[idxNDVI]) : null;
      if (!Number.isFinite(fid) || !Number.isFinite(year) || !Number.isFinite(val)) continue;
      rows.push({ fid, year, ndvi_value: val });
    }
  } else if (fidCol && yearHeaders.length) {
    // wide format: one row per FID, columns for years
    const idxFID = header.indexOf(fidCol);
    const yearIdxMap = yearHeaders.reduce((acc, y) => { acc[y] = header.indexOf(y); return acc; }, {});
    for (const r of dataRows) {
      const fid = Number(r[idxFID]);
      if (!Number.isFinite(fid)) continue;
      for (const yHeader of yearHeaders) {
        const cell = r[yearIdxMap[yHeader]];
        const val = cell != null ? Number(cell) : null;
        if (!Number.isFinite(val)) continue;
        const yMatch = String(yHeader).match(/(19|20)\d{2}/);
        const y = yMatch ? Number(yMatch[0]) : null;
        if (!Number.isFinite(y)) continue;
        rows.push({ fid, year: y, ndvi_value: val });
      }
    }
  } else {
    console.error('Excel 表头:', headerRow);
    throw new Error('无法识别Excel列，请确保包含 FID/FID_1 以及 year+ndvi 或 各年份列');
  }
  return rows;
}

async function ensureSchema(conn) {
  await conn.query(`
    CREATE TABLE IF NOT EXISTS ndvi_data (
      fid INT NOT NULL,
      year INT NOT NULL,
      ndvi_value DECIMAL(6,3) NOT NULL,
      PRIMARY KEY (fid, year)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
  `);
}

async function importExcel(filePath) {
  const abs = path.resolve(process.cwd(), filePath);
  if (!fs.existsSync(abs)) throw new Error('Excel 文件不存在: ' + abs);
  const wb = xlsx.readFile(abs);
  const sheetName = wb.SheetNames[0];
  const sheet = wb.Sheets[sheetName];
  const rows = rowsFromSheet(sheet);
  console.log(`解析 ${sheetName} 得到 ${rows.length} 条 NDVI 记录`);

  const conn = await mysql.createConnection(dbConfig);
  try {
    await ensureSchema(conn);
    const sql = 'INSERT INTO ndvi_data (fid, year, ndvi_value) VALUES (?, ?, ?) ON DUPLICATE KEY UPDATE ndvi_value = VALUES(ndvi_value)';
    let count = 0;
    for (const r of rows) {
      await conn.execute(sql, [r.fid, r.year, r.ndvi_value]);
      count++;
      if (count % 500 === 0) console.log('已写入', count);
    }
    console.log('导入完成，共写入', count, '条');
  } finally {
    await conn.end();
  }
}

// 执行
const excel = process.argv[2] || 'NDVI_2year.xlsx';
importExcel(excel).catch(err => {
  console.error('导入失败:', err.message);
  process.exit(1);
});

