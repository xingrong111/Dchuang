// ============================================================
// 智绘锡承 - 惠山泥人程序化建模工厂 v2（混元 PBR 手办风格）
// 位置: frontend/src/three/modelFactory.js
//
// v2 视觉升级:
//   - Q版比例（大头短身），圆润融合造型，高细分平滑
//   - MeshPhysicalMaterial 釉面质感（clearcoat + 陶土 bump）
//   - 五官/纹样由 textureFactory.js 直接彩绘在陶面上（三分塑七分彩）
//   - 民间低饱和釉色：朱红/石绿/哑金/月白/青花
//
// 双端复用: 浏览器运行时生成 + Node GLTFExporter 导出 .glb
// 锚点约定: group.userData.attachPoints = [{name, position, accept, used}]
// ============================================================
import * as THREE from 'three'
import {
  GLAZE,
  robeTexture,
  afuFaceTexture,
  catFaceTexture,
  catBodyTexture,
  clayNormalTexture,
} from './textureFactory.js'

// --- 材质工厂：釉面陶土 ---
const _normal = (() => {
  const t = new THREE.CanvasTexture(clayNormalTexture())
  t.wrapS = t.wrapT = THREE.RepeatWrapping
  t.repeat.set(3, 3)
  return t
})()

const clay = (extra = {}) =>
  new THREE.MeshPhysicalMaterial({
    roughness: 0.54,
    metalness: 0.02,
    clearcoat: 0.38,
    clearcoatRoughness: 0.32,
    normalMap: _normal,
    // 无显式切线的网格使用 glTF/OpenGL 绿通道约定，避免导出器逐材质翻转复制贴图。
    normalScale: new THREE.Vector2(1, -1),
    envMapIntensity: 0.9,
    ...extra,
  })

const goldMat = () =>
  new THREE.MeshPhysicalMaterial({
    color: GLAZE.gold,
    roughness: 0.28,
    metalness: 0.85,
    clearcoat: 0.35,
    clearcoatRoughness: 0.25,
    envMapIntensity: 1.2,
  })

const SKIN = GLAZE.skin
const INK = GLAZE.ink

function addAttach(group, name, x, y, z, accept = ['any']) {
  if (!group.userData.attachPoints) group.userData.attachPoints = []
  group.userData.attachPoints.push({ name, position: [x, y, z], accept, used: false })
}

function shadowed(mesh) {
  mesh.castShadow = true
  mesh.receiveShadow = true
  return mesh
}

export function normalizeModel(group, targetHeight = 2.6) {
  const box = new THREE.Box3().setFromObject(group)
  const size = box.getSize(new THREE.Vector3())
  const center = box.getCenter(new THREE.Vector3())
  const s = targetHeight / Math.max(size.y, 0.001)
  const wrap = new THREE.Group()
  group.position.sub(center.multiplyScalar(s))
  group.scale.setScalar(s)
  wrap.add(group)
  return wrap
}

// ============================================================
// 一、可组装部件（5 件）
// ============================================================

/** 部件1: 阿福头部（开脸彩绘+双髻） */
export function createAfuHead() {
  const g = new THREE.Group()

  const head = shadowed(new THREE.Mesh(
    new THREE.SphereGeometry(1, 64, 48),
    clay({ map: afuFaceTexture(), roughness: 0.35, clearcoat: 0.72, bumpScale: 0.008 })
  ))
  head.scale.set(1.02, 0.96, 1)
  g.add(head)

  // 双髻（哑光乌土，略小且贴头）
  for (const sx of [-1, 1]) {
    const bun = shadowed(new THREE.Mesh(
      new THREE.SphereGeometry(0.27, 32, 24),
      clay({ color: INK, roughness: 0.62, clearcoat: 0.25 })
    ))
    bun.position.set(sx * 0.58, 0.78, -0.05)
    g.add(bun)
    const tie = shadowed(new THREE.Mesh(
      new THREE.TorusGeometry(0.2, 0.04, 12, 28),
      clay({ color: GLAZE.vermilion, clearcoat: 0.65 })
    ))
    tie.position.set(sx * 0.57, 0.64, 0.06)
    tie.rotation.x = Math.PI / 2.2
    g.add(tie)
  }

  // 小耳朵（藏在髻下两侧）
  for (const sx of [-1, 1]) {
    const ear = shadowed(new THREE.Mesh(
      new THREE.SphereGeometry(0.16, 20, 16),
      clay({ color: SKIN, roughness: 0.35, clearcoat: 0.7, bumpScale: 0.006 })
    ))
    ear.scale.set(0.7, 1.1, 0.6)
    ear.position.set(sx * 0.92, -0.05, -0.05)
    g.add(ear)
  }

  addAttach(g, 'bottom', 0, -0.88, 0, ['top'])
  return g
}

