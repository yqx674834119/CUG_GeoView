<template>
  <transition name="fade">
    <div v-if="visible" class="modal-overlay" @click.self="$emit('close')">
      <div class="modal-content glass-panel">
        <div class="modal-header">
          <h3>{{ mineData.name }}</h3>
          <button class="close-btn" @click="$emit('close')">×</button>
        </div>
        <div class="modal-body">
          <div class="info-grid">
            <div class="info-item"><span class="label">矿山ID:</span> <span class="val">{{ mineData.mine_id }}</span></div>
            <div class="info-item"><span class="label">面积:</span> <span class="val">{{ mineData.area ? Number(mineData.area).toFixed(2) : '暂无' }} m²</span></div>
            <div class="info-item"><span class="label">状态:</span> 
              <span class="status-tag" :class="mineData.status_normalized">
                {{ mineData.status_raw || '未知' }}
              </span>
            </div>
            <div class="info-item"><span class="label">坐标:</span> <span class="val">{{ (mineData.center_lat||0).toFixed(4) }}, {{ (mineData.center_lng||0).toFixed(4) }}</span></div>
          </div>

          <div class="tabs">
            <button v-for="tab in ['NDVI', 'NDBI', 'NDWI', 'NDSI']" 
              :key="tab"
              :class="{ active: selectedTab === tab }"
              @click="$emit('tab-change', tab)">
              {{ tab }}
            </button>
          </div>

          <div class="trend-stats">
            <div class="stat-box">
              <span class="label">均值</span>
              <span class="val">{{ formatMaybeNumber(indicesData[selectedTab.toLowerCase()]?.mean, 3) }}</span>
            </div>
            <div class="stat-box">
              <span class="label">趋势斜率</span>
              <span class="val" :class="getTrendClass(indicesData[selectedTab.toLowerCase()]?.trend)">
                {{ formatTrend(indicesData[selectedTab.toLowerCase()]?.trend) }}
              </span>
            </div>
            <div class="stat-box">
              <span class="label">MK检验</span>
              <span class="val">{{ indicesData[selectedTab.toLowerCase()]?.mk_trend }}</span>
            </div>
          </div>

          <div class="chart-container" ref="trendChartRef"></div>
        </div>
      </div>
    </div>
  </transition>
</template>

<script setup>
import { defineProps, defineEmits, ref, watch, nextTick, onMounted } from 'vue';
import * as echarts from 'echarts';

const props = defineProps({
  visible: Boolean,
  mineData: Object,
  indicesData: Object,
  selectedTab: String,
  formatMaybeNumber: Function,
  formatTrend: Function,
  getTrendClass: Function
});

const emit = defineEmits(['close', 'tab-change']);

const trendChartRef = ref(null);
let trendChartInst = null;

const renderTrendChart = () => {
  if (!trendChartRef.value) return;
  if (trendChartInst) trendChartInst.dispose();
  trendChartInst = echarts.init(trendChartRef.value);
  
  const key = props.selectedTab.toLowerCase();
  const dataset = props.indicesData[key];
  const data = dataset?.data || [];
  
  const years = data.map(d => d.year);
  const values = data.map(d => d.value);
  
  const colorMap = { ndvi: '#00b894', ndbi: '#fdcb6e', ndwi: '#0984e3', ndsi: '#e17055' };
  const color = colorMap[key] || '#00b894';

  trendChartInst.setOption({
    backgroundColor: 'transparent',
    tooltip: { trigger: 'axis' },
    grid: { top: 30, bottom: 20, left: 40, right: 20 },
    xAxis: { type: 'category', data: years, axisLine: { lineStyle: { color: '#666' } } },
    yAxis: { type: 'value', splitLine: { lineStyle: { color: 'rgba(255,255,255,0.1)' } }, axisLine: { lineStyle: { color: '#666' } } },
    series: [{
      data: values,
      type: 'line',
      smooth: true,
      lineStyle: { color: color, width: 3 },
      itemStyle: { color: color },
      areaStyle: {
        color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [{ offset: 0, color: color + '80' }, { offset: 1, color: color + '00' }])
      }
    }]
  });
};

watch(() => [props.visible, props.selectedTab, props.indicesData], () => {
  if (props.visible) {
    nextTick(() => renderTrendChart());
  }
}, { deep: true });

</script>

<style scoped>
.modal-overlay {
  position: fixed;
  top: 0; left: 0; right: 0; bottom: 0;
  background: rgba(0,0,0,0.6);
  z-index: 3000;
  display: flex;
  align-items: center;
  justify-content: center;
}
.modal-content {
  width: 600px;
  background: #0a1929;
  border: 1px solid #4ecdc4;
  box-shadow: 0 0 30px rgba(78, 205, 196, 0.2);
}
.modal-header { display: flex; justify-content: space-between; border-bottom: 1px solid rgba(255,255,255,0.1); padding-bottom: 10px; margin-bottom: 15px; }
.close-btn { background: none; border: none; color: #fff; font-size: 24px; cursor: pointer; }

.glass-panel {
  background: rgba(255,255,255,0.03);
  border: 1px solid rgba(255,255,255,0.08);
  border-radius: 8px;
  padding: 12px;
}

.info-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; margin-bottom: 20px; }
.info-item { display: flex; justify-content: space-between; border-bottom: 1px dashed rgba(255,255,255,0.1); padding-bottom: 5px; }
.label { color: #8da3b6; font-size: 13px; }
.val { font-weight: bold; }
.status-tag { padding: 2px 8px; border-radius: 4px; font-size: 12px; }
.status-tag.treated { background: rgba(0, 184, 148, 0.2); color: #00b894; }
.status-tag.untreated { background: rgba(255, 118, 117, 0.2); color: #ff7675; }

.tabs { display: flex; gap: 10px; margin-bottom: 15px; }
.tabs button {
  flex: 1;
  background: rgba(255,255,255,0.05);
  border: 1px solid rgba(255,255,255,0.1);
  color: #fff;
  padding: 8px;
  cursor: pointer;
}
.tabs button.active { background: #4ecdc4; color: #000; border-color: #4ecdc4; }

.trend-stats { display: flex; justify-content: space-around; margin-bottom: 15px; background: rgba(0,0,0,0.2); padding: 10px; border-radius: 6px; }
.stat-box { display: flex; flex-direction: column; align-items: center; }
.stat-box .val { font-size: 16px; margin-top: 5px; }
.text-red { color: #ff7675; }
.text-green { color: #00b894; }

.chart-container { height: 250px; width: 100%; }

/* Transitions */
.fade-enter-active, .fade-leave-active { transition: opacity 0.3s; }
.fade-enter-from, .fade-leave-to { opacity: 0; }
</style>
