<template>
  <div class="header-content">
    <div class="header-left">
      <span class="platform-info">智能遥感解译系统</span>
    </div>
    <div class="header-right">
      <el-button
        v-if="minerEnabled"
        type="primary"
        class="miner-btn"
        @click="goToMiner"
      >
        <i class="icon-map" style="margin-right: 4px;" />
        ⛏️ 矿山监测系统
      </el-button>
      <el-button
        class="theme-toggle"
        @click="handleThemeToggle"
      >
        <i :class="themeIconClass" />
        {{ isDarkTheme ? "切换浅色" : "切换深色" }}
      </el-button>
    </div>
  </div>
</template>

<script>
import {
  THEME_CHANGE_EVENT,
  getCurrentTheme,
  toggleTheme,
} from "@/utils/theme";
import global from "@/global";

export default {
  name: 'HeaderComponent',
  data() {
    return {
      currentTheme: getCurrentTheme(),
    };
  },
  computed: {
    minerEnabled() {
      return global.MINER_ENABLED;
    },
    minerUrl() {
      return global.MINER_URL;
    },
    isDarkTheme() {
      return this.currentTheme === "dark";
    },
    themeIconClass() {
      return this.isDarkTheme ? "icon-sun" : "icon-moon";
    },
  },
  mounted() {
    window.addEventListener(THEME_CHANGE_EVENT, this.syncTheme);
  },
  beforeUnmount() {
    window.removeEventListener(THEME_CHANGE_EVENT, this.syncTheme);
  },
  methods: {
    syncTheme(event) {
      this.currentTheme = event.detail.theme;
    },
    handleThemeToggle() {
      this.currentTheme = toggleTheme();
    },
    goToMiner() {
      window.open(this.minerUrl, '_blank');
    },
  },
};
</script>
<style scoped>
.header-content {
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex: 1;
  width: 100%;
  min-width: 0;
  padding: 0;
  height: 60px;
  gap: 16px;
}

.header-left {
  display: flex;
  align-items: center;
  min-width: 0;
  flex: 1;
}

.platform-info {
  color: var(--theme-heading-color);
  font-size: 18px;
  font-weight: 700;
  letter-spacing: 0.04em;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.header-right {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-shrink: 0;
  white-space: nowrap;
}

.miner-btn {
  background: linear-gradient(135deg, var(--theme-major-color), var(--primary-hover)) !important;
  border: none !important;
  color: var(--text-inverse) !important;
  font-weight: 500;
  border-radius: 999px;
  transition: all var(--transition-fast);
}

.miner-btn:hover {
  transform: translateY(-1px);
  box-shadow: 0 10px 22px rgba(0, 100, 201, 0.24);
}

.theme-toggle {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  background: var(--theme-tag-bg);
  border: 1px solid transparent;
  color: var(--theme-active-color);
}

.theme-toggle:hover {
  border-color: var(--theme-active-color);
  background: transparent;
}

.theme-toggle [class^="icon-"]::before,
.theme-toggle [class*=" icon-"]::before {
  width: 16px;
  height: 16px;
}

@media (max-width: 768px) {
  .header-content {
    height: auto;
    min-height: 60px;
    flex-wrap: wrap;
    padding: 6px 0;
  }
  
  .platform-info {
    font-size: 16px;
  }

  .header-right {
    width: 100%;
    justify-content: flex-start;
    gap: 8px;
  }
}
</style>