/** 部件2: 阿福身体（Q版矮胖袍身，袍服彩绘） */
export function createAfuBody() {
  const g = new THREE.Group()

  // 盘腿底座式下半身（宽扁臀腿，和袍子融合）
  const lap = shadowed(new THREE.Mesh(
    new THREE.SphereGeometry(1, 48, 36),
    clay({ color: GLAZE.vermilion })
  ))
  lap.scale.set(1.05, 0.62, 0.92)
  lap.position.y = -0.28
  g.add(lap)

  // 袍身（自下而上收窄的圆润 Lathe）
  const pts = []
  for (let i = 0; i <= 22; i++) {
    const t = i / 22
    // 肩 0.55 → 腰 0.78 → 下摆 1.02，饱满外轮廓
    const r = 1.02 - 0.47 * t + 0.1 * Math.sin(t * Math.PI)
    pts.push(new THREE.Vector2(r, -0.05 + t * 1.12))
  }
  const robe = shadowed(new THREE.Mesh(new THREE.LatheGeometry(pts, 56), clay({ map: robeTexture('red') })))
  robe.rotation.y = Math.PI // 前襟团花对齐 +z
  g.add(robe)

  // 红鞋头（袍摆下露出两个圆润鞋尖）
  for (const sx of [-1, 1]) {
    const shoe = shadowed(new THREE.Mesh(
      new THREE.SphereGeometry(0.2, 24, 18),
      clay({ color: GLAZE.vermilionDark, clearcoat: 0.65 })
    ))
    shoe.scale.set(1.1, 0.62, 1.35)
    shoe.position.set(sx * 0.46, -0.72, 0.62)
    g.add(shoe)
  }

  addAttach(g, 'top', 0, 1.0, 0, ['bottom'])
  addAttach(g, 'bottom', 0, -0.82, 0, ['top'])
  addAttach(g, 'front', 0, 0.28, 0.92, ['front'])
  return g
}

/** 部件3: 短胖环抱臂 */
export function createAfuArms() {
  const g = new THREE.Group()
  for (const sx of [-1, 1]) {
    // 袖管
    const sleevePath = new THREE.CatmullRomCurve3([
      new THREE.Vector3(sx * 0.72, 0.32, -0.25),
      new THREE.Vector3(sx * 0.66, 0.15, 0.12),
      new THREE.Vector3(sx * 0.43, -0.04, 0.43),
      new THREE.Vector3(sx * 0.16, -0.1, 0.62),
    ])
    const sleeve = shadowed(new THREE.Mesh(
      new THREE.TubeGeometry(sleevePath, 40, 0.2, 20, false),
      clay({ map: robeTexture('red') })
    ))
    g.add(sleeve)
    // 金色袖口
    const cuff = shadowed(new THREE.Mesh(
      new THREE.TorusGeometry(0.19, 0.04, 12, 24),
      goldMat()
    ))
    cuff.position.set(sx * 0.16, -0.1, 0.62)
    cuff.quaternion.setFromUnitVectors(new THREE.Vector3(0, 0, 1), sleevePath.getTangent(1).normalize())
    g.add(cuff)
    // 圆手
    const hand = shadowed(new THREE.Mesh(
      new THREE.SphereGeometry(0.16, 22, 16),
      clay({ color: SKIN, roughness: 0.32, clearcoat: 0.75, bumpScale: 0.006 })
    ))
    hand.position.set(sx * 0.13, -0.16, 0.72)
    g.add(hand)
  }
  addAttach(g, 'center', 0, 0, 0, ['front'])
  addAttach(g, 'front', 0, -0.22, 0.55, ['bottom'])
  return g
}

