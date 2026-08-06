<template>
  <div class="museum page-container">
    <div class="page-header">
      <div>
        <h1 class="page-title">非遗数字博物馆</h1>
        <p class="page-subtitle">探索无锡丰富的非物质文化遗产</p>
      </div>
    </div>

    <div class="toolbar">
      <div class="search-bar">
        <el-input
          v-model="searchKeyword"
          placeholder="搜索展品..."
          prefix-icon="Search"
          @keyup.enter="handleSearch"
          clearable
        />
        <el-button type="primary" @click="handleSearch">搜索</el-button>
      </div>

      <div class="filter-section">
        <el-select v-model="selectedCategory" placeholder="分类筛选" style="width: 150px;">
          <el-option label="全部" value="" />
          <el-option label="惠山泥人" value="huishan" />
          <el-option label="锡绣" value="xixiu" />
          <el-option label="紫砂陶艺" value="zisha" />
          <el-option label="吴歌" value="wuge" />
          <el-option label="其他" value="other" />
        </el-select>

        <el-select v-model="sortBy" placeholder="排序方式" style="width: 120px;">
          <el-option label="默认排序" value="default" />
          <el-option label="按收藏数" value="favorites" />
          <el-option label="按浏览量" value="views" />
        </el-select>
      </div>
    </div>

    <div class="museum-main">
      <div class="categories-sidebar">
        <div class="sidebar-card">
          <h3><el-icon><Grid /></el-icon> 展品分类</h3>
          <div class="category-list">
            <span
              v-for="cat in categories"
              :key="cat.value"
              :class="{ active: selectedCategory === cat.value }"
              @click="selectedCategory = cat.value"
            >
              {{ cat.label }}
            </span>
          </div>
        </div>

        <div class="sidebar-card">
          <h3><el-icon><Star /></el-icon> 热门收藏</h3>
          <div class="favorite-list">
            <div v-for="item in favoriteItems" :key="item.id" class="favorite-item" @click="viewDetail(item)">
              <span class="favorite-icon">{{ item.icon }}</span>
              <div class="favorite-info">
                <span class="favorite-name">{{ item.name }}</span>
                <span class="favorite-count">{{ item.favorites }} 收藏</span>
              </div>
            </div>
          </div>
        </div>

        <div class="sidebar-card">
          <h3><el-icon><Document /></el-icon> 非遗知识</h3>
          <div class="knowledge-list">
            <div v-for="(item, idx) in knowledgeItems" :key="idx" class="knowledge-item">
              <span class="knowledge-title">{{ item.title }}</span>
              <span class="knowledge-desc">{{ item.desc }}</span>
            </div>
          </div>
        </div>
      </div>

      <div class="museum-content">
        <div v-if="filteredItems.length === 0" class="empty-state">
          <el-icon size="64" color="#ccc"><Box /></el-icon>
          <p>没有找到相关展品</p>
        </div>
        <div v-else class="museum-grid">
          <div class="museum-card" v-for="item in filteredItems" :key="item.id" @click="viewDetail(item)">
            <div class="museum-icon-wrapper">
              <div class="museum-icon">{{ item.icon }}</div>
              <div class="museum-category">{{ getCategoryName(item.category) }}</div>
            </div>
            <h3 class="museum-name">{{ item.name }}</h3>
            <p class="museum-description">{{ item.description }}</p>
            <div class="museum-stats">
              <span>
                <el-icon><Star /></el-icon>
                {{ item.favorites }}
              </span>
              <span>
                <el-icon><Picture /></el-icon>
                {{ item.views }}
              </span>
            </div>
            <button class="btn-view">查看详情</button>
          </div>
        </div>
      </div>
    </div>

    <div class="scene-container" ref="sceneContainer">
      <div class="scene-info" v-if="!currentItem">
        <el-icon size="48" color="#999"><Mouse /></el-icon>
        <p>点击上方展品查看3D模型</p>
        <p class="scene-tip">支持鼠标拖拽旋转，滚轮缩放</p>
      </div>
      <div class="scene-info" v-else-if="loading">
        <el-icon size="32" color="#4a90a4" class="loading-icon"><Loading /></el-icon>
        <p>正在加载 {{ currentItem.name }} 的3D模型...</p>
      </div>
      <div class="scene-info error" v-else-if="error">
        <el-icon size="48" color="#e74c3c"><Warning /></el-icon>
        <p>{{ error }}</p>
        <p class="hint">当前为演示模式，展示默认3D模型</p>
      </div>
    </div>

    <el-dialog title="展品详情" v-model="showDetailDialog" width="750px" top="30px">
      <div v-if="selectedExhibit" class="exhibit-detail">
        <div class="detail-header">
          <div class="detail-icon-wrapper">
            <div class="detail-icon">{{ selectedExhibit.icon }}</div>
          </div>
          <div class="detail-title-area">
            <h3>{{ selectedExhibit.name }}</h3>
            <span class="detail-category">{{ getCategoryName(selectedExhibit.category) }}</span>
          </div>
          <el-button
            @click="toggleFavorite(selectedExhibit)"
            :type="selectedExhibit.isFavorited ? 'danger' : 'default'"
            size="small"
            icon="Star"
            :circle="true"
          />
        </div>

        <div class="detail-content">
          <div class="detail-info">
            <div class="info-section">
              <h4><el-icon><DocIcon /></el-icon> 简介</h4>
              <p>{{ selectedExhibit.description }}</p>
            </div>

            <div class="info-section">
              <h4><el-icon><Clock /></el-icon> 历史渊源</h4>
              <p>{{ selectedExhibit.history }}</p>
            </div>

            <div class="info-section">
              <h4><el-icon><Brush /></el-icon> 艺术特点</h4>
              <ul>
                <li v-for="(feature, idx) in selectedExhibit.features" :key="idx">{{ feature }}</li>
              </ul>
            </div>

            <div class="info-section">
              <h4><el-icon><Avatar /></el-icon> 传承现状</h4>
              <p>{{ selectedExhibit.heritage }}</p>
            </div>
          </div>

          <div class="detail-stats-panel">
            <div class="stat-item">
              <el-icon><Star /></el-icon>
              <span class="stat-value">{{ selectedExhibit.favorites }}</span>
              <span class="stat-label">收藏数</span>
            </div>
            <div class="stat-item">
              <el-icon><Picture /></el-icon>
              <span class="stat-value">{{ selectedExhibit.views }}</span>
              <span class="stat-label">浏览量</span>
            </div>
            <div class="stat-item">
              <el-icon><Calendar /></el-icon>
              <span class="stat-value">{{ selectedExhibit.year }}</span>
              <span class="stat-label">入选年份</span>
            </div>
          </div>
        </div>
      </div>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, computed, onUnmounted } from 'vue'
