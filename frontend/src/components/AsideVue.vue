<template>
  <el-menu
    class="el-menu-vertical-demo geo-aside-menu"
    :collapse="isCollapse"
    :default-active="activeIndex"
  >
    <div class="platform">
      <img
        class="platform-logo"
        :src="require('@/assets/image/logo/80.svg')"
        alt="logo"
        @click="goDetectChanges"
      >
      <div
        v-if="!isCollapse"
        id="platform-title"
      >
        <a
          class="platform-title"
          @click="goShow"
        >智能遥感解译系统</a>
      </div>
    </div>
    <el-divider content-position="center">
      <span
        v-show="!isCollapse"
        class="divider-title"
      >分析工具</span>
    </el-divider>
    <el-menu-item
      index="/detectchanges"
      @click="goDetectChanges"
    >
      <i
        v-show="isCollapse"
        class="icon-change-detect"
      />
      <h3 v-show="!isCollapse">
        <i class="icon-change-detect" />时序变化分析
      </h3>
    </el-menu-item>

    <el-menu-item
      index="/detectobjects"
      @click="goDetectObjects"
    >
      <i
        v-show="isCollapse"
        class="icon-object-detect"
      />
      <h3 v-show="!isCollapse">
        <i class="icon-object-detect" />智能目标识别
      </h3>
    </el-menu-item>

    <el-menu-item
      index="/segmentation"
      @click="goSegmentation"
    >
      <i
        v-show="isCollapse"
        class="icon-classification"
      />
      <h3 v-show="!isCollapse">
        <i class="icon-classification" />地表覆盖分类
      </h3>
    </el-menu-item>

    <el-menu-item
      index="/classification"
      @click="goClassification"
    >
      <i
        v-show="isCollapse"
        class="icon-scene-class"
      />
      <h3 v-show="!isCollapse">
        <i class="icon-scene-class" />场景智能识别
      </h3>
    </el-menu-item>

    <el-menu-item
      index="/restoreimgs"
      @click="goRestoreImgs"
    >
      <i
        v-show="isCollapse"
        class="icon-enhance"
      />
      <h3 v-show="!isCollapse">
        <i class="icon-enhance" />影像超分重建
      </h3>
    </el-menu-item>

    <el-menu-item
      index="/registration"
      @click="goRegistration"
    >
      <i
        v-show="isCollapse"
        class="icon-registration" 
      />
      <h3 v-show="!isCollapse">
        <i class="icon-registration" />多模态自动配准
      </h3>
    </el-menu-item>

    <el-menu-item
      index="/tracking"
      @click="goTracking"
    >
      <i
        v-show="isCollapse"
        class="icon-tracking"
      />
      <h3 v-show="!isCollapse">
        <i class="icon-tracking" />全域目标跟踪
      </h3>
    </el-menu-item>

    <!-- 在线地图菜单项已删除 -->

    <el-divider content-position="center">
      <span
        v-show="!isCollapse"
        class="divider-title"
      >历史记录</span>
    </el-divider>

    <el-menu-item
      index="/history"
      @click="goHistory"
    >
      <i
        v-show="isCollapse"
        class="icon-history-new"
      />
      <h3 v-show="!isCollapse">
        <i class="icon-history-new" />分析历史记录
      </h3>
    </el-menu-item>

    <el-divider content-position="center">
      <span
        v-show="!isCollapse"
        class="divider-title"
      />
    </el-divider>
  </el-menu>
</template>

<script>
import {
  goDetectChanges,
  goDetectObjects,
  goSegmentation,
  goClassification,
  goRestoreImgs,
  goHistory,
  goRegistration,
  goTracking
} from "@/utils/gosomewhere.js";
// goOnlineMap 已删除
export default {
  props: {
    isCollapse: {
      type: Boolean,
      default: false
    },
    activeIndex: {
      type: String,
      default: '/detectchanges'
    }
  },
  methods: {
    goDetectChanges,
    goDetectObjects,
    goSegmentation,
    goClassification,
    goRestoreImgs,
    goHistory,
    goRegistration,
    goTracking,
    // goOnlineMap 已删除
    goShow() {
      this.$message.success('欢迎使用智能遥感解译系统')
    }
  },
};
</script>

<style lang="less">
.geo-aside-menu {
  position: relative;
  height: 100vh;
  top: 0;
  bottom: 0;
  text-align: center;
  background: var(--theme-sidebar-bg) !important;
  border-right: 1px solid var(--border-color) !important;
  box-shadow: 18px 0 32px rgba(7, 31, 63, 0.08);

  .el-menu-item {
    margin: 6px 12px;
    min-height: 50px;
    border-radius: 16px;
    position: relative;
    color: var(--text-secondary);
    z-index: 1;
    transition: transform var(--transition-fast), color var(--transition-fast), background-color var(--transition-fast);
    h3 {
      display: flex;
      align-items: center;
      justify-content: flex-start;
      gap: 10px;
      padding-right: 18px;
      width: 100%;
      margin: 0 auto;
      font-size: var(--font-size-h3);
      font-weight: 600;
      .iconfont {
        font-weight: normal;
      }
    }
  }

  .el-menu-item:hover {
    background-color: var(--bg-hover);
    color: var(--theme-active-color) !important;
    transform: translateX(2px);
  }

  .el-menu-item :hover::after {
    width: 100%;
    background: linear-gradient(135deg, var(--theme-major-color), var(--theme-active-color));
  }

  .el-menu-item ::after {
    position: absolute;
    content: "";
    width: 0;
    height: 100%;
    top: 0;
    left: 0;
    border-radius: 16px;
    transition: 0.25s;
    z-index: -1;
  }
}

.el-menu-vertical-demo:not(.el-menu--collapse) {
  width: 250px;
  min-height: 400px;
}

.is-active {
  background: linear-gradient(135deg, var(--theme-major-color), var(--primary-hover));
  h3,i{
    color: var(--text-inverse) !important;
  }
}

.platform {
  padding-top: 18px;
  text-align: center;
  color: var(--theme-active-color);
  height: 108px;
  width: auto;
  overflow: hidden;

  .platform-logo {
    width: 58px;
    height: 58px;
    padding: 8px;
    border-radius: 18px;
    background: rgba(255, 255, 255, 0.68);
    box-shadow: var(--shadow-sm);
  }

  .platform-title {
    color: var(--theme-heading-color);
    font-family: var(--theme-display-fontfamily);
    font-size: 22px;
    letter-spacing: 0.04em;
  }
}

.divider-title {
  display: block;
  line-height: 24.4px;
  overflow: hidden;
  width: 70px;
  color: var(--text-muted);
}

#platform-title {
  position: relative;
  font-size: 20px;
  font-weight: 800;
  cursor: pointer;
}

#platform-title::after {
  content: "";
  width: 0;
  height: 3px;
  background: var(--theme--color);
  position: absolute;
  top: 100%;
  left: 50%;
  right: 50%;
  transition: all 0.5s;
}

#platform-title:hover:after {
  left: 7%;
  right: 7%;
  width: 85%;
}
.el-menu .el-divider__text{
  background-color: transparent;
}
</style>
 
 
