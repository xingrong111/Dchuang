<template>
  <div class="ai-workshop">
    <div class="content-wrapper">
      <div class="left-panel">
        <div class="parts-panel">
          <h3><el-icon><Box /></el-icon> 零件组件</h3>
          <div class="parts-grid">
            <div
              v-for="part in parts"
              :key="part.id"
              class="part-item"
              draggable="true"
              @dragstart="onDragStart(part, $event)"
              @dragend="onDragEnd"
            >
              <div class="part-icon" :style="{ backgroundColor: part.color }">
                {{ part.icon }}
              </div>
              <p>{{ part.name }}</p>
            </div>
          </div>
        </div>

        <div class="params-panel">
          <h3><el-icon><Setting /></el-icon> 参数调整</h3>
          <el-form :model="modelParams" label-width="80px">
            <el-form-item label="缩放">
              <el-slider v-model="modelParams.scale" :min="0.1" :max="3" :step="0.1" />
              <span class="param-value">{{ modelParams.scale.toFixed(1) }}</span>
            </el-form-item>
            <el-form-item label="旋转X">
              <el-slider v-model="modelParams.rotation.x" :min="0" :max="360" />
              <span class="param-value">{{ modelParams.rotation.x }}°</span>
            </el-form-item>
            <el-form-item label="旋转Y">
              <el-slider v-model="modelParams.rotation.y" :min="0" :max="360" />
              <span class="param-value">{{ modelParams.rotation.y }}°</span>
            </el-form-item>
            <el-form-item label="旋转Z">
              <el-slider v-model="modelParams.rotation.z" :min="0" :max="360" />
              <span class="param-value">{{ modelParams.rotation.z }}°</span>
            </el-form-item>
            <el-form-item label="颜色">
              <el-color-picker v-model="modelParams.color" show-alpha />
            </el-form-item>
          </el-form>
        </div>

        <div class="actions-panel">
          <h3><el-icon><EditPen /></el-icon> 操作</h3>
          <el-button @click="resetCamera" class="action-btn">
            <el-icon><RefreshLeft /></el-icon>
            重置视角
          </el-button>
          <el-button @click="clearModels" class="action-btn">
            <el-icon><Delete /></el-icon>
            清空模型
          </el-button>
          <el-button @click="generateAI" class="action-btn ai-btn" :loading="isGenerating">
            <el-icon><MagicStick /></el-icon>
            AI生成
          </el-button>
          <el-button @click="exportModel" class="action-btn primary-btn">
            <el-icon><Download /></el-icon>
            导出模型
          </el-button>
        </div>
      </div>

      <div class="canvas-container" ref="canvasContainer">
        <div class="canvas-overlay" v-if="isGenerating">
          <div class="generating-modal">
            <div class="loading-spinner">
              <el-icon :size="48" color="#4a90a4"><Loading /></el-icon>
            </div>
            <h4>AI正在生成中...</h4>
            <el-progress :percentage="generateProgress" :stroke-width="10" />
            <p>{{ generateStatus }}</p>
          </div>
        </div>
        <div class="canvas-hint">
          <span>🖱️ 拖动旋转 | 滚轮缩放</span>
        </div>
      </div>
    </div>

    <el-dialog title="AI生成设置" v-model="showGenerateDialog" width="500px">
      <el-form :model="generateForm" label-width="100px">
        <el-form-item label="生成类型">
          <el-select v-model="generateForm.type" placeholder="请选择">
            <el-option label="惠山泥人风格" value="huishan" />
            <el-option label="锡绣风格" value="xixiu" />
            <el-option label="紫砂风格" value="zisha" />
            <el-option label="自定义风格" value="custom" />
          </el-select>
        </el-form-item>
        <el-form-item label="主题描述">
          <el-input v-model="generateForm.prompt" type="textarea" :rows="3" placeholder="描述你想生成的作品..." />
        </el-form-item>
        <el-form-item label="细节程度">
          <el-slider v-model="generateForm.detail" :min="1" :max="5" :step="1" :marks="{ 1: '低', 3: '中', 5: '高' }" />
        </el-form-item>
        <el-form-item label="颜色偏好">
          <el-color-picker v-model="generateForm.color" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showGenerateDialog = false">取消</el-button>
        <el-button type="primary" @click="startGeneration" :disabled="!generateForm.type">开始生成</el-button>
      </template>
    </el-dialog>

    <el-dialog title="导出模型" v-model="showExportDialog" width="400px">
      <div class="export-options">
        <p>选择导出格式：</p>
        <div class="format-list">
          <div class="format-item" @click="selectedFormat = 'glb'">
            <el-icon :size="32"><Folder /></el-icon>
            <span>GLB格式</span>
            <span class="format-desc">通用3D模型格式</span>
          </div>
          <div class="format-item" @click="selectedFormat = 'obj'">
            <el-icon :size="32"><Folder /></el-icon>
            <span>OBJ格式</span>
            <span class="format-desc">多平台兼容</span>
          </div>
          <div class="format-item" @click="selectedFormat = 'png'">
            <el-icon :size="32"><Picture /></el-icon>
            <span>PNG图片</span>
            <span class="format-desc">高清截图</span>
          </div>
        </div>
      </div>
      <template #footer>
        <el-button @click="showExportDialog = false">取消</el-button>
        <el-button type="primary" @click="confirmExport">确认导出</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, onUnmounted } from 'vue'
