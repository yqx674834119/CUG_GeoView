<template>
  <div class="header-content">
    <div class="header-left">
      <span class="platform-info"> </span>
    </div>
    <div class="header-right">
      <el-button type="text" class="system-menu">
        <i class="icon-settings" />
        系统设置
      </el-button>
    </div>
  </div>
</template>

<script>
export default {
  name: 'HeaderComponent',
  methods: {
    handleSystemSettings() {
      // 系统设置功能，暂时预留
      this.$message.info('系统设置功能开发中...');
    },
  },
};
</script>
<style scoped>
.header-content {
  display: flex;
  justify-content: space-between;
  align-items: center;
  width: 100%;
  padding: 0;
  font-family: Microsoft JhengHei UI, sans-serif;
  height: 60px;
}

.header-left {
  flex: 1;
}

.platform-info {
  color: var(--text-primary);
  font-size: 18px;
  font-weight: 600;
  letter-spacing: 0.5px;
}

.header-right {
  display: flex;
  align-items: center;
}

.system-menu {
  color: var(--text-secondary);
  font-size: 14px;
  padding: 8px 16px;
  border-radius: 6px;
  transition: all var(--transition-fast);
}

.system-menu:hover {
  color: var(--primary-light);
  background-color: var(--bg-hover);
}

.system-menu .iconfont {
  margin-right: 6px;
  font-size: 16px;
}

@media (max-width: 768px) {
  .header-content {
    padding: 0 10px;
  }
  
  .platform-info {
    font-size: 16px;
  }
  
  .system-menu {
    font-size: 12px;
    padding: 6px 12px;
  }
}
</style>