import { ElMessage } from 'element-plus'
import { Search, Grid, Star, Picture, Box, Document, Mouse, Loading, Warning, Document as DocIcon, Clock, Brush, Avatar, Calendar } from '@element-plus/icons-vue'
import * as THREE from 'three'
import { GLTFLoader } from 'three/examples/jsm/loaders/GLTFLoader'
import { OrbitControls } from 'three/examples/jsm/controls/OrbitControls'

const categories = [
  { label: '全部', value: '' },
  { label: '惠山泥人', value: 'huishan' },
  { label: '锡绣', value: 'xixiu' },
  { label: '紫砂陶艺', value: 'zisha' },
  { label: '吴歌', value: 'wuge' },
  { label: '其他', value: 'other' }
]

const knowledgeItems = [
  { title: '非遗是什么?', desc: '非物质文化遗产的简称' },
  { title: '无锡有多少非遗?', desc: '国家级非遗20+项' },
  { title: '如何传承非遗?', desc: '数字化保护与创新' }
]

const culturalItems = ref([
  {
    id: 1,
    name: '惠山泥人',
    description: '无锡传统泥塑艺术的代表，以其独特的造型和鲜艳的色彩著称',
    history: '惠山泥人起源于明代，距今已有400多年的历史。最初是民间艺人在惠山脚下制作的小型泥塑，后来逐渐发展成为具有地方特色的工艺品。',
    features: ['造型夸张生动', '色彩鲜艳明快', '题材丰富多样', '兼具观赏与收藏价值'],
    heritage: '2006年被列入第一批国家级非物质文化遗产名录，目前有多位国家级和省级传承人致力于技艺传承。',
    modelPath: '/models/huishan.glb',
    icon: '🗿',
    category: 'huishan',
    favorites: 342,
    views: 1256,
    year: '2006',
    isFavorited: false
  },
  {
    id: 2,
    name: '锡绣',
    description: '精美细腻的刺绣工艺，以其独特的针法和精美的图案闻名',
    history: '锡绣起源于宋代，明清时期达到鼎盛。无锡作为江南刺绣的重要产地，锡绣以其精细的针法和独特的风格著称于世。',
    features: ['针法细腻繁复', '图案精美典雅', '色彩柔和协调', '注重写实表现'],
    heritage: '2008年被列入第二批国家级非物质文化遗产名录，现有传承人致力于传统技艺的保护与创新。',
    modelPath: '/models/xixiu.glb',
    icon: '🧵',
    category: 'xixiu',
    favorites: 256,
    views: 890,
    year: '2008',
    isFavorited: true
  },
  {
    id: 3,
    name: '宜兴紫砂',
    description: '闻名遐迩的紫砂陶艺，以其独特的材质和精湛的工艺著称',
    history: '紫砂陶艺始于北宋，盛于明清。宜兴紫砂以其独特的泥料和精湛的手工技艺，成为中国传统工艺品中的瑰宝。',
    features: ['泥料独特珍贵', '造型古朴典雅', '工艺精湛考究', '泡茶效果极佳'],
    heritage: '2006年被列入第一批国家级非物质文化遗产名录，紫砂技艺传承至今已有千年历史。',
    modelPath: '/models/zisha.glb',
    icon: '🍵',
    category: 'zisha',
    favorites: 423,
    views: 1567,
    year: '2006',
    isFavorited: false
  },
  {
    id: 4,
    name: '吴歌',
    description: '江南水乡的传统民歌，以其婉转悠扬的旋律著称',
    history: '吴歌是江南地区的传统民歌，历史悠久，最早可追溯到春秋时期。吴歌以其婉转悠扬的旋律和朴实真挚的歌词，反映了江南人民的生活和情感。',
    features: ['旋律婉转悠扬', '歌词朴实真挚', '地域特色鲜明', '兼具叙事与抒情'],
    heritage: '2006年被列入第一批国家级非物质文化遗产名录，近年来通过各种形式的传承活动得到了有效的保护和弘扬。',
    modelPath: '/models/wuge.glb',
    icon: '🎤',
    category: 'wuge',
    favorites: 189,
    views: 678,
    year: '2006',
    isFavorited: false
  },
  {
    id: 5,
    name: '精微绣',
    description: '极其精细的刺绣技艺，是锡绣中的珍品',
    history: '精微绣是锡绣中的一种特殊技艺，起源于清代。它以其极其精细的针法和微小的画面，展现了刺绣艺术的极致境界。',
    features: ['针法极其精细', '画面小巧玲珑', '题材包罗万象', '艺术价值极高'],
    heritage: '作为锡绣的重要组成部分，精微绣技艺得到了很好的传承和发展，多次获得国内外大奖。',
    modelPath: '/models/jingwei.glb',
    icon: '🎨',
    category: 'xixiu',
    favorites: 167,
    views: 543,
    year: '2008',
    isFavorited: false
  },
  {
    id: 6,
    name: '无锡纸马',
    description: '传统民俗工艺品，用于祭祀和装饰',
    history: '无锡纸马是一种传统的民俗工艺品，起源于明代。它以木刻版画的形式制作，用于民间祭祀和装饰。',
    features: ['线条简洁流畅', '色彩鲜明对比', '题材吉祥喜庆', '民俗内涵丰富'],
    heritage: '作为无锡地区的传统民俗文化，纸马制作技艺得到了有效保护，成为研究江南民俗文化的重要资料。',
    modelPath: '/models/zhima.glb',
    icon: '📜',
    category: 'other',
    favorites: 123,
    views: 389,
    year: '2011',
    isFavorited: false
  },
  {
    id: 7,
    name: '无锡留青竹刻',
    description: '独特的竹刻艺术，以留青技法著称',
    history: '留青竹刻是一种独特的竹刻艺术，起源于唐代，明清时期在无锡得到了极大发展。它以保留竹子表面的青筠为特点，雕刻出精美的图案。',
    features: ['技法独特精湛', '图案层次分明', '风格清新典雅', '兼具实用性与艺术性'],
    heritage: '2008年被列入第二批国家级非物质文化遗产名录，现有多位传承人致力于这门技艺的传承。',
    modelPath: '/models/zhuke.glb',
    icon: '🪵',
    category: 'other',
    favorites: 145,
    views: 456,
    year: '2008',
    isFavorited: false
  },
  {
    id: 8,
    name: '无锡泥塑',
    description: '惠山泥人的姊妹艺术，风格古朴自然',
    history: '无锡泥塑与惠山泥人同源，但其风格更加古朴自然，注重表现生活场景和人物神态。',
    features: ['风格古朴自然', '造型生动传神', '注重生活气息', '具有浓郁的乡土风情'],
    heritage: '作为无锡地区的传统民间艺术，无锡泥塑在现代得到了新的发展，创作出许多具有时代特色的作品。',
    modelPath: '/models/nisu.glb',
    icon: '🏺',
    category: 'huishan',
    favorites: 98,
    views: 278,
    year: '2014',
    isFavorited: false
  }
])

