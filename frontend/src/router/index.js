import { createRouter, createWebHistory } from 'vue-router'

const Home = () => import('@/views/Home.vue')
const DetectChanges = () => import('@/views/mainfun/DetectChanges.vue')
const DetectObjects = () => import('@/views/mainfun/DetectObjects.vue')
const Segmentation = () => import('@/views/mainfun/Segmentation.vue')
const Classification = ()=> import('@/views/mainfun/Classification')
const RestoreImgs = ()=> import('@/views/mainfun/RestoreImgs')
// 在线地图模块已删除
const History = () => import('@/views/history/History.vue')
const NotFound = () => import('@/views/NotFound.vue')
const routes = [
  {
    path: '/',
    redirect: '/detectchanges'
  },
  {
    path: '/home',
    name: 'Home',
    component: Home,
    children: [
      {
        path: '/detectchanges',
        name: 'Detectchanges',
        component: DetectChanges,

      }, {
        path: '/detectobjects',
        name: 'Detectobjects',
        component: DetectObjects
      },  {
        path: '/segmentation',
        name: 'Segmentation',
        component: Segmentation
      },
      {
        path: '/classification',
        name:'Classification',
        component:Classification
      },
      {
        path:'/restoreimgs',
        name:'Restoreimgs',
        component:RestoreImgs
      },
      {
        path: '/history',
        name: 'history',
        component: History,
      }
      // 在线地图路由已删除
    ]
  },
  {
    path: "/:pathMatch(.*)*",
    name: 'notfound',
    component: NotFound
  }
]

const router = createRouter({
  history: createWebHistory(process.env.BASE_URL),
  routes,
})
export default router