import { ElMessage, ElProgress } from 'element-plus'
import { Box, Setting, EditPen, RefreshLeft, Delete, MagicStick, Download, Loading, Folder, Picture } from '@element-plus/icons-vue'
import * as THREE from 'three'
import { OrbitControls } from 'three/examples/jsm/controls/OrbitControls'

const parts = [
  { id: 1, name: '头部', icon: '🧠', color: '#ff6b6b' },
  { id: 2, name: '身体', icon: '👕', color: '#4ecdc4' },
  { id: 3, name: '手臂', icon: '💪', color: '#45b7d1' },
  { id: 4, name: '腿部', icon: '🦵', color: '#96ceb4' },
]

const canvasContainer = ref(null)
const showGenerateDialog = ref(false)
const showExportDialog = ref(false)
const isGenerating = ref(false)
const generateProgress = ref(0)
const generateStatus = ref('')
const selectedFormat = ref('glb')

const modelParams = reactive({
  scale: 1,
  rotation: { x: 0, y: 0, z: 0 },
  color: '#4a90e2'
})

const generateForm = reactive({
  type: '',
  prompt: '',
  detail: 3,
  color: '#4a90e2'
})

let scene = null
let camera = null
let renderer = null
let controls = null
let platform = null
let placedModels = []
let animationId = null

const cleanup = () => {
  if (animationId) {
    cancelAnimationFrame(animationId)
  }
  if (controls) {
    controls.dispose()
  }
  if (renderer) {
    renderer.dispose()
    canvasContainer.value.innerHTML = ''
  }
  scene = null
  camera = null
  renderer = null
}

const initScene = () => {
  const container = canvasContainer.value
  if (!container) return

  const width = container.clientWidth
  const height = container.clientHeight

  scene = new THREE.Scene()
  scene.background = new THREE.Color(0x111827)

  camera = new THREE.PerspectiveCamera(45, width / height, 0.1, 1000)
  camera.position.set(5, 5, 10)
  camera.lookAt(0, 1, 0)

  renderer = new THREE.WebGLRenderer({ antialias: true })
  renderer.setSize(width, height)
  renderer.setPixelRatio(window.devicePixelRatio)
  renderer.shadowMap.enabled = true
  renderer.shadowMap.type = THREE.PCFSoftShadowMap
  container.appendChild(renderer.domElement)

  controls = new OrbitControls(camera, renderer.domElement)
  controls.enableDamping = true
  controls.dampingFactor = 0.05
  controls.autoRotate = true
  controls.autoRotateSpeed = 1.0
  controls.enableZoom = true
  controls.maxPolarAngle = Math.PI / 2
  controls.target.set(0, 1, 0)

  addLights()
  createPlatform()
  addEnvironment()
  addSampleModels()
  animate()
}

