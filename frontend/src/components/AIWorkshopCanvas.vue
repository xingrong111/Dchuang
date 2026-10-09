<template>
  <div class="ai-workshop">
    <div class="content-wrapper">
      <div class="left-panel">
        <div class="parts-panel"><h3>混元文创模型</h3><p class="asset-note">现有展示模型，可载入后调整和导出。</p><el-select v-model="assetId" placeholder="选择文创模型" :disabled="assetLoading"><el-option v-for="item in editorial.products" :key="item.id" :value="item.id" :label="item.name" /></el-select><el-button :loading="assetLoading" @click="loadProductAsset">载入模型</el-button></div>
        <div class="parts-panel part-library">
          <h3>部件库</h3><p class="asset-note">头部与身体自动衔接；宠物和配件分别陈列在台座两侧，统一落地。再次选择同类部件可替换款式。</p>
          <div v-if="!partCategory" class="category-grid"><button v-for="category in WORKSHOP_CATEGORIES" :key="category.id" @click="partCategory=category.id"><strong>{{ category.name }}</strong><span>{{ category.parts.length }} 款可选</span></button></div>
          <template v-else><div class="category-header"><button @click="partCategory=''">‹ 全部分类</button><strong>{{ currentCategory.name }}</strong></div><p v-if="partCategory==='arms'&&bodyHasIntegratedArms" class="asset-note">所选身体已包含完整双臂，保留原有姿态，无需重复添加手臂。</p><div class="parts-grid"><article v-for="part in visibleParts" :key="part.id" class="part-item"><ModelPreview :load-object="previewLoaders.get(part.id)" class="part-preview"/><p>{{ part.name }}</p><button :disabled="partLoading||(partCategory==='arms'&&bodyHasIntegratedArms)" :draggable="!(partCategory==='arms'&&bodyHasIntegratedArms)" @click="addPart(part)" @dragstart="onDragStart(part,$event)" @dragend="onDragEnd">{{ loadingPart===part.id?'载入中…':(partCategory==='arms'&&bodyHasIntegratedArms?'身体已含双臂':'加入场景') }}</button></article></div></template>
        </div>

        <div class="params-panel">
          <h3><el-icon><Setting /></el-icon> 参数调整</h3>
          <el-form :model="modelParams" label-width="80px">
            <el-form-item v-for="axis in ['x', 'y', 'z']" :key="axis" :label="`位置${axis.toUpperCase()}`">
              <el-input-number v-model="modelParams.position[axis]" :min="-10" :max="10" :step="0.1" :precision="2" :disabled="selectedConnected" />
            </el-form-item>
            <el-form-item label="缩放">
              <el-slider v-model="modelParams.scale" :min="scaleBounds.min" :max="scaleBounds.max" :step="0.01" />
              <span class="param-value">{{ modelParams.scale.toFixed(2) }}</span>
            </el-form-item>
            <el-form-item v-if="selectedIsHead" label="颈部衔接">
              <el-slider v-model="modelParams.neckLift" :min="-0.015" :max="0.045" :step="0.002" />
              <span class="asset-note">微调头部高度，颈部随之衔接；检查优化可恢复默认。</span>
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
              <el-color-picker v-model="modelParams.color" @change="applyColor" />
            </el-form-item>
          </el-form>
        </div>

        <div class="actions-panel">
          <h3><el-icon><EditPen /></el-icon> 操作</h3>
          <el-switch v-model="autoReview" active-text="添加后自动校正" />
          <el-button @click="runAssemblyReview(true)" class="action-btn">检查并优化装配</el-button>
          <el-button @click="undoAssemblyReview" :disabled="!reviewSnapshot" class="action-btn">撤销上次校正</el-button>
          <el-button @click="runVisualReview" :loading="visualReviewBusy" :disabled="partLoading" class="action-btn">在线视觉复核</el-button>
          <p class="asset-note">在线复核会发送场景截图，需登录并配置视觉服务；可能消耗服务额度。</p>
          <p class="asset-note" role="status">{{ reviewMessage }}</p>
          <ul v-if="reviewDetails.length" class="asset-note"><li v-for="item in reviewDetails" :key="item">{{ item }}</li></ul>
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
            描述创作
          </el-button>
          <el-button @click="exportModel" class="action-btn primary-btn">
            <el-icon><Download /></el-icon>
            导出模型
          </el-button>
          <el-button @click="publishModel" class="action-btn" :loading="isPublishing">保存并发布作品</el-button>
        </div>
      </div>

      <div class="canvas-container" ref="canvasContainer" @dragover.prevent @drop.prevent="onDrop">
        <div class="canvas-overlay" v-if="isGenerating">
          <div class="generating-modal">
            <div class="loading-spinner">
              <el-icon :size="48" color="#4a90a4"><Loading /></el-icon>
            </div>
            <h4>正在制作模型…</h4>
            <el-progress :percentage="generateProgress" :stroke-width="10" />
            <p>{{ generateStatus }}</p>
          </div>
        </div>
        <div class="canvas-hint">
          <span>点击部件自动组装 · 点击模型选中 · 拖动旋转 · 双指或滚轮缩放</span>
        </div>
      </div>
    </div>

    <el-dialog title="创作设置" v-model="showGenerateDialog" width="500px">
      <el-form :model="generateForm" label-width="100px">
        <el-form-item label="创作类型">
          <el-select v-model="generateForm.type" placeholder="请选择">
            <el-option label="惠山泥人风格" value="huishan" />
            <el-option label="锡绣风格" value="xixiu" />
            <el-option label="紫砂风格" value="zisha" />
            <el-option label="自定义风格" value="custom" />
          </el-select>
        </el-form-item>
        <el-form-item label="主题描述">
          <el-input v-model="generateForm.prompt" type="textarea" :rows="3" placeholder="描述你想创作的作品..." />
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
        <el-button type="primary" @click="startGeneration" :disabled="!generateForm.type">开始创作</el-button>
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
            <span class="format-desc">几何网格（彩绘请用 GLB）</span>
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
import { ref, shallowRef, reactive, computed, onMounted, onUnmounted, onActivated, onDeactivated } from 'vue'
import { useRoute } from 'vue-router'
import { useUserStore } from '@/store/userStore'
import editorial from '@/content/editorial.json'
import { ElMessage, ElProgress } from 'element-plus'
import { Setting, EditPen, RefreshLeft, Delete, MagicStick, Download, Loading, Folder, Picture } from '@element-plus/icons-vue'
import * as THREE from 'three'
import { OrbitControls } from 'three/examples/jsm/controls/OrbitControls'
import { GLTFExporter } from 'three/examples/jsm/exporters/GLTFExporter.js'
import { OBJExporter } from 'three/examples/jsm/exporters/OBJExporter.js'
import { RoomEnvironment } from 'three/examples/jsm/environments/RoomEnvironment.js'
import { GLTFLoader } from 'three/examples/jsm/loaders/GLTFLoader.js'
import { generate3D, getTask, reviewAssembly } from '@/api/ai'
import { getWorkDetail, uploadFile, saveWork } from '@/api/workshop'
import { ElMessageBox } from 'element-plus'
import { findConnection, attachPart, alignConnection, rebuildConnections, connectAvailableParts, releasePart } from '@/three/assembly'
import { WORKSHOP_CATEGORIES, WORKSHOP_PARTS, createWorkshopPart } from '@/three/workshopParts'
import ModelPreview from '@/components/ModelPreview.vue'
import { captureAssembly, reviewAndRepair, restoreAssembly } from '@/three/assemblyReview'

