<template>
  <header class="header">
    <div class="header-left">
      <div class="logo-area">
        <h1 class="title">云南矿山生态修复智能监测平台</h1>
      </div>
      <div class="weather-widget">
        <span class="weather-icon">{{ weatherIcon }}</span>
        <div class="weather-info">
          <span class="temp">{{ temperature }}°C</span>
          <span class="aqi" :class="getAqiClass(airQuality)">空气{{ airQuality }}</span>
        </div>
      </div>
    </div>
    <div class="header-right">
      <div class="time-widget">{{ currentDate }} {{ currentTime }}</div>
      <div class="user-profile">
        <span class="role">管理员</span>
      </div>
      <button class="system-btn" @click="goToGeoView">
        <span>🌍 GeoView 遥感平台</span>
        <svg viewBox="0 0 24 24" width="16" height="16" stroke="currentColor" stroke-width="2" fill="none"><path d="M5 12h14M12 5l7 7-7 7"/></svg>
      </button>
    </div>
  </header>
</template>

<script setup>
import { defineProps } from 'vue';

const props = defineProps({
  weatherIcon: String,
  temperature: [Number, String],
  airQuality: String,
  currentDate: String,
  currentTime: String,
  getAqiClass: Function
});

const goToGeoView = () => {
  let base = import.meta.env.VITE_GEOVIEW_URL || 'http://localhost:3000/'
  const hasHash = /#\//.test(base)
  const target = hasHash ? base : (base.endsWith('/') ? base + '#/detectchanges' : base + '/#/detectchanges')
  window.location.href = target
};
</script>

<style scoped>
.header {
  height: 60px;
  background: rgba(10, 25, 41, 0.85);
  backdrop-filter: blur(10px);
  border-bottom: 1px solid var(--border-color);
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0 20px;
  z-index: 2000;
}

.header-left, .header-right { display: flex; align-items: center; gap: 20px; }

.logo-area { display: flex; align-items: center; gap: 10px; }
.logo-icon { font-size: 24px; }
.title { font-size: 20px; font-weight: 600; letter-spacing: 1px; margin: 0; background: linear-gradient(90deg, #fff, #4ecdc4); -webkit-background-clip: text; color: transparent; }

.weather-widget { display: flex; align-items: center; gap: 10px; padding: 5px 15px; background: rgba(255,255,255,0.05); border-radius: 20px; }
.weather-info { display: flex; flex-direction: column; font-size: 12px; line-height: 1.2; }
.temp { font-weight: bold; color: #f1c40f; }
.aqi { padding: 1px 4px; border-radius: 4px; font-size: 10px; color: #fff; }
.aqi-1 { background: rgba(0, 228, 0, 0.6); }   /* 优 - Green */
.aqi-2 { background: rgba(255, 255, 0, 0.6); color: #000; } /* 良 - Yellow */
.aqi-3 { background: rgba(255, 126, 0, 0.6); } /* 轻度 - Orange */
.aqi-4 { background: rgba(255, 0, 0, 0.6); }   /* 中度 - Red */
.aqi-5 { background: rgba(153, 0, 76, 0.6); }  /* 重度 - Purple */
.aqi-6 { background: rgba(126, 0, 35, 0.6); }  /* 严重 - Maroon */

.system-btn {
  background: linear-gradient(135deg, #0984e3, #00cec9);
  border: none;
  padding: 8px 16px;
  border-radius: 4px;
  color: white;
  cursor: pointer;
  display: flex;
  align-items: center;
  gap: 8px;
  font-weight: 500;
  transition: transform 0.2s;
}
.system-btn:hover { transform: translateY(-1px); box-shadow: 0 4px 12px rgba(9, 132, 227, 0.4); }
</style>
