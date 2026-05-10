<template>
  <div>
    <div class="hint">
      当前浏览功能区：<span v-if="type !== ''">{{ type }}</span><span v-else>全部</span><i
        class="hint-icon"
        :class="{
          'iconfont icon-bianhuajiance': type === '变化检测',
          'iconfont icon-mubiaojiance': type === '目标检测',
          'iconfont icon-erfenleibianhuajiance16px': type === '地物分类',
          'iconfont icon-changjingguanli' : type === '场景分类',
          'iconfont icon-jishu' : type === '影像超分重建',
          'icon-registration': type === '自动配准',
          'icon-tracking': type === '目标跟踪'
        }"
      />
    </div>
    <el-table
      ref="multipleTable"
      :data="tableData"
      @selection-change="handleSelectionChange"
    >
      <el-table-column type="selection" />
      <el-table-column label="日期">
        <template #default="scope">
          <span>{{ scope.row.create_time }}</span>
        </template>
      </el-table-column>
      <el-table-column label="功能区">
        <template #default="scope">
          <span id="sub-title"><i
            :class="{
              'iconfont icon-bianhuajiance': scope.row.type === '变化检测',
              'iconfont icon-mubiaojiance': scope.row.type === '目标检测',
              'iconfont icon-erfenleibianhuajiance16px':
                scope.row.type === '地物分类',
              'iconfont icon-changjingguanli' : scope.row.type === '场景分类',
              'iconfont icon-jishu' : scope.row.type ==='影像超分重建',
              'icon-registration' : scope.row.type === '自动配准',
              'icon-tracking' : scope.row.type === '目标跟踪'
            }"
          />{{ scope.row.type }}
          </span>
        </template>
      </el-table-column>
      <el-table-column label="原图">
        <template #default="scope">
          <div
            v-if="isTrackingVideoInput(scope.row)"
            class="history-thumb history-thumb--video"
            @click="openTrackingSource(scope.row)"
          >
            <img
              :src="previewAsset(scope.row, 'before_img')"
              min-width="70"
              height="70"
              alt="视频封面"
            >
            <span class="history-thumb__badge">视频输入</span>
          </div>
          <img
            v-else
            :src="previewAsset(scope.row, 'before_img')"
            min-width="70"
            height="70"
            alt="原图"
            @click="previewOnePic(scope.row.before_img)"
          >

          <img
            v-if="scope.row.type === '变化检测' || scope.row.type === '自动配准'"
            :src="previewAsset(scope.row, 'before_img1')"
            min-width="70"
            height="70"
            style="margin-left: 20px"
            alt="原图"
            @click="previewOnePic(scope.row.before_img1)"
          >
        </template>
      </el-table-column>
      <el-table-column label="结果图/预测结果">
        <template #default="scope">
          <img
            v-show="scope.row.type !== '场景分类'"
            :src="previewAsset(scope.row, 'after_img')"
            min-width="70"
            height="70"
            alt="结果图"
            @click="previewOnePic(scope.row.after_img)"
          >
          <div v-show="scope.row.type === '场景分类'">
            {{ Object.keys(scope.row.data)[0] }}:
            {{ scope.row.data[(Object.keys(scope.row.data)[0])] }}
          </div>
        </template>
      </el-table-column>

      <el-table-column label="操作">
        <template #default="scope">
          <el-button
            size="default"
            type="danger"
            @click="handleDelete(scope.$index, scope.row)"
          >
            删除
          </el-button>
          <el-button
            v-show="scope.row.type !== '变化检测'&&scope.row.type !=='场景分类'&&scope.row.type !== '自动配准'"
            size="default"
            type="primary"
            @click="previewHistoryRow(scope.row)"
          >
            预览
          </el-button>
          <el-button
            v-show="scope.row.type === '场景分类'"
            size="default"
            type="primary"
            @click="previewOnePic(scope.row.before_img, scope.row.after_img)"
          >
            预览
          </el-button>
          <el-button
            v-show="scope.row.type ==='变化检测' || scope.row.type === '自动配准'"
            size="default"
            type="primary"
            @click="
              previewThreePic(
                scope.row.before_img,
                scope.row.before_img1,
                scope.row.after_img
              )
            "
          >
            预览
          </el-button>
          <el-button
            v-if="scope.row.type === '自动配准' && hasRegistrationAsset(scope.row, 'overlay_path')"
            size="default"
            type="primary"
            @click="previewHistoryAsset(scope.row.data.overlay_path)"
          >
            叠加
          </el-button>
          <el-button
            v-if="scope.row.type === '自动配准' && hasRegistrationAsset(scope.row, 'checkerboard_path')"
            size="default"
            type="primary"
            @click="previewHistoryAsset(scope.row.data.checkerboard_path)"
          >
            棋盘
          </el-button>
          <el-button
            v-if="isTrackingVideoInput(scope.row)"
            size="default"
            type="primary"
            @click="openTrackingSource(scope.row)"
          >
            原视频
          </el-button>
          <el-button
            v-show="scope.row.type === '目标跟踪'"
            size="default"
            type="primary"
            @click="openTrackingVideo(scope.row)"
          >
            视频
          </el-button>
          <el-button
            v-if="scope.row.type === '目标跟踪' && hasTrackingTrajectory(scope.row)"
            size="default"
            type="primary"
            @click="openTrackingTrajectory(scope.row)"
          >
            轨迹
          </el-button>
          <el-button
            v-show="scope.row.type !== '场景分类'"
            size="default"
            type="primary"
            @click="downloadHistoryAsset(scope.row)"
          >
            下载
          </el-button>
        </template>
      </el-table-column>
    </el-table>

    <div
      type="primary"
      class="select-fun-drawer hidden-md-and-down"
      @click="isSelect = true"
    >
      <div class="select-fun-title">
        <span>功能筛选</span>
      </div>
      <div class="select-fun-icon">
        <i class="iconfont icon-shaixuan" />
      </div>
    </div>

    <el-drawer
      v-model="isSelect"
      title="功能区筛选"
      :direction="direction"
      :size="size"
    >
      <el-menu
        class="el-menu-vertical-demo"
      >
        <el-menu-item-group>
          <el-menu-item
            index="1"
            @click="onlyOneFun('变化检测')"
          >
            <h3>
              <i class="iconfont icon-bianhuajiance" />时序变化分析
            </h3>
          </el-menu-item>
          <el-menu-item
            index="2"
            @click="onlyOneFun('目标检测')"
          >
            <h3>
              <i class="iconfont icon-mubiaojiance" />智能目标识别
            </h3>
          </el-menu-item>
          <el-menu-item
            index="3"
            @click="onlyOneFun('地物分类')"
          >
            <h3>
              <i class="iconfont icon-erfenleibianhuajiance16px" />地表覆盖分类
            </h3>
          </el-menu-item>
          <el-menu-item
            index="4"
            @click="onlyOneFun('场景分类')"
          >
            <h3>
              <i class="iconfont icon-changjingguanli" />场景智能识别
            </h3>
          </el-menu-item>
          <el-menu-item
            index="5"
            @click="onlyOneFun('影像超分重建')"
          >
            <h3>
              <i class="iconfont icon-jishu" />影像超分重建
            </h3>
          </el-menu-item>
          <el-menu-item
            index="6"
            @click="onlyOneFun('自动配准')"
          >
            <h3>
              <i class="icon-registration" />多模态自动配准
            </h3>
          </el-menu-item>
          <el-menu-item
            index="7"
            @click="onlyOneFun('目标跟踪')"
          >
            <h3>
              <i class="icon-tracking" />全域目标跟踪
            </h3>
          </el-menu-item>
          <el-menu-item
            index="8"
            @click="onlyOneFun('')"
          >
            <h3><i class="iconfont icon-fuyuan" />列表复原</h3>
          </el-menu-item>
        </el-menu-item-group>
      </el-menu>
    </el-drawer>
    <div
      v-show="tableData.length !== 0"
      style="margin-top: 20px"
    >
      <el-button @click="toggleSelection(tableData)">
        全选
      </el-button>
      <el-button @click="toggleSelection()">
        取消选择
      </el-button>
      <el-button
        type="danger"
        @click="deleteAll()"
      >
        删除
      </el-button>
      <el-button
        type="primary"
        @click="downLoadAll()"
      >
        下载
      </el-button>
    </div>
    <el-row justify="center">
      <el-col
        :xs="24"
        :sm="24"
        :md="10"
        :lg="11"
        :xl="10"
        style="margin-right: 40px"
      >
        <el-pagination
          background
          :page-size="pageSize"
          layout="prev, pager, next, jumper"
          :total="total"
          :current-page="currentPage"
          @size-change="handleSizeChange"
          @current-change="handleCurrentChange"
          @next-click="goNextPage"
          @prev-click="goPrePage"
        />
      </el-col>
    </el-row>

    <el-dialog
      v-model="preVisible"
      :modal="false"
      title="图片预览"
      width="75%"
      fullscreen
      center
    >
      <div v-if="flag === 2">
        <el-row justify="space-evenly">
          <img
            id="pre-img"
            :src="previewPic1"
            alt="预览"
          >
          <img
            id="pre-img"
            :src="previewPic2"
            alt="预览"
          >
        </el-row>
      </div>
      <div v-else-if="flag === 1">
        <el-row justify="space-evenly">
          <img
            id="pre-img"
            :src="previewPic1"
            alt="预览"
          >
        </el-row>
      </div>
      <div v-else-if="flag === 3">
        <el-row justify="space-evenly">
          <img
            id="pre-img"
            :src="previewPic1"
            alt="预览"
          >

          <img
            id="pre-img"
            :src="previewPic3"
            alt="预览"
          >

          <img
            id="pre-img"
            :src="previewPic2"
            alt="预览"
          >
        </el-row>
        <el-row />
      </div>
      <el-row
        type="flex"
        justify="center"
      >
        <el-col :span="1">
          <el-button
            type="primary"
            @click="preVisible = false"
          >
            OK
          </el-button>
        </el-col>
      </el-row>
    </el-dialog>
  </div>