const autoReview = ref(true), reviewSnapshot = shallowRef(null), visualReviewBusy = ref(false)
const reviewMessage = ref('本地装配检查会校正比例、连接间隙、倾斜和落地位置。')
const reviewDetails = ref([])
const runAssemblyReview = (notify = false) => {
  if (!placedModels.some(part => part.userData.category)) {
    if (notify) ElMessage.info('请先添加部件')
    return
  }
  const result = reviewAndRepair(placedModels)
  reviewSnapshot.value = result.snapshot
  reviewDetails.value = [...result.changes, ...result.issues.map(issue => issue.text)]
  reviewMessage.value = result.issues.length ? '已完成校正，以下问题仍需补充部件或人工调整。' : '比例、连接与落地检查通过；可继续调整造型。'
  selectModel(selectedModel)
  frameAssembly()
  if(notify)ElMessage.success(result.changes.length ? `已校正${result.changes.length}项；请查看装配说明` : '检查完成，未发现可自动校正的问题')
}
const undoAssemblyReview = () => {
  if (!restoreAssembly(reviewSnapshot.value, placedModels)) {
    reviewSnapshot.value = null
    ElMessage.info('部件已改变，无法恢复这次校正')
    return
  }
  reviewSnapshot.value = null; reviewDetails.value = []
  reviewMessage.value = '已恢复校正前的比例和姿态。'
  selectModel(selectedModel); frameAssembly()
}
const runVisualReview = async () => {
  if (visualReviewBusy.value || !renderer || !placedModels.some(part => part.userData.category)) return
  if (!userStore.user?.token) { ElMessage.info('请先登录后使用在线视觉复核'); return }
  const parts = placedModels.filter(part => part.userData.category)
  const original = captureAssembly(parts)
  visualReviewBusy.value = true
  try {
    const collage = document.createElement('canvas'); collage.width = 1152; collage.height = 384
    const context = collage.getContext('2d'), position = camera.position.clone()
    const offset = position.clone().sub(controls.target), boxVisible = selectionBox?.visible
    if (selectionBox) selectionBox.visible = false
    try {
      for (const [index, angle] of [0, .65, -.65].entries()) {
        camera.position.copy(controls.target).add(offset.clone().applyAxisAngle(new THREE.Vector3(0, 1, 0), angle))
        camera.lookAt(controls.target); renderer.render(scene, camera)
        const ratio = Math.min(384 / renderer.domElement.width, 384 / renderer.domElement.height)
        const width = renderer.domElement.width * ratio, height = renderer.domElement.height * ratio
        context.fillStyle = '#eee8dd'; context.fillRect(index * 384, 0, 384, 384)
        context.drawImage(renderer.domElement, index * 384 + (384 - width) / 2, (384 - height) / 2, width, height)
      }
    } finally {
      camera.position.copy(position); camera.lookAt(controls.target)
      if (selectionBox) selectionBox.visible = boxVisible
      renderer.render(scene, camera)
    }
    const result = (await reviewAssembly({ parts: parts.map(part => ({ id: part.uuid, category: part.userData.category })), image: collage.toDataURL('image/png') })).data
    if (editorDisposed || parts.length !== placedModels.filter(part => part.userData.category).length || original.some(item => !placedModels.includes(item.part) || !item.part.position.equals(item.position) || !item.part.quaternion.equals(item.quaternion) || !item.part.scale.equals(item.scale))) {
      ElMessage.info('场景已改变，请重新复核'); return
    }
    const baseline = reviewAndRepair(parts)
    for (const adjustment of result.adjustments || []) {
      const part = parts.find(part => part.uuid === adjustment.id)
      if (!part || !['pet', 'accessory'].includes(part.userData.category)) continue
      part.scale.multiplyScalar(THREE.MathUtils.clamp(adjustment.scaleFactor ?? 1, .9, 1.1))
      part.rotation.y += THREE.MathUtils.degToRad(THREE.MathUtils.clamp(adjustment.yawDegrees ?? 0, -15, 15))
      alignConnection(part)
    }
    const verified = reviewAndRepair(parts)
    if (verified.issues.some(issue => issue.part && !baseline.issues.some(old => old.code === issue.code && old.part === issue.part))) restoreAssembly(baseline.snapshot, parts)
    reviewSnapshot.value = original
    reviewMessage.value = '在线复核完成；变换建议已经过本地装配检查。'
    reviewDetails.value = [result.summary, ...verified.issues.map(issue => issue.text)]
    selectModel(selectedModel); frameAssembly()
  } catch (error) { ElMessage.error(error.message || '在线复核暂不可用，本地校正仍可使用') }
  finally { visualReviewBusy.value = false }
}

