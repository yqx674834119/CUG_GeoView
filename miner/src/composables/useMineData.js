import { ref, computed } from 'vue';
import axios from 'axios';

export function useMineData() {
  const allMinesData = ref([]);
  const filteredMinesData = ref([]);
  
  // Filters
  const filterCity = ref('');
  const filterStatus = ref('');
  const filterMethod = ref('');
  const searchMineId = ref('');

  // Options
  const cityOptions = ref([]);
  const miningMethodOptions = ref([]);

  // Stats
  const mineTotal = ref(0);
  const overviewArea = ref(0);
  const treatedCount = ref(0);
  const untreatedCount = ref(0);
  const restorationMethodList = ref([]);
  const miningMethodList = ref([]); // Add this
  const landTypeList = ref([]);

  // Indices Data
  const mineIndices = ref({
    ndvi: { mean: 0, trend: 0, mk_trend: '暂无', data: [] },
    ndbi: { mean: 0, trend: 0, mk_trend: '暂无', data: [] },
    ndwi: { mean: 0, trend: 0, mk_trend: '暂无', data: [] },
    ndsi: { mean: 0, trend: 0, mk_trend: '暂无', data: [] }
  });

  const loadData = async () => {
    try {
      // 1. Fetch Stats
      const statsRes = await axios.get('http://localhost:8000/api/stats');
      const stats = statsRes.data;
      mineTotal.value = stats.mineTotal;
      overviewArea.value = stats.mineAreaTotal;
      treatedCount.value = stats.treatedCount;
      untreatedCount.value = stats.untreatedCount;
      restorationMethodList.value = stats.restorationMethodList || [];
      miningMethodList.value = stats.miningMethodList || []; // Add this
      landTypeList.value = stats.landTypeList || [];
      
      // 2. Fetch GeoJSON
      const geoRes = await axios.get('http://localhost:8000/api/geojson');
      if (geoRes.data && geoRes.data.features) {
        allMinesData.value = geoRes.data.features;
        
        // Extract Filter Options
        const cities = new Set();
        const methods = new Set();
        allMinesData.value.forEach(f => {
          const p = f.properties || {};
          if (p.SHI) cities.add(p.SHI);
          if (p.KCFS) methods.add(p.KCFS);
        });
        cityOptions.value = Array.from(cities).filter(Boolean);
        miningMethodOptions.value = Array.from(methods).filter(Boolean);
        
        applyFilters();
      }
    } catch (e) {
      console.error("Data load error:", e);
    }
  };

  const applyFilters = () => {
    filteredMinesData.value = allMinesData.value.filter(f => {
      const p = f.properties || {};
      const cityMatch = !filterCity.value || p.SHI === filterCity.value;
      const methodMatch = !filterMethod.value || p.KCFS === filterMethod.value;
      
      let statusMatch = true;
      if (filterStatus.value) {
        const norm = p.status_normalized || 'unknown';
        statusMatch = norm === filterStatus.value;
      }
      
      // Basic client-side search filtering (if searchMineId is set and matches locally)
      // Note: The main search uses searchMineById to find specific mines, 
      // but we can also filter the list if needed. 
      // For now, let's keep search separate or integrate it here.
      // If we want search to filter the map view:
      let searchMatch = true;
      if (searchMineId.value) {
         const q = searchMineId.value.toLowerCase();
         const idMatch = String(p.FID_1) === q;
         const nameMatch = p.mine_name && p.mine_name.includes(q);
         searchMatch = idMatch || nameMatch;
      }

      return cityMatch && methodMatch && statusMatch && (searchMineId.value ? searchMatch : true);
    });
  };

  const resetFilters = () => {
    filterCity.value = '';
    filterStatus.value = '';
    filterMethod.value = '';
    searchMineId.value = '';
    applyFilters();
  };

  const fetchIndices = async (fid) => {
    try {
      const res = await axios.get(`http://localhost:8000/api/mines/indices?fid=${fid}`);
      mineIndices.value = res.data;
    } catch (e) {
      console.warn("No indices data for FID:", fid);
      mineIndices.value = { ndvi: {}, ndbi: {}, ndwi: {}, ndsi: {} };
    }
  };
  
  // Helper to format numbers
  const formatMaybeNumber = (v, d = 2) => {
    const n = Number(v);
    return Number.isFinite(n) ? n.toFixed(d) : '--';
  };

  const formatTrend = (v) => {
    const n = Number(v);
    if (!Number.isFinite(n)) return '--';
    return n > 0 ? `+${n.toFixed(4)}` : `${n.toFixed(4)}`;
  };

  const getTrendClass = (v) => {
    const n = Number(v);
    if (!Number.isFinite(n)) return '';
    return n > 0 ? 'text-green' : (n < 0 ? 'text-red' : '');
  };

  return {
    allMinesData,
    filteredMinesData,
    filterCity,
    filterStatus,
    filterMethod,
    searchMineId,
    cityOptions,
    miningMethodOptions,
    mineTotal,
    overviewArea,
    treatedCount,
    untreatedCount,
    restorationMethodList,
    miningMethodList, // Add this
    landTypeList,
    mineIndices,
    loadData,
    applyFilters,
    resetFilters,
    fetchIndices,
    formatMaybeNumber,
    formatTrend,
    getTrendClass
  };
}
