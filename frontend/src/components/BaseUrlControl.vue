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
    <span class="base-url-control__label">包</span>
    <el-input-number
      v-model="draftChunkSize"
      class="base-url-control__chunk"
      size="small"
      :min="1024"
      :max="262144"
      :step="10240"
      controls-position="right"
      @change="saveChunkSize"
    />
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
      draftChunkSize: global.RESULT_CHUNK_SIZE || 65536,
    };
  },
  methods: {
    save() {
      const nextUrl = global.setBackendBaseUrl(this.draftUrl);
      this.draftUrl = nextUrl;
      this.saveChunkSize(false);
      ElMessage.success("后端地址已更新");
    },
    saveChunkSize(showMessage = true) {
      const nextSize = global.setResultChunkSize(this.draftChunkSize);
      this.draftChunkSize = nextSize;
      if (showMessage !== false) {
        ElMessage.success(`传输分片大小已更新：${nextSize} bytes`);
      }
    },
    async checkHealth() {
      this.save();
      const baseUrl = String(global.BASEURL || "").replace(/\/+$/, "");
      try {
        const sizes = [1024];
        for (let size = 10 * 1024; size <= 200 * 1024; size += 10 * 1024) {
          sizes.push(size);
        }
        let stableSize = 0;
        console.groupCollapsed("[GeoView][health-probe] backend payload size probe");
        for (const size of sizes) {
          const startedAt = performance.now();
          const response = await fetch(`${baseUrl}/health?payload_size=${size}`, {
            headers: { Accept: "application/json" },
          });
          const text = await response.text();
          let payload = {};
          try {
            payload = text ? JSON.parse(text) : {};
          } catch (error) {
            throw new Error(`健康检查返回非 JSON 内容：${text.slice(0, 120)}`);
          }
          const accepted = response.ok && payload.status === "ok" && payload.probe?.payload?.length === size;
          console.info("[GeoView][health-probe]", {
            requested_bytes: size,
            response_bytes: text.length,
            accepted,
            duration_ms: Math.round(performance.now() - startedAt),
          });
          if (!accepted) {
            break;
          }
          stableSize = size;
        }
        console.info("[GeoView][health-probe] stable max bytes", stableSize);
        console.groupEnd();
        if (!stableSize) {
          throw new Error("未找到稳定可接收的响应包大小");
        }
        this.draftChunkSize = stableSize;
        this.saveChunkSize(false);
        ElMessage.success(`后端健康检查通过，稳定包大小 ${stableSize} bytes`);
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

.base-url-control__chunk {
  width: 150px;
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