const sceneContainer = ref(null)
const loading = ref(false)
const error = ref(null)
const currentItem = ref(null)
const showDetailDialog = ref(false)
const selectedExhibit = ref(null)

const searchKeyword = ref('')
const selectedCategory = ref('')
const sortBy = ref('default')

let scene = null
let camera = null
let renderer = null
let controls = null
let animationId = null

const filteredItems = computed(() => {
  let result = [...culturalItems.value]
  if (searchKeyword.value) {
    const keyword = searchKeyword.value.toLowerCase()
    result = result.filter(item =>
      item.name.toLowerCase().includes(keyword) ||
      item.description.toLowerCase().includes(keyword)
    )
  }
  if (selectedCategory.value) {
    result = result.filter(item => item.category === selectedCategory.value)
  }
  switch (sortBy.value) {
    case 'favorites':
      result.sort((a, b) => b.favorites - a.favorites)
      break
    case 'views':
      result.sort((a, b) => b.views - a.views)
      break
  }
  return result
})

const favoriteItems = computed(() => {
  return [...culturalItems.value].sort((a, b) => b.favorites - a.favorites).slice(0, 5)
})

const getCategoryName = (category) => {
  const cat = categories.find(c => c.value === category)
  return cat ? cat.label : '其他'
}

const handleSearch = () => {
  showDetailDialog.value = false
}