/** 部件4: 描金底座 */
export function createClayBase() {
  const g = new THREE.Group()
  const base = shadowed(new THREE.Mesh(
    new THREE.CylinderGeometry(1.12, 1.3, 0.32, 56),
    clay({ color: '#3c2f26', roughness: 0.5, clearcoat: 0.45 })
  ))
  base.position.y = -0.16
  g.add(base)
  const rim = shadowed(new THREE.Mesh(new THREE.TorusGeometry(1.12, 0.045, 14, 56), goldMat()))
  rim.rotation.x = Math.PI / 2
  rim.position.y = 0.0
  g.add(rim)
  const rim2 = shadowed(new THREE.Mesh(
    new THREE.TorusGeometry(1.22, 0.03, 12, 56),
    new THREE.MeshPhysicalMaterial({ color: GLAZE.gold, roughness: 0.4, metalness: 0.6 })
  ))
  rim2.rotation.x = Math.PI / 2
  rim2.position.y = -0.3
  g.add(rim2)
  addAttach(g, 'top', 0, 0, 0, ['bottom'])
  return g
}

/** 部件5: Q版瑞狮（抱球式看门狮） */
export function createLionBeast() {
  const g = new THREE.Group()
  const gold = clay({ color: GLAZE.gold, roughness: 0.48, metalness: 0.02, clearcoat: 0.4 })

  const bodyM = shadowed(new THREE.Mesh(new THREE.SphereGeometry(0.48, 40, 30), gold))
  bodyM.scale.set(1.05, 0.92, 1.12)
  g.add(bodyM)

  // 鬃毛（一圈红色小瓣环绕头部）
  for (let i = 0; i < 14; i++) {
    const a = (i / 14) * Math.PI * 2
    const petal = shadowed(new THREE.Mesh(
      new THREE.SphereGeometry(0.13, 16, 12),
      clay({ color: GLAZE.vermilion, clearcoat: 0.6 })
    ))
    petal.scale.set(1, 1, 0.7)
    petal.position.set(Math.cos(a) * 0.34, 0.34 + Math.sin(a) * 0.3, 0.26)
    g.add(petal)
  }
  const headM = shadowed(new THREE.Mesh(new THREE.SphereGeometry(0.3, 32, 24), gold))
  headM.position.set(0, 0.34, 0.4)
  g.add(headM)

  // 耳
  for (const sx of [-1, 1]) {
    const ear = shadowed(new THREE.Mesh(
      new THREE.SphereGeometry(0.09, 14, 12),
      clay({ color: GLAZE.vermilion, clearcoat: 0.6 })
    ))
    ear.position.set(sx * 0.2, 0.58, 0.36)
    g.add(ear)
  }
  // 点睛（黑色釉点）
  for (const sx of [-1, 1]) {
    const eye = shadowed(new THREE.Mesh(
      new THREE.SphereGeometry(0.05, 12, 10),
      clay({ color: INK, roughness: 0.15, clearcoat: 1 })
    ))
    eye.position.set(sx * 0.11, 0.4, 0.64)
    g.add(eye)
  }
  // 鼻
  const nose = shadowed(new THREE.Mesh(
    new THREE.SphereGeometry(0.07, 14, 10),
    clay({ color: GLAZE.vermilionDark, clearcoat: 0.7 })
  ))
  nose.scale.set(1.3, 0.8, 0.8)
  nose.position.set(0, 0.28, 0.66)
  g.add(nose)

  // 浅色吻部和弯嘴，让瑞狮区别于仅靠鬃毛辨识的几何球。
  for (const sx of [-1, 1]) {
    const muzzle = shadowed(new THREE.Mesh(new THREE.SphereGeometry(0.085, 20, 16),
      clay({ color: GLAZE.cream, roughness: 0.52, clearcoat: 0.3 })))
    muzzle.scale.set(1.1, 0.75, 0.5)
    muzzle.position.set(sx * 0.065, 0.23, 0.665)
    g.add(muzzle)
    const browPath = new THREE.CatmullRomCurve3([
      new THREE.Vector3(sx * 0.17, 0.45, 0.635),
      new THREE.Vector3(sx * 0.11, 0.48, 0.64),
      new THREE.Vector3(sx * 0.065, 0.46, 0.645),
    ])
    g.add(shadowed(new THREE.Mesh(new THREE.TubeGeometry(browPath, 12, 0.013, 8, false), clay({ color: INK }))))
  }
  const smile = new THREE.CatmullRomCurve3([
    new THREE.Vector3(-0.065, 0.19, 0.685), new THREE.Vector3(0, 0.165, 0.69),
    new THREE.Vector3(0.065, 0.19, 0.685),
  ])
  g.add(shadowed(new THREE.Mesh(new THREE.TubeGeometry(smile, 16, 0.012, 8, false), clay({ color: GLAZE.vermilionDark }))))

  // 四肢（短粗）
  for (const [x, z] of [[-0.26, 0.3], [0.26, 0.3], [-0.26, -0.26], [0.26, -0.26]]) {
    const paw = shadowed(new THREE.Mesh(
      new THREE.SphereGeometry(0.14, 18, 14),
      clay({ color: GLAZE.gold, metalness: 0.02, roughness: 0.52 })
    ))
    paw.scale.set(1, 0.72, 1.15)
    paw.position.set(x, -0.4, z)
    g.add(paw)
  }

  // 尾尖（背上一个小卷）
  const tail = shadowed(new THREE.Mesh(
    new THREE.TorusGeometry(0.12, 0.05, 10, 20),
    clay({ color: GLAZE.vermilion, clearcoat: 0.6 })
  ))
  tail.position.set(0, 0.42, -0.42)
  tail.rotation.set(0.5, 0, 0)
  g.add(tail)

  addAttach(g, 'bottom', 0, -0.5, 0, ['top'])
  return g
}