</template>

<script>

import { historyGetPage, historyDelete } from "@/api/history";
import {
  previewOnePic,
  previewTwoPic,
  previewThreePic,
} from "@/utils/preview.js";
import { downloadimgWithWords } from "@/utils/download.js";
import { isBackendPhotoAssetPath, toBackendAssetUrl } from "@/utils/backendAssetUrl";
import { getBackendAssetPreviewDataUrl } from "@/utils/assetPreview";
import { logFrontendDebug } from "@/utils/debugLog";

import global from "@/global.vue";
export default {
  name: "History",
  beforeRouteEnter(to, from, next) {
    next((vm) => {
      document.querySelector(".el-main").scrollTop = 0;
    });
  },
  data() {
    return {
      delete: {
        ids: [],
      },
      type: "",
      isSelect: false,
      direction: "rtl",
      size: "15%",
      pageSize: 10,
      total: 0,
      flag: "",
      currentPage: 1,
      multipleSelection: [],
      preVisible: false,
      previewPic1: "",
      previewPic2: "",
      previewPic3: "",
      tableData: [],
      previewLoadToken: 0,
      previewPlaceholder: "data:image/gif;base64,R0lGODlhAQABAIAAAAAAAP///ywAAAAAAQABAAACAUwAOw==",
      global: {
        BASEURL: global.BASEURL,
      },
    };
  },
  mounted() {
    this.getTabelInfo();
  },
  methods: {
    previewOnePic,
    downloadimgWithWords,
    historyGetPage,
    historyDelete,
    previewTwoPic,
    previewThreePic,
    previewAsset(row, field) {
      if (!row || !row[field]) {
        return this.previewPlaceholder;
      }
      return row[`_${field}_preview`] || this.previewPlaceholder;
    },
    loadHistoryPreviews() {
      const token = this.previewLoadToken + 1;
      this.previewLoadToken = token;
      const fields = ["before_img", "before_img1", "after_img"];

      this.tableData.forEach((row) => {
        fields.forEach((field) => {
          const path = row[field];
          if (!path) {
            return;
          }

          getBackendAssetPreviewDataUrl(path, 420)
            .then((dataUrl) => {
              if (this.previewLoadToken === token) {
                row[`_${field}_preview`] = dataUrl;
              }
            })
            .catch(() => {
              if (this.previewLoadToken === token) {
                row[`_${field}_preview`] = "";
              }
            });
        });
      });
    },
    toAbsoluteUrl(path) {
      if (!path) {
        return "";
      }
      if (path.startsWith("http://") || path.startsWith("https://")) {
        return path;
      }
      return toBackendAssetUrl(path);
    },
    downloadDirect(url, filename) {
      const link = document.createElement("a");
      link.href = url;
      link.download = filename;
      link.click();
    },
    openExternalAsset(path) {
      if (!path) {
        this.$message.warning("未找到可预览的文件");
        return;
      }
      if (isBackendPhotoAssetPath(path)) {
        this.previewOnePic(path);
        return;
      }
      window.open(this.toAbsoluteUrl(path), "_blank", "noopener");
    },
    previewHistoryAsset(path) {
      if (!path) {
        this.$message.warning("未找到可预览的结果文件");
        return;
      }
      this.previewOnePic(path);
    },
    previewHistoryRow(row) {
      this.previewTwoPic(row.before_img, row.after_img);
    },
    hasRegistrationAsset(row, field) {
      return Boolean(row && row.data && row.data[field]);
    },
    isTrackingVideoInput(row) {
      return Boolean(
        row
        && row.type === "目标跟踪"
        && row.data
        && row.data.input_mode === "video"
        && row.data.source_input_path,
      );
    },
    hasTrackingTrajectory(row) {
      return Boolean(row && row.data && row.data.trajectory_path);
    },
    downloadHistoryAsset(row) {
      if (row.type === "目标跟踪" && row.data && row.data.output_video_path) {
        this.downloadDirect(
          this.toAbsoluteUrl(row.data.output_video_path),
          `第${row.id}组目标跟踪结果.mp4`,
        );
        return;
      }
      this.downloadimgWithWords(
        row.id,
        this.toAbsoluteUrl(row.after_img),
        `${row.type}结果图.png`,
      );
    },
    openTrackingTrajectory(row) {
      const trajectoryPath = row.data && row.data.trajectory_path;
      if (!trajectoryPath) {
        this.$message.warning("当前记录没有轨迹 JSON");
        return;
      }
      window.open(this.toAbsoluteUrl(trajectoryPath), "_blank");
    },
    openTrackingVideo(row) {
      const videoPath = row.data && row.data.output_video_path;
      if (!videoPath) {
        this.previewHistoryRow(row);
        return;
      }
      this.openExternalAsset(videoPath);
    },
    openTrackingSource(row) {
      const sourcePath = row.data && row.data.source_input_path;
      if (!sourcePath) {
        this.previewOnePic(row.before_img);
        return;
      }
      this.openExternalAsset(sourcePath);
    },
    handleDelete(index, row) {
      this.$confirm("此操作将永久删除, 是否继续?", "提示", {
        confirmButtonText: "确定",
        cancelButtonText: "取消",
        type: "warning",
      })
        .then(() => {
          this.delete.ids.push(row.id);
          this.historyDelete(this.delete).then((res) => {
            this.tableData.splice(index, 1);
            this.getTabelInfo();
            this.$message({
              type: "success",
              message: "删除成功!",
            });
          }).catch((rej)=>{})
        })
        .catch(() => {
          this.$message({
            type: "info",
            message: "已取消删除",
          });
        });
    },
    deleteAll() {
      if (this.multipleSelection.length === 0) {
        this.$message.warning("请选择要删除的记录哦");
      } else {
        this.$confirm("此操作将永久删除, 是否继续?", "提示", {
          confirmButtonText: "确定",
          cancelButtonText: "取消",
          type: "warning",
        })
          .then(() => {
            this.delete.ids = this.multipleSelection.map((item) => {
              return item.id;
            });

            this.historyDelete(this.delete).then((res) => {
              this.getTabelInfo();
              this.tableData = this.tableData.filter((item) => {
                return this.multipleSelection.every((item2) => {
                  return item.id !== item2.id;
                });
              })
              this.$message({
                type: "success",
                message: "删除成功!",
              });
            }).catch((rej)=>{})
          })
          .catch(() => {
            this.$message({
              type: "info",
              message: "已取消删除",
            });
          });
      }
    },
    downLoadAll() {
      if (this.multipleSelection.length === 0) {
        this.$message.warning("请选择要下载的历史记录的图片哦");
      } else {
        for (let item of this.multipleSelection) {
          this.downloadHistoryAsset(item);
        }
      }
    },
    toggleSelection(rows) {
      if (rows) {
        rows.forEach((row) => {
          this.$refs.multipleTable.toggleRowSelection(row);
        });
      } else {
        this.$refs.multipleTable.clearSelection();
      }
    },
    handleSelectionChange(val) {
      this.multipleSelection = val;
    },
    handleSizeChange(val) {
      this.pageSize = val;
      this.getTabelInfo();
    },
    handleCurrentChange(val) {
      this.page = val;
      this.currentPage = val;

      this.getTabelInfo();
    },
    getTabelInfo() {
      logFrontendDebug("历史记录页面", "准备请求历史记录列表", {
        page: this.currentPage,
        limit: 10,
        type: this.type || "全部",
        backendBaseUrl: this.global.BASEURL,
      }, { always: true });
      this.historyGetPage(this.currentPage, 10, this.type).then((res) => {
        this.total = res.data.count;
        this.tableData = res.data.data;
        logFrontendDebug("历史记录页面", "历史记录列表返回成功", {
          page: this.currentPage,
          type: this.type || "全部",
          total: this.total,
          returned: this.tableData.length,
          sampleTypes: this.tableData.slice(0, 5).map((item) => item.type),
          sampleIds: this.tableData.slice(0, 5).map((item) => item.id),
        }, { always: true });
        this.loadHistoryPreviews();
      }).catch((error)=>{
        logFrontendDebug("历史记录页面", "历史记录列表请求失败", {
          page: this.currentPage,
          type: this.type || "全部",
          message: error?.message || String(error),
          status: error?.response?.status,
          response: error?.response?.data || null,
        }, { error: true, always: true });
      })
    },
    goNextPage() {
      this.getTabelInfo();
    },
    goPrePage() {
      this.getTabelInfo();
    },
    onlyOneFun(funName){
      this.type = funName
      this.getTabelInfo()
      this.isSelect = false
    },
  },
};
</script>