const addLights = () => {
  const ambientLight = new THREE.AmbientLight(0x404060)
  scene.add(ambientLight)

  const mainLight = new THREE.DirectionalLight(0xffffff, 1.2)
  mainLight.position.set(5, 10, 7)
  mainLight.castShadow = true
  mainLight.receiveShadow = true
  mainLight.shadow.mapSize.width = 1024
  mainLight.shadow.mapSize.height = 1024
  mainLight.shadow.camera.near = 0.5
  mainLight.shadow.camera.far = 25
  mainLight.shadow.camera.left = -10
  mainLight.shadow.camera.right = 10
  mainLight.shadow.camera.top = 10
  mainLight.shadow.camera.bottom = -10
  scene.add(mainLight)

  const backLight = new THREE.PointLight(0x4466ff, 0.3)
  backLight.position.set(-3, 2, -4)
  scene.add(backLight)

  const fillLight = new THREE.PointLight(0xffaa44, 0.3)
  fillLight.position.set(4, 3, 5)
  scene.add(fillLight)
}

const createPlatform = () => {
  const platformGroup = new THREE.Group()

  const diskGeo = new THREE.CylinderGeometry(4, 4, 0.2, 64)
  const diskMat = new THREE.MeshStandardMaterial({
    color: 0x2d3748,
    roughness: 0.4,
    metalness: 0.1,
    transparent: true,
    opacity: 0.9
  })
  const disk = new THREE.Mesh(diskGeo, diskMat)
  disk.position.y = 0
  disk.receiveShadow = true
  disk.castShadow = true
  platformGroup.add(disk)

  const gridHelper = new THREE.GridHelper(8, 16, 0x4a90e2, 0x2c3e50)
  gridHelper.position.y = 0.11
  gridHelper.material.opacity = 0.3
  gridHelper.material.transparent = true
  platformGroup.add(gridHelper)

  const ringGeo = new THREE.TorusGeometry(4.1, 0.05, 16, 100)
  const ringMat = new THREE.MeshStandardMaterial({
    color: 0x4a90e2,
    emissive: 0x1a3650,
    emissiveIntensity: 0.5
  })
  const ring = new THREE.Mesh(ringGeo, ringMat)
  ring.rotation.x = Math.PI / 2
  ring.position.y = 0.15
  platformGroup.add(ring)

  const centerGeo = new THREE.CylinderGeometry(0.3, 0.3, 0.05, 16)
  const centerMat = new THREE.MeshStandardMaterial({
    color: 0x4a90e2,
    emissive: 0x1a3650,
    emissiveIntensity: 0.8
  })
  const center = new THREE.Mesh(centerGeo, centerMat)
  center.position.y = 0.16
  platformGroup.add(center)

  platform = platformGroup
  scene.add(platformGroup)
}

const addSampleModels = () => {
  const colors = [0xff6b6b, 0x4ecdc4, 0x45b7d1, 0x96ceb4]
  const positions = [
    { x: -2, z: -2 },
    { x: 2, z: -2 },
    { x: -2, z: 2 },
    { x: 2, z: 2 }
  ]

  positions.forEach((pos, index) => {
    const geometry = new THREE.BoxGeometry(0.8, 0.8, 0.8)
    const material = new THREE.MeshStandardMaterial({
      color: colors[index],
      roughness: 0.3,
      metalness: 0.1,
      emissive: 0x000000
    })
    const cube = new THREE.Mesh(geometry, material)
    cube.position.set(pos.x, 0.5, pos.z)
    cube.castShadow = true
    cube.receiveShadow = true

    const edges = new THREE.EdgesGeometry(geometry)
    const line = new THREE.LineSegments(edges, new THREE.LineBasicMaterial({ color: 0xffffff }))
    cube.add(line)

    scene.add(cube)
    placedModels.push(cube)
  })
}