// ============================================================
// 二、三个经典泥人成品
// ============================================================

function assemble(parts) {
  const root = new THREE.Group()
  for (const { group, pos, rot } of parts) {
    group.position.set(...pos)
    if (rot) group.rotation.set(...rot)
    root.add(group)
  }
  return root
}

/** 大阿福 */
export function createDaAfu() {
  return assemble([
    { group: createClayBase(), pos: [0, 0, 0] },
    { group: createAfuBody(), pos: [0, 0.82, 0] },
    { group: createAfuArms(), pos: [0, 1.1, 0.92] },
    { group: createAfuHead(), pos: [0, 2.7, 0] },
    { group: createLionBeast(), pos: [0, 1.38, 1.47] },
  ])
}

/** 蚕猫（蹲坐，开脸+五彩釉斑） */
export function createCanMao() {
  const g = new THREE.Group()

  // 身体（蹲坐竖椭球，整面五彩釉斑贴图）
  const bodyM = shadowed(new THREE.Mesh(
    new THREE.SphereGeometry(0.78, 56, 40),
    clay({ map: catBodyTexture(), clearcoat: 0.75, roughness: 0.3 })
  ))
  bodyM.scale.set(1.02, 1.18, 0.95)
  bodyM.position.y = 0.52
  g.add(bodyM)

  // 前腿（两只并拢短腿）
  for (const sx of [-1, 1]) {
    const leg = shadowed(new THREE.Mesh(
      new THREE.SphereGeometry(0.2, 24, 18),
      clay({ color: GLAZE.white, clearcoat: 0.8, roughness: 0.28, bumpScale: 0.006 })
    ))
    leg.scale.set(0.9, 1.15, 0.8)
    leg.position.set(sx * 0.24, -0.32, 0.42)
    g.add(leg)
    const toe = shadowed(new THREE.Mesh(
      new THREE.SphereGeometry(0.06, 12, 10),
      clay({ color: GLAZE.vermilion, clearcoat: 0.8 })
    ))
    toe.position.set(sx * 0.24, -0.36, 0.58)
    g.add(toe)
  }

  // 头（开脸彩绘）
  const headM = shadowed(new THREE.Mesh(
    new THREE.SphereGeometry(0.56, 56, 40),
    clay({ map: catFaceTexture(), clearcoat: 0.78, roughness: 0.28, bumpScale: 0.006 })
  ))
  headM.position.set(0, 1.62, 0.12)
  g.add(headM)

  // 圆角耳：曲线轮廓 + 倒角，避免四棱锥的生硬折面。
  const earShape = new THREE.Shape()
  earShape.moveTo(-0.17, -0.15)
  earShape.quadraticCurveTo(-0.12, 0.04, -0.025, 0.19)
  earShape.quadraticCurveTo(0, 0.23, 0.025, 0.19)
  earShape.quadraticCurveTo(0.12, 0.04, 0.17, -0.15)
  earShape.quadraticCurveTo(0, -0.19, -0.17, -0.15)
  const earGeometry = new THREE.ExtrudeGeometry(earShape, { depth: 0.1, steps: 1,
    bevelEnabled: true, bevelSegments: 4, bevelSize: 0.025, bevelThickness: 0.025, curveSegments: 20 })
  earGeometry.translate(0, 0, -0.05)
  for (const sx of [-1, 1]) {
    const ear = shadowed(new THREE.Mesh(
      earGeometry.clone(),
      clay({ color: GLAZE.white, clearcoat: 0.8, roughness: 0.28, bumpScale: 0.006 })
    ))
    ear.position.set(sx * 0.34, 2.02, 0)
    ear.rotation.z = sx * -0.28
    g.add(ear)
    const inner = shadowed(new THREE.Mesh(
      earGeometry.clone(),
      clay({ color: GLAZE.vermilion, clearcoat: 0.7 })
    ))
    inner.scale.set(0.6, 0.65, 0.5)
    inner.position.set(sx * 0.34, 2.02, 0.09)
    inner.rotation.z = sx * -0.28
    g.add(inner)
  }
  earGeometry.dispose()

  // 卷尾（花釉）
  const tail = shadowed(new THREE.Mesh(
    new THREE.TorusGeometry(0.3, 0.085, 14, 28, Math.PI * 1.35),
    clay({ color: GLAZE.vermilion, clearcoat: 0.65 })
  ))
  tail.position.set(0.02, 0.55, -0.62)
  tail.rotation.set(0.35, 0, Math.PI / 2)
  g.add(tail)

  return assemble([{ group: g, pos: [0, 0, 0] }, { group: createClayBase(), pos: [0, -0.55, 0] }])
}