<style lang="less" scoped>
.hint {
  font-size: 18px;
  margin: 10px 0;
  color: var(--text-secondary);
}
.hint-icon {
  margin-left: 8px;
  font-size: 20px;
}
#sub-title {
  font-size: 16px;
  .iconfont {
    margin-right: 8px;
  }
}

#sub-title:hover:after {
  left: 0%;
  right: 0%;
  width: 100%;
}

.history-thumb {
  position: relative;
  display: inline-flex;
  cursor: pointer;
}

.history-thumb__badge {
  position: absolute;
  right: 4px;
  bottom: 4px;
  padding: 2px 6px;
  border-radius: 999px;
  font-size: 12px;
  color: #fff;
  background: rgba(0, 0, 0, 0.72);
}

.select-fun-drawer {
  position: fixed;
  z-index: 100;
  background: var(--theme-surface-elevated);
  color: var(--text-primary);
  top: 250px;
  right: 0;
  width: 34px;
  height: 120px;
  padding: 0.5rem;
  border-top-left-radius: 0.2rem;
  border-bottom-left-radius: 0.2rem;
  box-shadow: -12px 0 28px rgba(0, 0, 0, 0.14);
  transition: all 0.1s ease-in-out;
  cursor: pointer;
  .select-fun-title {
    font-size: 17px;
    font-weight: 1000;
    -webkit-writing-mode: vertical-rl;
    writing-mode: vertical-rl;
    color: var(--theme-active-color);
    background: var(--theme-tag-bg);
    padding: 0.12rem;
    border-radius: 0.2rem;
    height: 80px;
    text-align: center;
    width: 33px;
    span {
      display: block;
      padding-right: 6px;
      color: var(--theme-danger-color); 
    }
  }
  .select-fun-icon {
    width: 37px;
    text-align: center;
    margin-top: 6px;
    color: var(--theme-active-color);
    background: var(--theme-tag-bg);
    border-radius: 0.2rem;
    height: 30px;
    .iconfont {
      display: block;
      padding-top: 5px;
    }
  }
}
.select-fun-title:hover,
.select-fun-icon:hover {
  background-color: var(--bg-hover);
}
.el-menu {
  width: 100%;
}

</style>
