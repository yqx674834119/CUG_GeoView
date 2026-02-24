<template>
  <div id="map" class="h-screen w-full"></div>
  <div v-if="showPanel" class="fixed bottom-5 right-5 w-96 bg-white shadow-lg rounded-lg p-3">
    <h3 class="text-lg font-bold">矿山 {{ currentFID }}</h3>
    <p>NDVI 均值：{{ ndviMean }}</p>
    <p>
      趋势：
      <span :style="{ color: ndviTrend > 0 ? 'green' : (ndviTrend < 0 ? 'red' : 'gray') }">
        {{ ndviTrend }}
      </span>
    </p>
  </div>
</template>

<script setup>
import { ref, onMounted } from "vue";
import * as L from "leaflet";
import axios from "axios";

const showPanel = ref(false);
const currentFID = ref("");
const ndviMean = ref(0);
const ndviTrend = ref(0);

onMounted(async () => {
  const map = L.map("map").setView([256, 100.2], 8);
  L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png").addTo(map);

  const res = await axios.get("http://localhost:8000/api/mines");
  const mines = res.data;

  mines.forEach((mine) => {
    const geom = mine.geometry;
    const polygon = L.geoJSON(geom, { color: "blue" }).addTo(map);
    polygon.on("click", async () => {
      const ndviRes = await axios.get(`http://localhost:8000/api/mines/ndvi?fid=${mine.fid}`);
      const data = ndviRes.data;
      if (!data || data.error) return alert("未找到 NDVI 数据");
      currentFID.value = data.fid;
      ndviMean.value = data.ndvi_mean;
      ndviTrend.value = data.ndvi_trend;
      showPanel.value = true;
    });
  });
});
</script>