const cleanup = () => {
  if (animationId) {
    cancelAnimationFrame(animationId)
  }
  if (controls) {
    controls.dispose()
  }
  if (renderer) {
    renderer.dispose()
    sceneContainer.value.innerHTML = ''
  }
  scene = null
  camera = null
  renderer = null
}

const createScene = () => {
  const container = sceneContainer.value
  if (!container) return

  const width = container.clientWidth
  const height = container.clientHeight

  scene = new THREE.Scene()
  scene.background = new THREE.Color(0xf8f6f0)

  camera = new THREE.PerspectiveCamera(45, width / height, 0.1, 1000)
  camera.position.set(0, 2, 8)
  camera.lookAt(0, 0, 0)

  renderer = new THREE.WebGLRenderer({ antialias: true })
  renderer.setSize(width, height)
  renderer.setPixelRatio(window.devicePixelRatio)
  renderer.shadowMap.enabled = true
  container.appendChild(renderer.domElement)

  controls = new OrbitControls(camera, renderer.domElement)
  controls.enableDamping = true
  controls.dampingFactor = 0.05
  controls.target.set(0, 1, 0)

  const ambientLight = new THREE.AmbientLight(0xffffff, 0.6)
  scene.add(ambientLight)

  const directionalLight = new THREE.DirectionalLight(0xffffff, 0.8)
  directionalLight.position.set(10, 10, 5)
  directionalLight.castShadow = true
  scene.add(directionalLight)

  const fillLight = new THREE.PointLight(0x4a90a4, 0.3)
  fillLight.position.set(-5, 3, 5)
  scene.add(fillLight)

  const gridHelper = new THREE.GridHelper(10, 10, 0xcccccc, 0xeeeeee)
  gridHelper.position.y = 0
  scene.add(gridHelper)
}

