<template>
  <section class="not-found">
    <div class="not-found__ambient">
      <span
        v-for="index in 12"
        :key="index"
        class="not-found__orb"
        :style="orbStyle(index)"
      />
    </div>

    <div class="not-found__card">
      <div class="not-found__badge">
        页面未找到
      </div>
      <h1 class="not-found__code">
        404
      </h1>
      <h2 class="not-found__title">
        当前地址不存在或已被移动
      </h2>
      <p class="not-found__copy">
        你访问的页面不在当前导航结构中。可以返回首页继续使用系统，或回到上一页重新选择功能区。
      </p>
      <div class="not-found__actions">
        <el-button
          type="primary"
          class="btn-animate btn-animate__shiny"
          @click="goHome"
        >
          返回首页
        </el-button>
        <el-button
          class="not-found__secondary"
          @click="goBack"
        >
          返回上一页
        </el-button>
      </div>
    </div>
  </section>
</template>

<script>
export default {
  name: "Notfound",
  methods: {
    goBack() {
      this.$router.go(-1);
    },
    goHome() {
      this.$router.push("/detectchanges");
    },
    orbStyle(index) {
      const positions = [
        { top: "12%", left: "10%", size: "120px", delay: "0s" },
        { top: "18%", left: "72%", size: "84px", delay: "1.2s" },
        { top: "64%", left: "12%", size: "92px", delay: "1.8s" },
        { top: "72%", left: "72%", size: "116px", delay: "0.6s" },
        { top: "8%", left: "42%", size: "64px", delay: "0.9s" },
        { top: "52%", left: "82%", size: "70px", delay: "1.4s" },
      ];
      const item = positions[index % positions.length];
      return {
        top: item.top,
        left: item.left,
        width: item.size,
        height: item.size,
        animationDelay: item.delay,
      };
    },
  },
};
</script>

<style scoped>
.not-found {
  position: relative;
  min-height: 100vh;
  padding: 40px 20px;
  display: grid;
  place-items: center;
  overflow: hidden;
  background:
    radial-gradient(circle at top, rgba(255, 255, 255, 0.22), transparent 30%),
    linear-gradient(180deg, var(--theme-body-bg-strong) 0%, var(--bg-primary) 100%);
}

.not-found__ambient {
  position: absolute;
  inset: 0;
  pointer-events: none;
}

.not-found__orb {
  position: absolute;
  border-radius: 999px;
  background: radial-gradient(circle, rgba(255, 255, 255, 0.38) 0%, rgba(255, 255, 255, 0.06) 62%, transparent 100%);
  filter: blur(2px);
  animation: drift 8s ease-in-out infinite alternate;
}

.not-found__card {
  position: relative;
  width: min(100%, 720px);
  padding: 42px 38px;
  border-radius: 32px;
  border: 1px solid var(--border-color);
  background: var(--theme-card-bg);
  box-shadow: var(--shadow-xl);
  backdrop-filter: blur(18px);
  text-align: center;
}

.not-found__badge {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 120px;
  padding: 8px 16px;
  border-radius: 999px;
  background: var(--theme-tag-bg);
  color: var(--theme-active-color);
  font-size: var(--font-size-tips);
  line-height: var(--line-height-tips);
  font-weight: 700;
}

.not-found__code {
  margin: 18px 0 8px;
  font-family: var(--theme-display-fontfamily);
  font-size: clamp(88px, 18vw, 168px);
  line-height: 1;
  letter-spacing: 0.06em;
  color: var(--theme-heading-color);
  text-shadow: 0 20px 40px rgba(0, 37, 89, 0.18);
}

.not-found__title {
  margin: 0 0 14px;
  font-size: clamp(24px, 4vw, 34px);
  line-height: 1.35;
  color: var(--text-primary);
}

.not-found__copy {
  max-width: 520px;
  margin: 0 auto;
  font-size: var(--font-size-h3);
  line-height: 28px;
  color: var(--text-secondary);
}

.not-found__actions {
  display: flex;
  justify-content: center;
  gap: 14px;
  flex-wrap: wrap;
  margin-top: 28px;
}

.not-found__secondary {
  min-width: 116px;
  height: 42px;
}

@keyframes drift {
  from {
    transform: translate3d(0, 0, 0) scale(1);
  }

  to {
    transform: translate3d(10px, -16px, 0) scale(1.08);
  }
}

@media (max-width: 768px) {
  .not-found__card {
    padding: 32px 22px;
  }

  .not-found__title {
    font-size: 22px;
  }

  .not-found__copy {
    font-size: 15px;
  }
}
</style>
