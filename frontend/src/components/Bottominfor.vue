<template>
  <el-header height="60px">
    <el-row>
      <el-col
        :xs="12"
        :sm="12"
        :md="16"
        :lg="16"
        :xl="16"
        class="hidden-sm-and-down"
        style="margin-left:30px"
      />
      <el-col
        :xs="24"
        :sm="24"
        :md="8"
        :lg="4"
        :xl="4"
        style="margin-left:30px"
      >
        更多说明请点击 <a @click="goGithub">项目主页<i
          class="iconfont icon-dianji1"
        /></a>
      </el-col>
    </el-row>
  </el-header>
</template>

<script>

export default {
  name: "Bottominfor",
  methods:{
    goGithub(){
      window.open('https://github.com/PaddleCV-SIG/cugrs');
    }

  }
};
</script>

<style scoped>
.el-header {
  margin-top: 30px;
  line-height: 60px;
  position: relative;
  left: -37px;
  width: 120%;
  color: var(--text-muted);
  font-size: 15px;
  overflow: hidden;
}
a{
  color: var(--theme-active-color);
  cursor: pointer;
  transition: all .4s;
}
a:hover{
  color: var(--theme-major-color);
}
</style>