const addEnvironment = () => {
  const particleCount = 200
  const particleGeo = new THREE.BufferGeometry()
  const particlePositions = new Float32Array(particleCount * 3)

  for (let i = 0; i < particleCount * 3; i += 3) {
    particlePositions[i] = (Math.random() - 0.5) * 30
    particlePositions[i+1] = (Math.random() - 0.5) * 20
    particlePositions[i+2] = (Math.random() - 0.5) * 30
  }

  particleGeo.setAttribute('position', new THREE.BufferAttribute(particlePositions, 3))

  const particleMat = new THREE.PointsMaterial({
    color: 0x4a90e2,
    size: 0.05,
    transparent: true,
    opacity: 0.3
  })

  const particles = new THREE.Points(particleGeo, particleMat)
  scene.add(particles)
}

const animate = () => {
  animationId = requestAnimationFrame(animate)

  placedModels.forEach((model, index) => {
    model.rotation.y += 0.002 * (index + 1)
    model.scale.set(modelParams.scale, modelParams.scale, modelParams.scale)
    model.rotation.x = (modelParams.rotation.x * Math.PI) / 180
    model.rotation.y += 0.002 * (index + 1)
    model.rotation.z = (modelParams.rotation.z * Math.PI) / 180
  })

  if (platform) {
    platform.position.y = Math.sin(Date.now() * 0.001) * 0.05
  }

  controls.update()
  renderer.render(scene, camera)
}

const resetCamera = () => {
  camera.position.set(5, 5, 10)
  controls.target.set(0, 1, 0)
  controls.update()
  ElMessage.success('视角已重置')
}

const clearModels = () => {
  placedModels.forEach(model => {
    scene.remove(model)
    model.geometry.dispose()
    if (model.material) {
      model.material.dispose()
    }
  })
  placedModels = []
  ElMessage.success('模型已清空')
}

const generateAI = () => {
  showGenerateDialog.value = true
}

const startGeneration = () => {
  showGenerateDialog.value = false
  isGenerating.value = true
  generateProgress.value = 0
  generateStatus.value = '正在分析创意...'

  const steps = [
    { progress: 20, status: '正在生成基础模型...' },
    { progress: 40, status: '正在添加纹理细节...' },
    { progress: 60, status: '正在优化材质渲染...' },
    { progress: 80, status: '正在进行风格转换...' },
    { progress: 100, status: '生成完成！' }
  ]

  let stepIndex = 0
  const interval = setInterval(() => {
    if (stepIndex < steps.length) {
      generateProgress.value = steps[stepIndex].progress
      generateStatus.value = steps[stepIndex].status
      stepIndex++
    } else {
      clearInterval(interval)
      setTimeout(() => {
        isGenerating.value = false
        addGeneratedModel()
        ElMessage.success('AI生成完成！')
      }, 500)
    }
  }, 500)
}

const addGeneratedModel = () => {
  const shapes = [
    () => new THREE.SphereGeometry(0.8, 32, 32),
    () => new THREE.TorusGeometry(0.6, 0.3, 16, 32),
    () => new THREE.ConeGeometry(0.6, 1.2, 32),
    () => new THREE.OctahedronGeometry(0.7),
    () => new THREE.TetrahedronGeometry(0.8)
  ]

  const randomShape = shapes[Math.floor(Math.random() * shapes.length)]
  const geometry = randomShape()
  const material = new THREE.MeshStandardMaterial({
    color: generateForm.color || modelParams.color,
    roughness: 0.3,
    metalness: 0.2,
    emissive: new THREE.Color(generateForm.color || modelParams.color).multiplyScalar(0.2),
    emissiveIntensity: 0.5
  })

  const model = new THREE.Mesh(geometry, material)
  model.position.set(
    (Math.random() - 0.5) * 4,
    1,
    (Math.random() - 0.5) * 4
  )
  model.castShadow = true
  model.receiveShadow = true

  const edges = new THREE.EdgesGeometry(geometry)
  const line = new THREE.LineSegments(edges, new THREE.LineBasicMaterial({ color: 0xffffff }))
  model.add(line)

  scene.add(model)
  placedModels.push(model)
}

const exportModel = () => {
  showExportDialog.value = true
}

const confirmExport = () => {
  showExportDialog.value = false
  ElMessage.success(`模型已导出为${selectedFormat.value}格式`)
}