const createPlaceholderModel = () => {
  const group = new THREE.Group()

  const baseGeo = new THREE.CylinderGeometry(2, 2, 0.2, 32)
  const baseMat = new THREE.MeshStandardMaterial({
    color: 0x8b6914,
    roughness: 0.4,
    metalness: 0.1
  })
  const base = new THREE.Mesh(baseGeo, baseMat)
  base.position.y = 0.1
  base.receiveShadow = true
  group.add(base)

  const boxGeo = new THREE.BoxGeometry(1.5, 2, 1.5)
  const boxMat = new THREE.MeshStandardMaterial({
    color: 0x4a90a4,
    roughness: 0.3,
    metalness: 0.2,
    emissive: 0x2d6172,
    emissiveIntensity: 0.2
  })
  const box = new THREE.Mesh(boxGeo, boxMat)
  box.position.y = 1.2
  box.castShadow = true
  box.receiveShadow = true
  group.add(box)

  const sphereGeo = new THREE.SphereGeometry(0.6, 32, 32)
  const sphereMat = new THREE.MeshStandardMaterial({
    color: 0xc7693d,
    roughness: 0.2,
    metalness: 0.1,
    emissive: 0x8b4513,
    emissiveIntensity: 0.3
  })
  const sphere = new THREE.Mesh(sphereGeo, sphereMat)
  sphere.position.y = 2.8
  sphere.castShadow = true
  group.add(sphere)

  scene.add(group)
  return group
}

const loadModel = async (modelPath) => {
  cleanup()
  loading.value = true
  error.value = null

  createScene()

  let placeholderModel = null

  try {
    const loader = new GLTFLoader()

    await new Promise((resolve, reject) => {
      loader.load(
        modelPath,
        (gltf) => {
          const model = gltf.scene
          model.scale.set(0.5, 0.5, 0.5)
          model.position.set(0, 0, 0)
          model.traverse((child) => {
            if (child.isMesh) {
              child.castShadow = true
              child.receiveShadow = true
            }
          })
          scene.add(model)
          loading.value = false
          resolve()
        },
        undefined,
        (err) => {
          reject(err)
        }
      )
    })
  } catch (err) {
    error.value = `模型加载失败: ${err.message || '文件不存在或格式错误'}`
    loading.value = false
    placeholderModel = createPlaceholderModel()
  }

  const animate = () => {
    animationId = requestAnimationFrame(animate)
    if (placeholderModel) {
      placeholderModel.rotation.y += 0.005
    }
    if (controls) {
      controls.update()
    }
    if (renderer && scene && camera) {
      renderer.render(scene, camera)
    }
  }
  animate()
}

const viewDetail = (item) => {
  currentItem.value = item
  selectedExhibit.value = item
  item.views++
  showDetailDialog.value = true
  loadModel(item.modelPath)
}

