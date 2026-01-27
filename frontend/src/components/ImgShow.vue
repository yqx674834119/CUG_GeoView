<template>
  <el-card style="margin-bottom: 10px">
    <el-empty
      v-if="childImgArr.length === 0"
      :image-size="200"
    />
    <div class="img-display-box">
      <div
        v-for="(item,index) in childImgArr"
        :key="index"
        class="img-display-item"
      >
        <el-divider class="img-divider">
          第<span class="index-number">{{ item.id }}</span>组
        </el-divider>
        <div>
          <el-image
            ref="tableTab"
            class="img-display"
            :src="item.before_img"
            :fit="fit"
            :lazy="true"
            :preview-src-list="[item.before_img]"
            :preview-teleported="true"
          />
         
          <div class="img-infor">
            <span>原图</span>
          </div>
        </div>
        <div>
          <div v-if="item.type!=='场景分类'">
            <div style="display: flex;">
              <div>
                <el-image
                  ref="tableTab"
                  class="img-display"
                  :src="item.after_img"
                  :fit="fit"
                  :lazy="true"
                  :preview-src-list="[item.after_img]"
                  :preview-teleported="true"
                />
                <div class="img-infor">
                  <span>预测结果</span>
                  <span
                    @click="
                      downloadimgWithWords(
                        item.id,
                        item.after_img,
                        `${item.type}结果图.png`
                      )
                    "
                  ><i class="iconfont icon-xiazai" /></span>
                </div>
              </div>
              
              <!-- 地物分类图例 -->
              <div v-if="item.type === '地物分类'" style="margin-left: 20px; display: flex; flex-direction: column; justify-content: center;">
                <h4>类别图例</h4>
                <!-- DeepLabV3P (Paddle) Legend -->
                <div v-if="!item.after_img.includes('pred_')" style="font-size: 14px; line-height: 1.8;">
                   <div style="display: flex; align-items: center;"><span style="width: 20px; height: 20px; background-color: rgb(0, 0, 0); margin-right: 8px; border: 1px solid #ccc;"></span> <span>云 (Cloud)</span></div>
                   <div style="display: flex; align-items: center;"><span style="width: 20px; height: 20px; background-color: rgb(128, 0, 0); margin-right: 8px;"></span> <span>阴影 (Shadow)</span></div>
                   <div style="display: flex; align-items: center;"><span style="width: 20px; height: 20px; background-color: rgb(0, 128, 0); margin-right: 8px;"></span> <span>雪 (Snow)</span></div>
                   <div style="display: flex; align-items: center;"><span style="width: 20px; height: 20px; background-color: rgb(128, 128, 0); margin-right: 8px;"></span> <span>水体 (Water)</span></div>
                   <div style="display: flex; align-items: center;"><span style="width: 20px; height: 20px; background-color: rgb(0, 0, 128); margin-right: 8px;"></span> <span>陆地 (Land)</span></div>
                </div>
                <!-- MMSegmentation (CUGRS) Legend -->
                <div v-else style="font-size: 14px; line-height: 1.8;">
                   <div style="display: flex; align-items: center;"><span style="width: 20px; height: 20px; background-color: rgb(0, 255, 0); margin-right: 8px;"></span> <span>草地 (Grassland)</span></div>
                   <div style="display: flex; align-items: center;"><span style="width: 20px; height: 20px; background-color: rgb(0, 128, 0); margin-right: 8px;"></span> <span>林地 (Forest)</span></div>
                   <div style="display: flex; align-items: center;"><span style="width: 20px; height: 20px; background-color: rgb(255, 0, 0); margin-right: 8px;"></span> <span>建筑 (Building)</span></div>
                   <div style="display: flex; align-items: center;"><span style="width: 20px; height: 20px; background-color: rgb(255, 255, 0); margin-right: 8px;"></span> <span>道路 (Road)</span></div>
                   <div style="display: flex; align-items: center;"><span style="width: 20px; height: 20px; background-color: rgb(255, 0, 255); margin-right: 8px;"></span> <span>裸地 (Bareground)</span></div>
                   <div style="display: flex; align-items: center;"><span style="width: 20px; height: 20px; background-color: rgb(0, 191, 255); margin-right: 8px;"></span> <span>水体 (Water)</span></div>
                </div>
              </div>
            </div>
          </div>
          <div
            v-else
            class="img-index"
          >
            <span class="index-number ">{{ Object.keys(item.data)[0] }}: {{ item.data[Object.keys(item.data)] }}</span>
          </div>
        </div>
      </div>
    </div>
  </el-card>
</template>

<script>
import { downloadimgWithWords } from "@/utils/download.js";

export default {
  name: "Imgshow",
  props: {
    imgArr:{
      type:Array,
      default(){
        return []
      }
    },
  },
  data() {
    return {
      fit: "fill",
      childImgArr:[]
    };
  },
  mounted() {
    this.childImgArr = this.imgArr
  },
  updated() {
    this.childImgArr = this.imgArr
  },
  methods: {
    downloadimgWithWords,
  },
};
</script>

<style scoped lang="less">
* {
  font-family: SimHei sans-serif;
}
.index-number {
  font-family: Yu Gothic Medium;
  font-style: oblique;
  font-size: 30px;
  margin-left: 5px;
  margin-right: 10px;
}
.img-infor {
  text-align: center;
  font-size: 18px;
  margin-top: 5px;
  margin-bottom: 10px;
  height: 30px;
  line-height: 30px;
  font-weight: 500;
  font-family: Microsoft JhengHei UI, sans-serif;
}
.img-display-box{
  display: flex;
  flex-direction: column;
  .img-display-item{
    display: flex;
    flex-direction: row;
    justify-content: space-evenly;
    flex-wrap: wrap;
    .img-index{
      line-height: 21rem;
    }
  .img-display{
    width:21rem;
    height: 21rem;
  }
    .img-divider{
      align-items: center;
    }
  }
}
.el-divider /deep/{
  background-color: white;
}
</style>