const onDragStart = (part, event) => {
  event.dataTransfer.setData('partId', part.id.toString())
  event.dataTransfer.effectAllowed = 'move'
}

const onDragEnd = () => {}

onMounted(() => {
  initScene()
  window.addEventListener('resize', onWindowResize)
})

onUnmounted(() => {
  window.removeEventListener('resize', onWindowResize)
  cleanup()
})

const onWindowResize = () => {
  if (!canvasContainer.value || !camera || !renderer) return

  const container = canvasContainer.value
  const width = container.clientWidth
  const height = container.clientHeight

  camera.aspect = width / height
  camera.updateProjectionMatrix()
  renderer.setSize(width, height)
}
</script>

<style scoped>
.ai-workshop {
  height: 100%;
  width: 100%;
  display: flex;
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
  background: #f5f5f5;
}

.content-wrapper {
  flex: 1;
  display: flex;
  overflow: hidden;
}

.left-panel {
  width: 300px;
  background: white;
  border-right: 1px solid #e5e7eb;
  overflow-y: auto;
  box-shadow: 2px 0 10px rgba(0, 0, 0, 0.02);
}

.parts-panel, .params-panel, .actions-panel {
  padding: 20px;
  border-bottom: 1px solid #eee;
}

.parts-panel h3, .params-panel h3, .actions-panel h3 {
  margin: 0 0 15px 0;
  font-size: 15px;
  color: #374151;
  font-weight: 600;
  display: flex;
  align-items: center;
  gap: 8px;
}

.parts-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 10px;
}

.part-item {
  text-align: center;
  cursor: grab;
  border: 1px solid #e5e7eb;
  border-radius: 10px;
  padding: 14px 8px;
  background: white;
  transition: all 0.2s ease;
  user-select: none;
}

.part-item:hover {
  transform: translateY(-2px);
  box-shadow: 0 10px 20px rgba(0, 0, 0, 0.05);
  border-color: #4a90e2;
}

.part-item:active {
  cursor: grabbing;
  transform: scale(0.98);
}

.part-icon {
  width: 50px;
  height: 50px;
  margin: 0 auto 8px;
  border-radius: 25px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: white;
  font-size: 24px;
  box-shadow: 0 4px 10px rgba(0, 0, 0, 0.1);
}

.part-item p {
  margin: 0;
  font-size: 12px;
  color: #4b5563;
  font-weight: 500;
}

.param-value {
  font-size: 12px;
  color: #666;
  margin-left: 8px;
}

.action-btn {
  width: 100%;
  margin-bottom: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
}

.ai-btn {
  background: linear-gradient(135deg, #667eea, #764ba2);
  border-color: transparent;
  color: white;
}

.primary-btn {
  background: linear-gradient(135deg, #4a90a4, #2d6172);
  border-color: transparent;
}

.canvas-container {
  flex: 1;
  position: relative;
  overflow: hidden;
  background: #111827;
}

.canvas-overlay {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.8);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 100;
}

.generating-modal {
  text-align: center;
  color: white;
}

.generating-modal h4 {
  margin: 20px 0;
}

.generating-modal p {
  margin-top: 15px;
  color: #999;
}

.canvas-hint {
  position: absolute;
  bottom: 20px;
  left: 20px;
  color: rgba(255, 255, 255, 0.6);
  background: rgba(0, 0, 0, 0.3);
  padding: 8px 16px;
  border-radius: 20px;
  font-size: 12px;
  backdrop-filter: blur(4px);
  z-index: 10;
  border: 1px solid rgba(255, 255, 255, 0.1);
}

.export-options p {
  margin: 0 0 15px 0;
  color: #666;
}

.format-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.format-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px;
  border: 1px solid #eee;
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.2s;
}

.format-item:hover {
  border-color: #4a90a4;
  background: #f9f9f9;
}

.format-item span {
  font-size: 14px;
  color: #333;
}

.format-desc {
  font-size: 12px;
  color: #999;
  margin-left: auto;
}

:deep(canvas) {
  display: block;
  width: 100% !important;
  height: 100% !important;
  outline: none;
}
</style>