const toggleFavorite = (item) => {
  item.isFavorited = !item.isFavorited
  item.favorites += item.isFavorited ? 1 : -1
  ElMessage.success(item.isFavorited ? '收藏成功' : '取消收藏')
}

onUnmounted(() => {
  cleanup()
})
</script>

<style scoped>
.museum {
  max-width: 1280px;
}

.page-header {
  margin-bottom: 30px;
}

.page-title {
  font-size: 2rem;
  font-weight: 700;
  color: #2c3e50;
  margin: 0;
}

.page-subtitle {
  font-size: 1rem;
  color: #666;
  margin: 8px 0 0;
}

.toolbar {
  padding: 16px 20px;
}

.search-bar .el-input {
  width: 350px;
}

.museum-main {
  display: flex;
  gap: 24px;
}

.categories-sidebar {
  width: 240px;
  flex-shrink: 0;
}

.sidebar-card {
  background: white;
  border-radius: 16px;
  padding: 20px;
  margin-bottom: 20px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.06);
}

.sidebar-card h3 {
  margin: 0 0 16px;
  font-size: 1rem;
  font-weight: 600;
  color: #2c3e50;
  display: flex;
  align-items: center;
  gap: 8px;
}

.category-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.category-list span {
  padding: 10px 14px;
  background: #f5f5f5;
  border-radius: 10px;
  font-size: 0.9rem;
  cursor: pointer;
  transition: all 0.2s;
  color: #666;
  text-align: left;
}

.category-list span:hover, .category-list span.active {
  background: #4a90a4;
  color: white;
}

.favorite-list {
  list-style: none;
  padding: 0;
  margin: 0;
}

.favorite-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 0;
  border-bottom: 1px dashed #eee;
  cursor: pointer;
  transition: background 0.2s;
}

.favorite-item:last-child {
  border-bottom: none;
}

.favorite-item:hover {
  background: #f9f9f9;
}

.favorite-icon {
  font-size: 1.5rem;
}

.favorite-info {
  flex: 1;
  display: flex;
  flex-direction: column;
}

.favorite-name {
  font-size: 0.9rem;
  color: #333;
}

.favorite-count {
  font-size: 0.75rem;
  color: #999;
}

.knowledge-list {
  list-style: none;
  padding: 0;
  margin: 0;
}

.knowledge-item {
  padding: 12px 0;
  border-bottom: 1px dashed #eee;
}

.knowledge-item:last-child {
  border-bottom: none;
}

.knowledge-title {
  display: block;
  font-size: 0.9rem;
  color: #333;
  font-weight: 500;
}

.knowledge-desc {
  display: block;
  font-size: 0.8rem;
  color: #999;
}

.museum-content {
  flex: 1;
}

.empty-state {
  text-align: center;
  padding: 60px 20px;
  background: white;
  border-radius: 16px;
}

.empty-state p {
  margin: 16px 0;
  color: #999;
}

.museum-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(260px, 1fr));
  gap: 20px;
}

.museum-card {
  background: white;
  border-radius: 16px;
  padding: 24px;
  text-align: center;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.06);
  cursor: pointer;
  transition: all 0.3s ease;
}

.museum-card:hover {
  transform: translateY(-6px);
  box-shadow: 0 12px 28px rgba(0, 0, 0, 0.12);
}

.museum-icon-wrapper {
  position: relative;
  margin-bottom: 16px;
}

.museum-icon {
  font-size: 4rem;
}

.museum-category {
  position: absolute;
  top: -5px;
  right: 10px;
  padding: 4px 12px;
  background: #4a90a4;
  color: white;
  font-size: 0.75rem;
  border-radius: 15px;
}

.museum-name {
  font-size: 1.15rem;
  font-weight: 600;
  color: #2c3e50;
  margin: 0 0 10px;
}

.museum-description {
  color: #666;
  font-size: 0.9rem;
  margin: 0 0 16px;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
  line-height: 1.6;
}

