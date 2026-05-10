import { createApp } from 'vue'
import ElementPlus from 'element-plus'
import 'element-plus/dist/index.css'
import App from './App.vue'
import router from './router'
import { initializeTheme } from '@/utils/theme'
import { installAssetImageInterceptor } from '@/utils/assetDomInterceptor'
import { runStartupDiagnostics } from '@/utils/startupDiagnostics'
import global from '@/global'
import { logFrontendDebug } from '@/utils/debugLog'

import '@/assets/font/iconfont.css'
import './assets/css/normalize.css'
import '@/assets/css/app.css'
import '@/assets/css/font.css'
import 'element-plus/theme-chalk/display.css'
import 'animate.css';

import JSZIP from "jszip"
import zhCn from 'element-plus/es/locale/lang/zh-cn'

initializeTheme()
installAssetImageInterceptor()
logFrontendDebug("前端启动", "Vue 应用开始初始化", {
  page: window.location.href,
  backendBaseUrl: global.BASEURL,
  backendAssetMode: global.BACKEND_ASSET_MODE,
  frontendAssetDebug: global.FRONTEND_ASSET_DEBUG,
  runtimeConfig: window.__GEOVIEW_RUNTIME_CONFIG__ || {},
  userAgent: window.navigator.userAgent,
}, { always: true })

const RESIZE_OBSERVER_NOISE = "ResizeObserver loop completed with undelivered notifications."

window.addEventListener("error", (event) => {
  if (event?.message === RESIZE_OBSERVER_NOISE) {
    event.stopImmediatePropagation()
  }
})

window.addEventListener("unhandledrejection", (event) => {
  const reason = event?.reason
  const message = typeof reason === "string" ? reason : reason?.message
  if (message === RESIZE_OBSERVER_NOISE) {
    event.preventDefault()
  }
})

const app = createApp(App)
app.use(router).use(ElementPlus,{locale: zhCn}).use(JSZIP).mount('#app')
router.isReady().then(() => {
  logFrontendDebug("前端启动", "路由就绪，开始执行启动诊断", {
    route: router.currentRoute.value.fullPath,
    backendBaseUrl: global.BASEURL,
  }, { always: true })
  runStartupDiagnostics()
})
app.directive('drag',{
    mounted(el, binding, vnode, prevVnode) {
        const mouseDown = (e) => {
            let X = e.clientX - el.offsetLeft
            let Y = e.clientY - el.offsetTop
            const mouseMove = (e) => {
                el.style.left = e.clientX - X + 'px'
                el.style.top = e.clientY - Y + 'px'
            }
            document.addEventListener('mousemove', mouseMove)
            document.addEventListener('mouseup', () => {
                document.removeEventListener('mousemove', mouseMove)
            })
        }
        el.addEventListener('mousedown', mouseDown)
    },
})
