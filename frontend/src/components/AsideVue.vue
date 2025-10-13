<template>
  <el-menu
    class="el-menu-vertical-demo"
    :collapse="isCollapse"
    text-color="black"
    background-color="rgb(247,246,242)"
    :default-active="activeIndex"
    active-text-color="#FFFFFF"
  >
    <div class="platform">
      <img
        class="platform-logo"
        :src="require('@/assets/image/logo/80.png')"
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
  goHistory
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
    // goOnlineMap 已删除
    goShow() {
      this.$message.success('欢迎使用智能遥感解译系统')
    }
  },
};
</script>

<style lang="less">
.el-menu {
  position: relative;
  height: 100vh;
  top: 0;
  bottom: 0;
  text-align: center;
  font-family: Microsoft JhengHei UI, sans-serif;

  .el-menu-item {
    padding: 0 0;
    border-radius: 10px;
    position: relative;
    color: rgb(117, 117, 117);
    z-index: 1;
    h3 {
      padding-right: 30px;
      width: 100%;
      margin: 0 auto;
      .iconfont {
        font-weight: normal;
        margin-right: 5px;
      }
    }
  }
  .el-menu-item:hover {
    background-color: rgb(247, 246, 242);
    color: #ecf4ff !important;
  }

  .el-menu-item :hover::after {
    width: 100%;
    background: var(--theme--color);
  }
  .el-menu-item ::after {
    position: absolute;
    content: "";
    width: 0;
    height: 100%;
    top: 0;
    left: 0;
    border-radius: 10px;
    transition: 0.25s;
    z-index: -1;
  }
}
.el-menu-vertical-demo:not(.el-menu--collapse) {
  width: 250px;
  min-height: 400px;
}

.is-active {
  background-color: var(--theme--color);
  h3,i{
    color:rgb(247, 246, 242)!important;
  }
}

.platform {
  padding-top: 14px;
  text-align: center;
  color: var(--theme--color);
  height: 80px;
  width: auto;
  overflow: hidden;

  .platform-logo {
    color: var(--theme--color);
  }

  .platform-title {
    color: var(--theme--color);
    font-family: Microsoft JhengHei UI, sans-serif;
    font-size: 21px;
  }
}

.divider-title {
  display: block;
  line-height: 24.4px;
  overflow: hidden;
  width: 70px;
  color: rgb(140, 157, 182)
}

#platform-title {
  position: relative;
  font-size: 20px;
  font-weight: 1000;
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
  background-color: rgb(247,246,242);
}
</style>
 
 