// 部件库来自程序化建模工厂（含锚点连接接口 userData.attachPoints）
const parts = WORKSHOP_PARTS
const userStore = useUserStore()
const partCategory=ref(''),loadingPart=ref(''),partLoading=ref(false)
const currentCategory=computed(()=>WORKSHOP_CATEGORIES.find(c=>c.id===partCategory.value))
const visibleParts=computed(()=>currentCategory.value?.parts||[])
const previewLoaders=new Map(parts.map(part=>[part.id,()=>createWorkshopPart(part.id)]))

const canvasContainer = ref(null)
const showGenerateDialog = ref(false)
const showExportDialog = ref(false)
const isGenerating = ref(false)
const generateProgress = ref(0)
const generateStatus = ref('')
const isPublishing = ref(false)
let generationTimer = null
let resumeGenerationWait = null
let generationCancelled = false
const selectedFormat = ref('glb')
const selectedConnected = ref(false)
const selectedIsHead=ref(false)
const bodyHasIntegratedArms = ref(false),scaleBounds=ref({min:.1,max:3})

const modelParams = reactive({
  neckLift:0,
  scale: 1,
  rotation: { x: 0, y: 0, z: 0 },
  position: { x: 0, y: 0, z: 0 },
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
let placedModels = []
let modelsGroup = null
let selectedModel = null
let raycaster = null
let pointer = null
let animationId = null
let resizeObserver = null
let selectionBox = null

const cleanup = () => {
  resizeObserver?.disconnect()
  generationCancelled = true
  clearTimeout(generationTimer)
  resumeGenerationWait?.()
  resumeGenerationWait = null
  clearModels(false)
  scene?.environment?.dispose()
  if (animationId) {
    cancelAnimationFrame(animationId)
  }
  window.removeEventListener('keydown', onKeyDown)
  if (renderer && renderer.domElement) {
    renderer.domElement.removeEventListener('pointerdown', onCanvasPointerDown)
  }
  if (controls) {
    controls.dispose()
  }
  if (renderer) {
    renderer.dispose()
    renderer.forceContextLoss()
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
  scene.background = new THREE.Color(0xeee8dd)

  camera = new THREE.PerspectiveCamera(45, width / height, 0.1, 1000)
  camera.position.set(5, 5, 10)
  camera.lookAt(0, 1, 0)

  renderer = new THREE.WebGLRenderer({ antialias: true, preserveDrawingBuffer: true })
  renderer.toneMapping = THREE.ACESFilmicToneMapping
  renderer.setSize(width, height)
  renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2))
  renderer.shadowMap.enabled = true
  renderer.shadowMap.type = THREE.PCFShadowMap
  container.appendChild(renderer.domElement)

  // PBR 环境反射：让釉面/金属材质呈现混元手办般的柔和光影
  const pmrem = new THREE.PMREMGenerator(renderer)
  const room = new RoomEnvironment()
  scene.environment = pmrem.fromScene(room, 0.04).texture
  room.dispose()
  pmrem.dispose()

  controls = new OrbitControls(camera, renderer.domElement)
  controls.enableDamping = true
  controls.dampingFactor = 0.05
  controls.autoRotate = false
  controls.autoRotateSpeed = 1.0
  controls.enableZoom = true
  controls.maxPolarAngle = Math.PI / 2
  controls.target.set(0, 1, 0)

  addLights()
  createPlatform()
  addEnvironment()
  addSampleModels()
  initInteraction()
  animate()
}

// ---- 选中拾取与部件组装交互 ----
const initInteraction = () => {
  raycaster = new THREE.Raycaster()
  pointer = new THREE.Vector2()
  renderer.domElement.addEventListener('pointerdown', onCanvasPointerDown)
  window.addEventListener('keydown', onKeyDown)
}

const onCanvasPointerDown = (event) => {
  if (!camera) return
  const rect = renderer.domElement.getBoundingClientRect()
  pointer.x = ((event.clientX - rect.left) / rect.width) * 2 - 1
  pointer.y = -((event.clientY - rect.top) / rect.height) * 2 + 1
  raycaster.setFromCamera(pointer, camera)
  const hits = raycaster.intersectObjects(modelsGroup ? modelsGroup.children : [], true)
  if (hits.length > 0) {
    // 从命中的 mesh 向上找到所属部件根节点（placedModels 中的直接子节点）
    let obj = hits[0].object
    while (obj && !placedModels.includes(obj)) obj = obj.parent
    selectModel(obj)
  } else {
    selectModel(null)
  }
}

const onKeyDown = (event) => {
  if (event.target?.closest('input, textarea, [contenteditable="true"]')) return
  if ((event.key === 'Delete' || event.key === 'Backspace') && selectedModel) {
    event.preventDefault()
    deleteSelected()
  }
}

const selectModel = (model) => {
  // 清除旧选中高亮
  if (selectionBox) { selectionBox.removeFromParent(); selectionBox.geometry.dispose(); selectionBox.material.dispose(); selectionBox=null }
  selectedModel = model
  selectedConnected.value = !!model?.userData.connection
  selectedIsHead.value=model?.userData.category==='head'&&!!model?.userData.connection
  modelParams.neckLift=model?.userData.neckLift||0
  const fit=model?.userData.fittedScale
  scaleBounds.value=model?.userData.category==='head'&&model.userData.connection&&fit?{min:fit*.9,max:fit*1.1}:{min:.1,max:3}
  if (model) {
    modelParams.position = { x: model.position.x, y: model.position.y, z: model.position.z }
    modelParams.scale = model.scale.x
    modelParams.rotation = { x: THREE.MathUtils.radToDeg(model.rotation.x), y: THREE.MathUtils.radToDeg(model.rotation.y), z: THREE.MathUtils.radToDeg(model.rotation.z) }
    selectionBox=new THREE.BoxHelper(model,0xb6a06c)
    selectionBox.material.transparent=true;selectionBox.material.opacity=.35
    scene.add(selectionBox)
  }
}

const deleteSelected = () => {
  if (!selectedModel) return
  const removed = new Set()
  selectedModel.traverse(o => removed.add(o))
  selectModel(null)
  const root = [...removed][0]
  disposeAsset(root)
  root.removeFromParent()
  placedModels = placedModels.filter(m => !removed.has(m))
  bodyHasIntegratedArms.value=placedModels.some(m=>m.userData.integratedArms)
  rebuildConnections(placedModels)
  selectedModel = null
  ElMessage.success('部件已删除，锚点已重置')
}

// 只改变当前部件，不穿过子部件的组装边界。
const applyColor = (color) => {
  if (!selectedModel || !color) return
  const visit = (object) => {
    if (object !== selectedModel && placedModels.includes(object)) return
    if (object.isMesh) for (const material of [object.material].flat().filter(Boolean)) material.color?.set(color)
    for (const child of object.children) visit(child)
  }
  visit(selectedModel)
}



/** 从部件库添加部件（点击/拖入），优先自动吸附到开放锚点 */
const addPart = async (part) => {
  if(partLoading.value||editorDisposed)return
  if(part.category==='arms'&&bodyHasIntegratedArms.value){ElMessage.info('所选身体已包含双臂，保留原有完整姿态');return}
  partLoading.value=true;loadingPart.value=part.id
  let partObj
  try{partObj=await createWorkshopPart(part.id)}catch{ElMessage.error('部件加载失败，请重试')}finally{partLoading.value=false;loadingPart.value=''}
  if(!partObj)return
  if(editorDisposed){disposeAsset(partObj);return}
  if(partObj.userData.integratedArms){
    for(const arms of placedModels.filter(m=>m.userData.category==='arms')){
      selectModel(null);placedModels=releasePart(arms,placedModels,modelsGroup);disposeAsset(arms)
    }
  }
  partObj.traverse(o => {
    if (o.isMesh) { o.castShadow = true; o.receiveShadow = true }
  })

  const previous=placedModels.find(model=>model.userData.category===part.category)
  if(previous){
    selectModel(null)
    placedModels=releasePart(previous,placedModels,modelsGroup)
    disposeAsset(previous)
  }
  const snap = findConnection(partObj, placedModels)
  if (snap) {
    attachPart(partObj, snap)
  } else {
    partObj.position.set(0,0.11,0)
    modelsGroup.add(partObj)
  }

  placedModels.push(partObj)
  bodyHasIntegratedArms.value=placedModels.some(m=>m.userData.integratedArms)
  connectAvailableParts(placedModels)
  reviewSnapshot.value=null
  if(autoReview.value)runAssemblyReview()
  selectModel(partObj)
  frameAssembly()
  const connected=partObj.userData.connection||placedModels.some(model=>model.userData.connection?.targetUUID===partObj.uuid)
  if(connected)ElMessage.success(`「${part.name}」已自动拼接`)
  else ElMessage.info(`「${part.name}」已放置，添加配套部件后自动拼接`)
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
    color: 0xd8d1c5,
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

  const gridHelper = new THREE.GridHelper(8, 16, 0xa89a83, 0xc3b8a5)
  gridHelper.position.y = 0.11
  gridHelper.material.opacity = 0.3
  gridHelper.material.transparent = true
  platformGroup.add(gridHelper)

  const ringGeo = new THREE.TorusGeometry(4.1, 0.05, 16, 100)
  const ringMat = new THREE.MeshStandardMaterial({
    color: 0xa99a80,
    roughness: .9
  })
  const ring = new THREE.Mesh(ringGeo, ringMat)
  ring.rotation.x = Math.PI / 2
  ring.position.y = 0.15
  platformGroup.add(ring)


  scene.add(platformGroup)
}

const addSampleModels = () => {
  // 部件组装容器（导出时只导出该组）
  modelsGroup = new THREE.Group()
  modelsGroup.name = 'assembledParts'
  scene.add(modelsGroup)


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

let editorActive = true
onActivated(() => { editorActive = true })
onDeactivated(() => { editorActive = false })
const animate = () => {
  animationId = requestAnimationFrame(animate)
  if (!editorActive) return

  // 参数面板仅作用于当前选中部件（不再强制所有部件统一变形/自转，以保持锚点对位）
  if (selectedModel) {
    if(selectedModel.userData.category==='head')selectedModel.userData.neckLift=modelParams.neckLift
    if (!selectedModel.userData.connection) selectedModel.position.set(modelParams.position.x, modelParams.position.y, modelParams.position.z)
    selectedModel.scale.setScalar(modelParams.scale)
    selectedModel.rotation.set(
      (modelParams.rotation.x * Math.PI) / 180,
      (modelParams.rotation.y * Math.PI) / 180,
      (modelParams.rotation.z * Math.PI) / 180
    )
    alignConnection(selectedModel)
    for(const part of placedModels)if(['pet','accessory'].includes(part.userData.category))alignConnection(part)
    selectionBox?.update()
  }

  controls.update()
  renderer.render(scene, camera)
}

const resetCamera = () => {
  if (modelsGroup?.children.length) { frameAssembly(); return }
  camera.position.set(5, 5, 10)
  controls.target.set(0, 1, 0)
  controls.update()
  ElMessage.success('视角已重置')
}

const frameAssembly = () => {
  if (!modelsGroup?.children.length || !camera || !controls) return
  modelsGroup.updateMatrixWorld(true)
  const bounds=new THREE.Box3().setFromObject(modelsGroup),size=bounds.getSize(new THREE.Vector3()),center=bounds.getCenter(new THREE.Vector3())
  const halfFov=Math.tan(THREE.MathUtils.degToRad(camera.fov/2))
  const distance=Math.max(size.y/(2*halfFov),size.x/(2*halfFov*camera.aspect),size.z)*1.35
  camera.position.set(center.x+size.x*.16,center.y+size.y*.14,center.z+distance)
  controls.target.copy(center);controls.update()
}

const clearModels = (notify = true) => {
  if (modelsGroup) {
    disposeAsset(modelsGroup)
    modelsGroup.clear()
  }
  placedModels = []
  reviewSnapshot.value=null;reviewDetails.value=[]
  bodyHasIntegratedArms.value=false
  selectModel(null)
  if (notify) ElMessage.success('模型已清空')
}

const assetId=ref('afu-desk'),assetLoading=ref(false),route=useRoute()
let editorDisposed=false
const disposeAsset=object=>object?.traverse(child=>{child.geometry?.dispose();for(const material of [child.material].flat().filter(Boolean)){for(const value of Object.values(material))if(value?.isTexture)value.dispose();material.dispose()}})
const loadProductAsset=async()=>{
 if(assetLoading.value)return
 const product=editorial.products.find(item=>item.id===assetId.value)
 if(!product)return
 assetLoading.value=true
 try{
  const model=(await new GLTFLoader().loadAsync(import.meta.env.BASE_URL+product.model)).scene
  if(editorDisposed){disposeAsset(model);return}
  const bounds=new THREE.Box3().setFromObject(model),size=bounds.getSize(new THREE.Vector3()),factor=2.6/Math.max(size.x,size.y,size.z)
  if(!Number.isFinite(factor)){disposeAsset(model);throw Error('模型没有有效几何体')}
  model.position.sub(bounds.getCenter(new THREE.Vector3()))
  const normalized=new THREE.Group();normalized.add(model);normalized.scale.setScalar(factor)
  const wrap=new THREE.Group();wrap.name=product.name;wrap.add(normalized);wrap.position.y=size.y*factor/2+0.02
  modelsGroup.add(wrap);placedModels.push(wrap);selectModel(wrap);ElMessage.success('混元文创模型已载入')
 }catch{if(!editorDisposed)ElMessage.error('模型载入失败，请重试')}finally{assetLoading.value=false}
}

const generateAI = () => {
  showGenerateDialog.value = true
}

const startGeneration = async () => {
  if (!generateForm.prompt.trim()) return ElMessage.warning('请输入作品描述')
  showGenerateDialog.value = false
  isGenerating.value = true
  generationCancelled = false
  generateProgress.value = 0
  generateStatus.value = '正在提交任务...'
  try {
    let task = (await generate3D({ task_type: 'text_to_3d', prompt: `${generateForm.type}：${generateForm.prompt.trim()}，惠山彩绘泥人，圆润造型，陶土材质`, params: { detail: generateForm.detail, color: generateForm.color } })).data
    const deadline = Date.now() + 15 * 60 * 1000
    while (!generationCancelled && ['PENDING', 'RUNNING'].includes(task.status)) {
      if (Date.now() > deadline) throw new Error('等待超时，可在个人中心查看任务进度')
      generateStatus.value = task.status === 'PENDING' ? '任务排队中...' : '云端正在制作模型...'
      await new Promise(resolve => { resumeGenerationWait = resolve; generationTimer = setTimeout(resolve, 3000) })
      resumeGenerationWait = null
      if (generationCancelled) return
      task = (await getTask(task.id)).data
    }
    if (generationCancelled) return
    if (task.status !== 'SUCCESS') throw new Error(task.error_message || '制作失败')
    const work = task.artwork_id ? (await getWorkDetail(task.artwork_id)).data : null
    const url = work?.model_url || task.result_url
    if (!url) throw new Error('生成任务未返回模型地址')
    const model = (await new GLTFLoader().loadAsync(url)).scene
    if (generationCancelled) { disposeAsset(model); return }
    const bounds = new THREE.Box3().setFromObject(model)
    const height = bounds.getSize(new THREE.Vector3()).y
    if (!height) throw new Error('模型没有有效几何体')
    const wrap = new THREE.Group()
    model.position.sub(bounds.getCenter(new THREE.Vector3()))
    wrap.add(model)
    wrap.scale.setScalar(2.6 / height)
    wrap.position.set(0, 1.5, 0)
    modelsGroup.add(wrap)
    placedModels.push(wrap)
    selectModel(wrap)
    generateProgress.value = 100
    ElMessage.success(task.provider === 'mock' ? '阿福模型已载入' : '作品模型已加载')
  } catch (error) {
    if (!generationCancelled) ElMessage.error(error.message || '模型生成或加载失败，请在个人中心查看任务')
  } finally { isGenerating.value = false }
}

const serializeModel = () => new Promise((resolve, reject) => {
  if (!modelsGroup?.children.length) return reject(new Error('请先添加模型'))
  const selected = selectedModel
  selectModel(null)
  new GLTFExporter().parse(modelsGroup, result => {
    selectModel(selected)
    resolve(new Blob([result], { type: 'model/gltf-binary' }))
  }, error => { selectModel(selected); reject(error) }, { binary: true })
})

const publishModel = async () => {
  if (isPublishing.value) return
  if (!userStore.user?.token) return ElMessage.warning('请先登录后发布作品，当前组装可直接导出保存')
  try {
    const { value: title } = await ElMessageBox.prompt('请输入作品名称', '发布作品', { inputValidator: v => !!v?.trim() && v.trim().length <= 200 })
    isPublishing.value = true
    const blob = await serializeModel()
    const upload = await uploadFile(new File([blob], 'creation.glb', { type: 'model/gltf-binary' }))
    const selection = selectedModel
    selectModel(null)
    renderer.render(scene, camera)
    const thumbnailBlob = await new Promise(resolve => renderer.domElement.toBlob(resolve, 'image/png'))
    selectModel(selection)
    if (!thumbnailBlob) throw new Error('无法生成作品缩略图')
    const thumbnail = await uploadFile(new File([thumbnailBlob], 'preview.png', { type: 'image/png' }))
    await saveWork({ title: title.trim(), model_url: upload.data.url, thumbnail: thumbnail.data.url, tags: ['惠山泥人'], is_public: true })
    ElMessage.success('作品已保存到社区和个人中心')
  } catch (error) {
    if (!['cancel', 'close'].includes(error)) ElMessage.error(error.message || '作品保存失败')
  } finally { isPublishing.value = false }
}

const exportModel = () => {
  showExportDialog.value = true
}

const confirmExport = () => {
  if (selectedFormat.value === 'glb') {
    exportAsGlb()
  } else if (selectedFormat.value === 'png') {
    exportAsPng()
  } else {
    if (!modelsGroup?.children.length) return ElMessage.warning('请先添加模型')
    modelsGroup.updateMatrixWorld(true)
    const url = URL.createObjectURL(new Blob([new OBJExporter().parse(modelsGroup)], { type: 'text/plain' }))
    const link = document.createElement('a')
    link.href = url; link.download = 'huishan-creation.obj'; link.click()
    setTimeout(() => URL.revokeObjectURL(url), 1000)
    ElMessage.success('OBJ 网格已导出；保留彩绘与材质请使用 GLB')
  }
  showExportDialog.value = false
}

const exportAsGlb = async () => {
  if (!modelsGroup || modelsGroup.children.length === 0) {
    ElMessage.warning('场景中没有可导出的部件')
    return
  }
  try {
      const blob = await serializeModel()
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = 'huishan-creation.glb'
      a.click()
      setTimeout(() => URL.revokeObjectURL(url), 1000)
      ElMessage.success('GLB 模型已导出，可在 共创页上传或保存作品')
  } catch (err) {
      console.error('GLB 导出失败:', err)
      ElMessage.error('导出失败，请重试')
  }
}

const exportAsPng = () => {
  // 强制渲染一帧后截图
  const selection = selectedModel
  selectModel(null)
  renderer.render(scene, camera)
  const url = renderer.domElement.toDataURL('image/png')
  selectModel(selection)
  const a = document.createElement('a')
  a.href = url
  a.download = 'huishan-creation.png'
  a.click()
  ElMessage.success('PNG 截图已导出')
}

const onDragStart = (part, event) => {
  event.dataTransfer.setData('partId', part.id.toString())
  event.dataTransfer.effectAllowed = 'move'
}

const onDragEnd = () => {}
const onDrop = (event) => {
  const part = parts.find(p => p.id === event.dataTransfer.getData('partId'))
  if (part) addPart(part)
}

onMounted(() => {
  initScene()
  if(editorial.products.some(item=>item.id===route.query.modelAsset)){assetId.value=route.query.modelAsset;loadProductAsset()}
  resizeObserver = new ResizeObserver(onWindowResize)
  resizeObserver.observe(canvasContainer.value)
  window.addEventListener('resize', onWindowResize)
})

onUnmounted(() => {
  editorDisposed=true
  window.removeEventListener('resize', onWindowResize)
  cleanup()
})

const onWindowResize = () => {
  if (!canvasContainer.value || !camera || !renderer) return

  const container = canvasContainer.value
  const width = container.clientWidth
  const height = container.clientHeight

  if (!width || !height) return

  camera.aspect = width / height
  camera.updateProjectionMatrix()
  renderer.setSize(width, height)
  frameAssembly()
}
</script>

<style scoped>
.category-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:12px}.category-grid button{display:grid;gap:10px;padding:22px 10px;border:1px solid #ddd3bd;border-radius:12px;background:#faf7f0;color:#365e58;cursor:pointer}.category-grid span{font-size:12px;color:#776e5f}.category-header{display:flex;gap:16px;align-items:center;margin-bottom:16px}.category-header button,.part-item>button{border:1px solid #d3c5ab;background:#fffdf5;color:#365e58;border-radius:8px;padding:8px;cursor:pointer}.part-library .parts-grid{grid-template-columns:repeat(2,minmax(0,1fr))}.part-library .part-item{padding:6px;cursor:default}.part-library .part-item:hover{transform:none}.part-preview{height:145px!important;border-radius:8px}.part-preview :deep(.gesture-hint),.part-preview :deep(.reset-view){display:none}.part-library .part-item p{font-size:12px}.part-item>button{font-size:12px;width:100%}
.asset-note{font-size:12px;color:#766b5e;line-height:1.6}
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

@media (max-width: 768px) {
  .ai-workshop { height: auto; min-height: 900px; }
  .content-wrapper { flex-direction: column; overflow: visible; }
  .canvas-container { order: -1; width: 100%; flex: none; height: 420px; min-height: 420px; }
  .left-panel { width: 100%; overflow: visible; border-right: 0; }
  .parts-grid { grid-template-columns: repeat(3, minmax(0, 1fr)); }
  .parts-panel, .params-panel, .actions-panel { padding: 16px; }
  .part-item { padding: 10px 4px; }
  .part-icon { width: 40px; height: 40px; }
  .canvas-hint { left: 10px; right: 10px; bottom: 12px; padding: 8px; }
}
</style>

