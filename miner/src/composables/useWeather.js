import { ref, onMounted, onUnmounted } from 'vue';
import axios from 'axios';

export function useWeather() {
  const currentDate = ref('');
  const currentTime = ref('');
  const temperature = ref('--');
  const weatherIcon = ref('🌤️');
  const airQuality = ref('良');
  const humidity = ref('--');

  let timeInterval = null;

  const updateDateTime = () => {
    const now = new Date();
    currentDate.value = now.toLocaleDateString('zh-CN', { year: 'numeric', month: '2-digit', day: '2-digit' });
    currentTime.value = now.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' });
  };

  const mapWeatherCodeToIcon = (code) => {
    const c = Number(code);
    if (!Number.isFinite(c)) return '—';
    if (c === 0) return '☀️';
    if (c === 1 || c === 2) return '🌤️';
    if (c === 3) return '☁️';
    if (c === 45 || c === 48) return '🌫️';
    if (c === 51 || c === 53 || c === 55) return '🌦️';
    if (c === 56 || c === 57) return '🌧️';
    if (c === 61 || c === 63 || c === 65) return '🌧️';
    if (c === 66 || c === 67) return '🌧️';
    if (c === 71 || c === 73 || c === 75) return '🌨️';
    if (c === 77) return '🌨️';
    if (c === 80 || c === 81 || c === 82) return '🌧️';
    if (c === 85 || c === 86) return '🌨️';
    if (c === 95) return '⛈️';
    if (c === 96 || c === 99) return '⛈️';
    return '—';
  };

  // Based on China National Standard HJ 633-2012 (AQI)
  const formatAqiToText = (aqi) => {
    if (aqi == null) return '暂无';
    if (aqi <= 50) return '优';
    if (aqi <= 100) return '良';
    if (aqi <= 150) return '轻度污染';
    if (aqi <= 200) return '中度污染';
    if (aqi <= 300) return '重度污染';
    return '严重污染';
  };

  const fetchRealtimeEnvironmentAt = async (lat, lon) => {
    try {
      const weatherUrl = 'https://api.open-meteo.com/v1/forecast';
      const airUrl = 'https://air-quality-api.open-meteo.com/v1/air-quality';
      
      const w = await axios.get(weatherUrl, {
        params: {
          latitude: lat,
          longitude: lon,
          current: 'temperature_2m,relative_humidity_2m,weather_code',
          timezone: 'Asia/Shanghai'
        }
      });
      const curr = w?.data?.current || {};
      if (curr.temperature_2m != null) temperature.value = Math.round(curr.temperature_2m);
      if (curr.relative_humidity_2m != null) humidity.value = Math.round(curr.relative_humidity_2m);
      weatherIcon.value = mapWeatherCodeToIcon(curr.weather_code);

      const aq = await axios.get(airUrl, {
        params: {
          latitude: lat,
          longitude: lon,
          hourly: 'us_aqi,pm2_5,pm10', // Note: Using US AQI as proxy, ideally calculate from PM2.5/PM10 per HJ 633-2012
          timezone: 'Asia/Shanghai'
        }
      });
      const h = aq?.data?.hourly;
      let aqi = null;
      if (h?.us_aqi?.length) aqi = h.us_aqi[h.us_aqi.length - 1];
      airQuality.value = formatAqiToText(aqi);
    } catch (e) {
      console.warn('实时环境数据拉取失败:', e.message);
    }
  };

  const getAqiClass = (aqiStr) => {
    // Map text back to class based on HJ 633-2012 colors
    switch (aqiStr) {
        case '优': return 'aqi-1'; // Green
        case '良': return 'aqi-2'; // Yellow
        case '轻度污染': return 'aqi-3'; // Orange
        case '中度污染': return 'aqi-4'; // Red
        case '重度污染': return 'aqi-5'; // Purple
        case '严重污染': return 'aqi-6'; // Maroon
        default: return '';
    }
  };

  onMounted(() => {
    updateDateTime();
    timeInterval = setInterval(updateDateTime, 1000);
    // Initial fetch for a default location (e.g., Dali) if needed, 
    // or let the map trigger it.
  });

  onUnmounted(() => {
    if (timeInterval) clearInterval(timeInterval);
  });

  return {
    currentDate,
    currentTime,
    temperature,
    weatherIcon,
    airQuality,
    humidity,
    getAqiClass,
    fetchRealtimeEnvironmentAt
  };
}