.museum-stats {
  display: flex;
  justify-content: center;
  gap: 30px;
  color: #888;
  font-size: 0.85rem;
  margin-bottom: 16px;
}

.btn-view {
  padding: 10px 24px;
  background: linear-gradient(135deg, #4a90a4, #2d6172);
  color: white;
  border: none;
  border-radius: 20px;
  cursor: pointer;
  font-weight: 500;
  font-size: 0.9rem;
  transition: all 0.2s;
}

.btn-view:hover {
  transform: scale(1.05);
}

.scene-container {
  margin-top: 30px;
  width: 100%;
  height: 500px;
  background: white;
  border-radius: 16px;
  box-shadow: 0 4px 15px rgba(0, 0, 0, 0.08);
  position: relative;
  overflow: hidden;
}

.scene-info {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  text-align: center;
  color: #666;
}

.scene-info.error {
  color: #e74c3c;
}

.scene-tip {
  font-size: 0.85rem;
  color: #999;
  margin-top: 10px !important;
}

.loading-icon {
  animation: spin 1s linear infinite;
}

@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

.exhibit-detail {
  text-align: left;
}

.detail-header {
  display: flex;
  align-items: center;
  gap: 20px;
  margin-bottom: 20px;
  padding-bottom: 20px;
  border-bottom: 1px solid #eee;
}

.detail-icon-wrapper {
  width: 80px;
  height: 80px;
  border-radius: 16px;
  background: linear-gradient(135deg, #f5f7fa 0%, #e4e8ec 100%);
  display: flex;
  align-items: center;
  justify-content: center;
}

.detail-icon {
  font-size: 2.5rem;
}

.detail-title-area {
  flex: 1;
}

.detail-title-area h3 {
  font-size: 1.5rem;
  font-weight: 700;
  color: #2c3e50;
  margin: 0 0 8px;
}

.detail-category {
  padding: 6px 16px;
  background: #4a90a4;
  color: white;
  border-radius: 20px;
  font-size: 0.85rem;
}

.detail-content {
  display: flex;
  gap: 30px;
}

.detail-info {
  flex: 1;
}

.info-section {
  margin-bottom: 20px;
}

.info-section h4 {
  font-size: 1rem;
  font-weight: 600;
  color: #2c3e50;
  margin: 0 0 10px;
  display: flex;
  align-items: center;
  gap: 8px;
}

.info-section p {
  color: #666;
  line-height: 1.7;
  margin: 0;
}

.info-section ul {
  list-style: none;
  padding: 0;
  margin: 0;
}

.info-section li {
  padding: 8px 0;
  color: #666;
  position: relative;
  padding-left: 20px;
}

.info-section li::before {
  content: '•';
  position: absolute;
  left: 0;
  color: #4a90a4;
  font-size: 1.2rem;
}

.detail-stats-panel {
  width: 200px;
  flex-shrink: 0;
}

.stat-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 20px 15px;
  background: #f9f9f9;
  border-radius: 12px;
  margin-bottom: 15px;
}

.stat-item:last-child {
  margin-bottom: 0;
}

.stat-item .el-icon {
  font-size: 24px;
  color: #4a90a4;
  margin-bottom: 10px;
}

.stat-value {
  font-size: 1.8rem;
  font-weight: 700;
  color: #2c3e50;
}

.stat-label {
  font-size: 0.85rem;
  color: #999;
  margin-top: 5px;
}

@media (max-width: 992px) {
  .museum-main {
    flex-direction: column;
  }

  .categories-sidebar {
    width: 100%;
  }

  .category-list {
    flex-direction: row;
    flex-wrap: wrap;
  }

  .search-bar .el-input {
    width: 100%;
  }

  .toolbar {
    flex-direction: column;
    gap: 16px;
  }

  .detail-content {
    flex-direction: column;
  }

  .detail-stats-panel {
    width: 100%;
    display: flex;
    gap: 15px;
  }

  .stat-item {
    flex: 1;
    margin-bottom: 0;
  }
}
</style>