/** 老寿星（高额长眉捧寿桃） */
export function createShouXing() {
  const g = new THREE.Group()

  // 长袍
  const pts = []
  for (let i = 0; i <= 20; i++) {
    const t = i / 20
    pts.push(new THREE.Vector2(0.42 + 0.5 * Math.pow(1 - t, 1.6), t * 1.55 - 0.75))
  }
  const robe = shadowed(new THREE.Mesh(
    new THREE.LatheGeometry(pts, 56),
    clay({ map: robeTexture('cream'), clearcoat: 0.6 })
  ))
  robe.rotation.y = Math.PI
  g.add(robe)

  // 腰带（哑金）
  const belt = shadowed(new THREE.Mesh(new THREE.TorusGeometry(0.6, 0.05, 14, 48), goldMat()))
  belt.rotation.x = Math.PI / 2
  belt.position.y = 0.18
  g.add(belt)

  // 头（寿星开脸：高额+白眉笑眼）
  const headGeometry = new THREE.SphereGeometry(0.42, 48, 36)
  const positions = headGeometry.getAttribute('position')
  for (let i = 0; i < positions.count; i++) {
    const y = positions.getY(i)
    if (y > 0) positions.setY(i, y + 0.23 * (y / 0.42) ** 2)
  }
  headGeometry.computeVertexNormals()
  const headM = shadowed(new THREE.Mesh(
    headGeometry,
    clay({ map: afuFaceTexture('shouxing'), roughness: 0.44, clearcoat: 0.5, bumpScale: 0.006 })
  ))
  headM.position.y = 1.2
  g.add(headM)

  // 高额由头部网格连续变形得到，保留五官 UV，不用前置球体遮挡眉眼。

  // 白寿眉（两缕长白眉）
  for (const sx of [-1, 1]) {
    const brow = shadowed(new THREE.Mesh(
      new THREE.CapsuleGeometry(0.055, 0.22, 8, 14),
      clay({ color: GLAZE.white, roughness: 0.5, clearcoat: 0.4 })
    ))
    brow.position.set(sx * 0.24, 1.24, 0.36)
    brow.rotation.z = sx * 0.5
    g.add(brow)
  }

  // 长须（一体白色锥形须）
  const beard = shadowed(new THREE.Mesh(
      new THREE.SphereGeometry(0.24, 28, 22),
      clay({ color: GLAZE.white, roughness: 0.5, clearcoat: 0.4 })
    ))
  beard.scale.set(0.75, 1.3, 0.48)
  beard.position.set(0, 0.79, 0.32)
  g.add(beard)

  // 捧寿桃
  const peach = shadowed(new THREE.Mesh(
    new THREE.SphereGeometry(0.26, 32, 24),
    clay({ color: '#efb2a0', roughness: 0.3, clearcoat: 0.85 })
  ))
  peach.position.set(0.4, 0.62, 0.46)
  g.add(peach)
  const tip = shadowed(new THREE.Mesh(
    new THREE.ConeGeometry(0.11, 0.2, 20),
    clay({ color: '#e79b8c', clearcoat: 0.85 })
  ))
  tip.position.set(0.4, 0.86, 0.46)
  g.add(tip)
  const leaf = shadowed(new THREE.Mesh(
    new THREE.SphereGeometry(0.1, 16, 10),
    clay({ color: GLAZE.green, clearcoat: 0.7 })
  ))
  leaf.scale.set(1.5, 0.4, 0.8)
  leaf.position.set(0.5, 0.88, 0.44)
  leaf.rotation.z = -0.6
  g.add(leaf)
  const hand = shadowed(new THREE.Mesh(
    new THREE.SphereGeometry(0.13, 18, 14),
    clay({ color: SKIN, roughness: 0.32, clearcoat: 0.75, bumpScale: 0.005 })
  ))
  hand.position.set(0.4, 0.48, 0.5)
  g.add(hand)

  // 龙杖
  const staff = shadowed(new THREE.Mesh(
    new THREE.CylinderGeometry(0.045, 0.055, 1.9, 16),
    clay({ color: '#6b4f3a', roughness: 0.6, clearcoat: 0.3 })
  ))
  staff.position.set(-0.66, 0.28, 0.18)
  g.add(staff)
  const staffTop = shadowed(new THREE.Mesh(new THREE.SphereGeometry(0.11, 18, 14), goldMat()))
  staffTop.position.set(-0.66, 1.26, 0.18)
  g.add(staffTop)

  return assemble([{ group: g, pos: [0, 0, 0] }, { group: createClayBase(), pos: [0, -0.75, 0] }])
}

// ============================================================
// 三、目录表
// ============================================================

export const CLASSIC_MODELS = {
  daafu: { name: '大阿福', create: createDaAfu },
  canmao: { name: '蚕猫', create: createCanMao },
  shouxing: { name: '老寿星', create: createShouXing },
}

export const PART_CATALOG = [
  { id: 'afu_head', name: '阿福头部', icon: '👦', color: GLAZE.skin, create: createAfuHead },
  { id: 'afu_body', name: '阿福身体', icon: '👘', color: GLAZE.vermilion, create: createAfuBody },
  { id: 'afu_arms', name: '环抱双臂', icon: '🤗', color: GLAZE.skin, create: createAfuArms },
  { id: 'clay_base', name: '描金底座', icon: '⭕', color: '#3c2f26', create: createClayBase },
  { id: 'lion_beast', name: '瑞狮', icon: '🦁', color: GLAZE.gold, create: createLionBeast },
]

export function createPartById(id) {
  const item = PART_CATALOG.find(p => p.id === id)
  if (!item) return null
  const part = item.create()
  part.userData.partId = id
  return part
}

export function createClassicById(id) {
  const item = CLASSIC_MODELS[id]
  return item ? normalizeModel(item.create()) : null
}
