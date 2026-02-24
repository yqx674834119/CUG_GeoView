<template>
  <aside class="sidebar right-sidebar" :class="{ 'collapsed': collapsed }">
    <div class="sidebar-header">
      <button class="collapse-btn" @click="$emit('toggle')">
        {{ collapsed ? '◀' : '➤' }}
      </button>
      <h2>分析统计</h2>
    </div>

    <div class="sidebar-content" v-show="!collapsed">
      <!-- 治理状态饼图 -->
      <div class="chart-panel glass-panel">
        <div class="panel-header"><h3>治理状态分布</h3></div>
        <div ref="pieChartRef" class="chart-box"></div>
      </div>

      <!-- 修复后地类 -->
      <div class="chart-panel glass-panel">
        <div class="panel-header"><h3>修复后地类 (Land Type)</h3></div>
        <div class="land-type-list">
           <div class="land-item" v-for="(item, idx) in landTypeList" :key="idx">
             <div class="land-info">
               <span class="land-name">{{ item.name }}</span>
               <span class="land-val">{{ item.value }}</span>
             </div>
             <div class="progress-bg">
               <div class="progress-fill" :style="{ width: Math.min(100, (item.value / (landTypeList[0]?.value || 1)) * 100) + '%' }"></div>
             </div>
           </div>
        </div>
      </div>

      <!-- 开采方式统计 -->
      <div class="chart-panel glass-panel">
        <div class="panel-header"><h3>开采方式统计</h3></div>
        <div ref="barChartRef" class="chart-box"></div>
      </div>
    </div>
  </aside>
</template>

<script setup>
import { defineProps, ref, onMounted, watch, nextTick, defineEmits } from 'vue';
import * as echarts from 'echarts';

const props = defineProps({
  collapsed: Boolean,
  treatedCount: Number,
  untreatedCount: Number,
  landTypeList: Array,
  miningMethodList: Array
});

const emit = defineEmits(['toggle']);

const pieChartRef = ref(null);
const barChartRef = ref(null);
let pieChartInst = null;
let barChartInst = null;

const initPieChart = () => {
  if (!pieChartRef.value) return;
  pieChartInst = echarts.init(pieChartRef.value);
  const data = [
    { value: props.treatedCount, name: '已治理', itemStyle: { color: '#00b894' } },
    { value: props.untreatedCount, name: '未治理', itemStyle: { color: '#ff7675' } }
  ];
  
  pieChartInst.setOption({
    backgroundColor: 'transparent',
    tooltip: { trigger: 'item' },
    legend: { bottom: '0%', textStyle: { color: '#fff' } },
    series: [
      {
        name: '治理状态',
        type: 'pie',
        radius: ['40%', '70%'],
        center: ['50%', '45%'],
        data: data,
        label: { show: false },
        emphasis: { itemStyle: { shadowBlur: 10, shadowOffsetX: 0, shadowColor: 'rgba(0, 0, 0, 0.5)' } }
      }
    ]
  });
};

const initBarChart = () => {
  if (!barChartRef.value) return;
  barChartInst = echarts.init(barChartRef.value);
  // Re-fetch miningMethodList if needed or passed from props
  // Wait, miningMethodList is derived in App from stats.miningMethodList
  // But useMineData computes `miningMethodOptions` for filter, but `miningMethodList` for chart comes from `stats` API.
  // In `App.vue`, we had `miningMethodList` ref populated from stats.
  // Let's assume props.miningMethodList is passed correctly.
  
  const list = (props.miningMethodList || []).slice(0, 5);
  
  barChartInst.setOption({
    backgroundColor: 'transparent',
    tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' } },
    grid: { left: '3%', right: '4%', bottom: '3%', top: '3%', containLabel: true },
    xAxis: { type: 'value', splitLine: { show: false }, axisLabel: { color: '#ccc' } },
    yAxis: { type: 'category', data: list.map(i => i.name), axisLabel: { color: '#ccc', width: 80, overflow: 'truncate' } },
    series: [
      {
        type: 'bar',
        data: list.map(i => i.value),
        itemStyle: {
          color: new echarts.graphic.LinearGradient(1, 0, 0, 0, [{ offset: 0, color: '#0984e3' }, { offset: 1, color: '#74b9ff' }])
        },
        barWidth: '60%'
      }
    ]
  });
};

const updateCharts = () => {
  if (pieChartInst) {
     const data = [
        { value: props.treatedCount, name: '已治理', itemStyle: { color: '#00b894' } },
        { value: props.untreatedCount, name: '未治理', itemStyle: { color: '#ff7675' } }
     ];
     pieChartInst.setOption({ series: [{ data }] });
  }
  
  if (barChartInst) {
     const list = (props.miningMethodList || []).slice(0, 5);
     barChartInst.setOption({
       yAxis: { data: list.map(i => i.name) },
       series: [{ data: list.map(i => i.value) }]
     });
  }
};

watch(() => [props.treatedCount, props.untreatedCount], () => {
  updateCharts();
});

watch(() => props.miningMethodList, () => {
  updateCharts();
}, { deep: true });

onMounted(() => {
  nextTick(() => {
    initPieChart();
    initBarChart();
  });
  window.addEventListener('resize', () => {
    pieChartInst && pieChartInst.resize();
    barChartInst && barChartInst.resize();
  });
});
</script>

<style scoped>
.sidebar {
  width: 300px;
  background: rgba(10, 25, 41, 0.65);
  backdrop-filter: blur(15px);
  border-right: 1px solid var(--border-color);
  display: flex;
  flex-direction: column;
  z-index: 100;
  transition: width 0.3s ease;
  overflow: hidden;
}
.right-sidebar { border-left: 1px solid var(--border-color); border-right: none; }

.sidebar.collapsed { width: 40px; }
.sidebar.collapsed .sidebar-content { opacity: 0; pointer-events: none; }

.sidebar-header {
  height: 50px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 10px;
  border-bottom: 1px solid rgba(255,255,255,0.1);
  white-space: nowrap;
}
.sidebar-header h2 { font-size: 16px; margin: 0; color: #4ecdc4; flex: 1; text-align: center; }
.collapse-btn {
  background: none;
  border: none;
  color: #8da3b6;
  cursor: pointer;
  font-size: 12px;
  padding: 5px;
}

.sidebar-content {
  flex: 1;
  overflow-y: auto;
  padding: 15px;
  display: flex;
  flex-direction: column;
  gap: 15px;
  transition: opacity 0.2s;
}

.glass-panel {
  background: rgba(255,255,255,0.03);
  border: 1px solid rgba(255,255,255,0.08);
  border-radius: 8px;
  padding: 12px;
}

.panel-header h3 {
  font-size: 14px;
  color: #fff;
  margin: 0 0 10px 0;
  border-left: 3px solid #4ecdc4;
  padding-left: 8px;
}

.chart-box { height: 180px; width: 100%; }

/* Land Type */
.land-type-list { display: flex; flex-direction: column; gap: 8px; }
.land-item { font-size: 12px; }
.land-info { display: flex; justify-content: space-between; margin-bottom: 2px; }
.progress-bg { height: 6px; background: rgba(255,255,255,0.1); border-radius: 3px; }
.progress-fill { height: 100%; background: linear-gradient(90deg, #6c5ce7, #a29bfe); border-radius: 3px; }
</style>
