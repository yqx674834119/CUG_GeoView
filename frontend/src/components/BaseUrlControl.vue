<template>
  <div class="base-url-control">
    <span class="base-url-control__label">后端</span>
    <el-input
      v-model="draftUrl"
      class="base-url-control__input"
      size="small"
      @keyup.enter="save"
    />
    <el-button
      size="small"
      type="primary"
      plain
      @click="save"
    >
      保存
    </el-button>
    <el-button
      size="small"
      plain
      @click="checkHealth"
    >
      Health
    </el-button>
  </div>
</template>

<script>
import { ElMessage } from "element-plus";
import global from "@/global";

export default {
  name: "BaseUrlControl",
  data() {
    return {
      draftUrl: global.BASEURL,
    };
  },
  methods: {
    save() {
      const nextUrl = global.setBackendBaseUrl(this.draftUrl);
      this.draftUrl = nextUrl;
      ElMessage.success("后端地址已更新");
    },
    async checkHealth() {
      this.save();
      const url = `${String(global.BASEURL || "").replace(/\/+$/, "")}/health`;
      try {
        const response = await fetch(url, { headers: { Accept: "application/json" } });
        const text = await response.text();
        let payload = {};
        try {
          payload = text ? JSON.parse(text) : {};
        } catch (error) {
          throw new Error(`健康检查返回非 JSON 内容：${text.slice(0, 120)}`);
        }
        if (!response.ok || payload.status !== "ok") {
          throw new Error(payload.msg || `HTTP ${response.status}`);
        }
        ElMessage.success("后端健康检查通过");
      } catch (error) {
        ElMessage.error(`后端健康检查失败：${error.message || error}`);
      }
    },
  },
};
</script>

<style scoped>
.base-url-control {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-left: auto;
  min-width: 0;
}

.base-url-control__label {
  color: var(--text-secondary);
  font-size: 13px;
  white-space: nowrap;
}

.base-url-control__input {
  width: min(38vw, 420px);
}

@media (max-width: 900px) {
  .base-url-control {
    width: 100%;
    flex-wrap: wrap;
    margin-left: 0;
  }

  .base-url-control__input {
    flex: 1 1 220px;
    width: auto;
  }
}
</style>
