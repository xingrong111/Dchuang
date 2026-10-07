<template><div ref="container" class="model-preview" role="region" aria-label="可旋转三维模型"><span v-if="message" class="model-message" aria-live="polite">{{ message }}<button v-if="failed" @click="load">重新加载</button></span><button v-if="!message" class="reset-view" @click="resetView">重置视角</button><span v-if="!message" class="gesture-hint">拖动旋转 · 滚轮或双指缩放</span></div></template>
<script setup>
import { ref, watch, onMounted, onUnmounted } from 'vue'
import * as THREE from 'three'
import { GLTFLoader } from 'three/examples/jsm/loaders/GLTFLoader.js'
import { OrbitControls } from 'three/examples/jsm/controls/OrbitControls.js'
import { RoomEnvironment } from 'three/examples/jsm/environments/RoomEnvironment.js'
const props = defineProps({ url: { type: String, default: '' }, loadObject: { type: Function, default: null } })
const container = ref(null), message = ref(''), failed = ref(false)
let renderer, scene, camera, controls, model, observer, visibilityObserver, environmentTarget, frame, generation = 0, visible = true
const resetView = () => { if (!camera || !controls) return; controls.target.set(0, 0, 0); camera.position.set(2.3, 1.6, 4.5); controls.update() }
const dispose = object => object?.traverse(child => {
  child.geometry?.dispose()
  for (const material of [child.material].flat().filter(Boolean)) {
    for (const value of Object.values(material)) if (value?.isTexture) value.dispose()
    material.dispose()
  }
})
const load = async () => {
  if (!scene) return
  const token = ++generation
  if (model) { scene.remove(model); dispose(model); model = null }
  if (!props.url && !props.loadObject) { message.value = '暂无 3D 模型'; return }
  message.value = '模型加载中...'
  failed.value = false
  try {
    const gltf = props.loadObject ? { scene: await props.loadObject() } : await new GLTFLoader().loadAsync(props.url)
    if (token !== generation) { dispose(gltf.scene); return }
    const box = new THREE.Box3().setFromObject(gltf.scene)
    const size = box.getSize(new THREE.Vector3())
    if (!size.length()) throw new Error('模型为空')
    model = new THREE.Group()
    gltf.scene.position.sub(box.getCenter(new THREE.Vector3()))
    model.add(gltf.scene)
    model.scale.setScalar(2.6 / Math.max(size.x, size.y, size.z))
    scene.add(model)
    controls.target.set(0, 0, 0)
    resetView()
    message.value = ''
  } catch { if (token === generation) { message.value = '模型加载失败，请重试'; failed.value = true } }
}
watch([() => props.url, () => props.loadObject], load)
onMounted(() => {
  try {
    scene = new THREE.Scene(); scene.background = new THREE.Color('#eee8dd')
    camera = new THREE.PerspectiveCamera(35, 1, 0.01, 100)
    renderer = new THREE.WebGLRenderer({ antialias: true })
    renderer.setPixelRatio(Math.min(devicePixelRatio, 2)); renderer.toneMapping = THREE.ACESFilmicToneMapping
    container.value.appendChild(renderer.domElement)
    const pmrem = new THREE.PMREMGenerator(renderer), room = new RoomEnvironment()
    environmentTarget = pmrem.fromScene(room, 0.04); scene.environment = environmentTarget.texture; room.dispose(); pmrem.dispose()
    scene.add(new THREE.HemisphereLight(0xffffff, 0x756251, 0.8))
    const light = new THREE.DirectionalLight(0xffffff, 1.6); light.position.set(3, 5, 4); scene.add(light)
    controls = new OrbitControls(camera, renderer.domElement); controls.enableDamping = true
    controls.enablePan = false; controls.minDistance = 2; controls.maxDistance = 9
    renderer.domElement.setAttribute('aria-label', '拖动旋转模型，双指或滚轮缩放')
    observer = new ResizeObserver(() => {
      const { clientWidth: w, clientHeight: h } = container.value
      if (!w || !h) return
      renderer.setSize(w, h); camera.aspect = w / h; camera.updateProjectionMatrix()
    }); observer.observe(container.value)
    visibilityObserver = new IntersectionObserver(entries => { visible = entries[0].isIntersecting }); visibilityObserver.observe(container.value)
    const render = () => { frame = requestAnimationFrame(render); if (!visible || document.hidden) return; controls.update(); renderer.render(scene, camera) }; render()
    load()
  } catch { message.value = '当前浏览器无法创建 3D 画布' }
})
onUnmounted(() => { generation++; cancelAnimationFrame(frame); observer?.disconnect(); visibilityObserver?.disconnect(); controls?.dispose(); dispose(model); environmentTarget?.dispose(); renderer?.dispose(); renderer?.forceContextLoss(); renderer?.domElement.remove() })
</script>
<style scoped>.model-preview{height:360px;width:100%;position:relative;overflow:hidden;border-radius:12px}.model-message{position:absolute;inset:0;display:flex;flex-direction:column;gap:12px;align-items:center;justify-content:center;color:#655b4e;z-index:1}.reset-view{position:absolute;right:12px;top:12px;z-index:1}.gesture-hint{position:absolute;bottom:12px;left:12px;font-size:12px;color:#655b4e;background:#ffffffc9;padding:5px 8px;border-radius:5px}.model-preview button{border:1px solid #d5c9b5;background:#fffdf5;border-radius:8px;padding:6px 10px;cursor:pointer}</style>
