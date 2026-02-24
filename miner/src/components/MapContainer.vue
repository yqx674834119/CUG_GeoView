<template>
  <div class="map-container" ref="mapContainer">
    <div id="map"></div>
    
    <!-- 地图图层控制 -->
    <div class="map-tools" :class="{ 'shifted-right': rightCollapsed }">
      <div class="tool-btn" :class="{ active: currentLayer === 'base' }" @click="switchLayer('base')" title="标准地图">🗺️</div>
      <div class="tool-btn" :class="{ active: currentLayer === 'satellite' }" @click="switchLayer('satellite')" title="卫星影像">🛰️</div>
      <div class="tool-btn" :class="{ active: currentLayer === 'terrain' }" @click="switchLayer('terrain')" title="地形图">⛰️</div>
    </div>

    <!-- 悬浮图例 -->
    <div class="map-legend glass-panel" :class="{ 'shifted-left': leftCollapsed }">
      <div class="legend-item"><span class="dot treated"></span> 已治理</div>
      <div class="legend-item"><span class="dot untreated"></span> 未治理</div>
      <div class="legend-item"><span class="dot unknown"></span> 未知/其他</div>
    </div>
  </div>
</template>

<script setup>
import { onMounted, onUnmounted, ref, watch, defineProps, defineEmits, defineExpose } from 'vue';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';

const props = defineProps({
  minesData: Array,
  leftCollapsed: Boolean,
  rightCollapsed: Boolean
});

const emit = defineEmits(['select-mine']);

const map = ref(null);
const mineLayer = ref(null);
const currentLayer = ref('satellite');
const mapContainer = ref(null); // Ref for the container div
let baseMaps = {};
let resizeObserver = null;

const initMap = () => {
  if (!mapContainer.value) return;
  map.value = L.map(mapContainer.value, { zoomControl: false, attributionControl: false }).setView([25.6, 100.2], 9);
  L.control.zoom({ position: 'bottomright' }).addTo(map.value);
  
  baseMaps = {
    base: L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', { maxZoom: 19 }),
    satellite: L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}', { maxZoom: 19 }),
    terrain: L.tileLayer('https://{s}.tile.opentopomap.org/{z}/{x}/{y}.png', { maxZoom: 17 })
  };
  
  baseMaps[currentLayer.value].addTo(map.value);
};

const switchLayer = (layer) => {
  currentLayer.value = layer;
  if (!map.value) return;
  
  Object.values(baseMaps).forEach(l => map.value.removeLayer(l));
  baseMaps[layer].addTo(map.value);
};

const renderMapMarkers = () => {
  if (!map.value) return;
  if (mineLayer.value) map.value.removeLayer(mineLayer.value);
  
  const geoJsonData = { type: 'FeatureCollection', features: props.minesData };
  
  mineLayer.value = L.geoJSON(geoJsonData, {
    style: (feature) => {
      const status = feature.properties.status_normalized || 'unknown';
      let color = '#fab1a0'; // Default unknown
      if (status === 'treated') color = '#00b894'; // Green
      if (status === 'untreated') color = '#ff7675'; // Red
      
      return {
        color: color,
        weight: 1,
        opacity: 0.8,
        fillColor: color,
        fillOpacity: 0.4
      };
    },
    onEachFeature: (feature, layer) => {
      // Tooltip
      const name = feature.properties.mine_name || feature.properties.name || `ID: ${feature.properties.FID_1}`;
      layer.bindTooltip(name, { direction: 'top', className: 'map-tooltip' });
      
      // Click
      layer.on('click', () => {
        const bounds = layer.getBounds();
        const center = bounds.getCenter();
        emit('select-mine', { feature, center, bounds });
      });
      
      // Hover highlight
      layer.on('mouseover', (e) => {
        e.target.setStyle({ weight: 3, fillOpacity: 0.7 });
      });
      layer.on('mouseout', (e) => {
        mineLayer.value.resetStyle(e.target);
      });
    }
  }).addTo(map.value);
  
  if (props.minesData.length > 0) {
    try {
      map.value.fitBounds(mineLayer.value.getBounds(), { padding: [50, 50] });
    } catch(e) {}
  }
};

const flyToMine = (fid) => {
  if (!map.value || !mineLayer.value) return;
  let targetLayer = null;
  mineLayer.value.eachLayer(l => {
      if (l.feature.properties.FID_1 === fid) {
        targetLayer = l;
      }
  });
  
  if (targetLayer) {
     map.value.fitBounds(targetLayer.getBounds(), { maxZoom: 15 });
     targetLayer.openTooltip();
     const bounds = targetLayer.getBounds();
     const center = bounds.getCenter();
     emit('select-mine', { feature: targetLayer.feature, center, bounds });
  }
};

const invalidateSize = () => {
  if (map.value) map.value.invalidateSize();
}

watch(() => props.minesData, () => {
  renderMapMarkers();
}, { deep: true });

onMounted(() => {
  initMap();
  
  // Setup ResizeObserver to handle layout changes (sidebar toggle)
  if (mapContainer.value) {
    resizeObserver = new ResizeObserver(() => {
      invalidateSize();
    });
    resizeObserver.observe(mapContainer.value);
  }
});

onUnmounted(() => {
  if (resizeObserver) {
    resizeObserver.disconnect();
  }
});

defineExpose({
  flyToMine,
  invalidateSize
});
</script>

<style scoped>
.map-container {
  flex: 1;
  position: relative;
  background: #000;
  width: 100%;
  height: 100%;
  overflow: hidden; /* Ensure no scrollbars */
}
#map { width: 100%; height: 100%; z-index: 1; }

.map-tools {
  position: absolute;
  top: 20px;
  right: 400px; /* Default */
  z-index: 10;
  display: flex;
  gap: 10px;
  transition: right 0.3s;
}
.map-tools.shifted-right { right: 60px; }

.tool-btn {
  width: 40px;
  height: 40px;
  background: rgba(13, 27, 42, 0.8);
  border: 1px solid var(--border-color);
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  font-size: 20px;
  transition: all 0.2s;
}
.tool-btn:hover, .tool-btn.active { background: #4ecdc4; color: #000; }

.map-legend {
  position: absolute;
  bottom: 20px;
  left: 300px; /* Default */
  z-index: 10;
  padding: 10px 15px;
  display: flex;
  gap: 15px;
  transition: left 0.3s;
}
.map-legend.shifted-left { left: 60px; }

.legend-item { display: flex; align-items: center; gap: 6px; font-size: 12px; }
.dot { width: 10px; height: 10px; border-radius: 50%; }
.dot.treated { background: #00b894; }
.dot.untreated { background: #ff7675; }
.dot.unknown { background: #fab1a0; }

.glass-panel {
  background: rgba(255,255,255,0.03);
  border: 1px solid rgba(255,255,255,0.08);
  border-radius: 8px;
  padding: 12px;
}
</style>
