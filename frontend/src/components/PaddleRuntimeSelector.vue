<template>
  <div
    v-if="visible"
    class="paddle-runtime-selector"
  >
    <span class="paddle-runtime-selector__label">推理设备</span>
    <el-radio-group
      :model-value="modelValue"
      size="small"
      @update:modelValue="onChange"
    >
      <el-radio-button label="gpu">
        GPU
      </el-radio-button>
      <el-radio-button label="cpu">
        CPU
      </el-radio-button>
    </el-radio-group>
  </div>
</template>

<script>
export default {
  name: "PaddleRuntimeSelector",
  props: {
    modelValue: {
      type: String,
      default: "gpu",
    },
    modelPath: {
      type: String,
      default: "",
    },
    models: {
      type: Array,
      default: () => [],
    },
  },
  computed: {
    selectedModel() {
      return this.models.find((item) => item.model_path === this.modelPath) || null;
    },
    isPaddleModel() {
      const model = this.selectedModel || {};
      const backend = String(model.backend || "").toLowerCase();
      const path = String(model.model_path || this.modelPath || "").toLowerCase();
      const name = String(model.model_name || "").toLowerCase();
      return backend === "paddle"
        || path.includes("/paddle")
        || path.includes("bit_256x256")
        || name.includes("paddle")
        || name.includes("通用遥感目标识别")
        || name.includes("高精度地物分类")
        || name.includes("建筑物变化");
    },
    visible() {
      return this.isPaddleModel;
    },
  },
  methods: {
    onChange(value) {
      this.$emit("update:modelValue", value);
    },
  },
};
</script>

<style scoped>
.paddle-runtime-selector {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-top: 12px;
  flex-wrap: wrap;
}

.paddle-runtime-selector__label {
  font-size: 14px;
  color: var(--text-secondary);
}
</style>
