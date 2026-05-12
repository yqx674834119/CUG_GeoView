<template>
  <el-container>
    <el-aside width="auto">
      <AsideVue
        :is-collapse="isCollapse"
        :active-index="activeIndex"
      />
    </el-aside>
    <el-container>
      <el-main
        class="main-ctx"
      >
        <el-header class="platform-header">
          <div class="platform-header__inner">
            <button
              class="platform-header__menu"
              type="button"
              @click="goCollapse"
            >
              <i class="icon-menu" />
            </button>
            <Tablogin />
            <BaseUrlControl />
          </div>
        </el-header>
        <router-view v-slot="{ Component }">
          <transition
            name="fade"
            mode="out-in"
          >
            <component :is="Component" />
          </transition>
        </router-view>
        <el-backtop
          target=".main-ctx"
          :bottom="40"
          :visibility-height="50"
          :right="27"
        />
      </el-main>
    </el-container>
  </el-container>
</template>

<script>
import "@/assets/css/app.css";
import AsideVue from "@/components/AsideVue";
import Tablogin from "@/components/Tablogin";
import BaseUrlControl from "@/components/BaseUrlControl.vue";

export default {
  name: "Home",
  components: {
    AsideVue,
    Tablogin,
    BaseUrlControl,
  },
  data() {
    return {
      isCollapse: false,
      scrollTop: "",
      activeIndex: this.$route.path,
    };
  },
  mounted() {
    window.onresize = () => {
      this.isCollapse = document.documentElement.clientWidth <= 1100;
    };
    document.body.style.overflow = "hidden";
  },
  updated(){
    this.activeIndex=this.$route.path
  },
  methods: {
    goCollapse() {
      this.isCollapse = !this.isCollapse;
    },
  }
};
</script>

<style scoped>
.el-main {
  --el-main-padding: 0px 20px 0 20px;
  height: auto;
  width: 100%;
  overflow-x: hidden;
}
.main-ctx {
  height: 100vh;
}
.fade-enter-active,
.fade-leave-active {
  transition: all 0.25s 
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}
.platform-header {
  padding: 0 24px;
  min-height: 72px;
  line-height: 60px;
  background: var(--theme-header-bg);
  border: 1px solid var(--border-color);
  border-radius: 0 0 var(--theme-radius-lg) var(--theme-radius-lg);
  box-shadow: var(--shadow-sm);
  backdrop-filter: blur(14px);
  display: flex;
  align-items: center;
  margin-bottom: 18px;
}

.platform-header__inner {
  display: flex;
  align-items: center;
  gap: 16px;
  width: 100%;
  min-height: 72px;
}

.platform-header__menu {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 44px;
  height: 44px;
  border: 1px solid var(--border-color);
  border-radius: 14px;
  background: var(--theme-surface-elevated);
  color: var(--text-secondary);
  cursor: pointer;
  transition: background-color var(--transition-fast), color var(--transition-fast), border-color var(--transition-fast);
}

.platform-header__menu:hover {
  color: var(--theme-active-color);
  border-color: var(--theme-active-color);
  background: var(--bg-hover);
}

@media (max-width: 768px) {
  .platform-header {
    padding: 0 14px;
  }

  .platform-header__inner {
    gap: 10px;
    flex-wrap: wrap;
    padding: 10px 0;
  }
}
</style>
