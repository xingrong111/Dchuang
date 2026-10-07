// ============================================================
// 智绘锡承 - 惠山泥人程序化彩绘贴图工厂
// 位置: frontend/src/three/textureFactory.js
//
// 设计理念对齐腾讯混元3D PBR 手办风格 + 惠山"三分塑七分彩":
//   五官/纹样不是独立浮贴的几何体，而是用 Canvas 2D 直接"画"在陶面上，
//   再配合 MeshPhysicalMaterial 的 clearcoat 形成上釉质感。
//
// UV 约定（three.js 内置几何体）:
//   SphereGeometry 正面(+z)在 u=0.25，v 上→下
//   LatheGeometry 正面(+z)在 u=0 接缝处 —— 使用方需将 mesh.rotation.y = PI，
//   此时正面映射到 u=0.5
// ============================================================
import * as THREE from 'three'

// --- 民间釉色（比纯色低饱和，模拟矿物颜料+釉面） ---
export const GLAZE = {
  vermilion: '#b0392e',
  vermilionDark: '#8f2c25',
  green: '#2f7d5e',
  gold: '#c9a24e',
  goldLight: '#e3c578',
  skin: '#f3ddbf',
  cream: '#ece1cc',
  cobalt: '#3d6b94',
  ink: '#3a2b20',
  blush: '#e2948d',
  white: '#f6efe2',
}

const makeCanvas = (w, h) => {
  const c = document.createElement('canvas')
  c.width = w
  c.height = h
  return c
}

const toTexture = (canvas) => {
  const t = new THREE.CanvasTexture(canvas)
  t.colorSpace = THREE.SRGBColorSpace
  t.anisotropy = 8
  t.wrapS = THREE.RepeatWrapping
  t.wrapT = THREE.ClampToEdgeWrapping
  t.needsUpdate = true
  return t
}

// 陶土细颗粒（bump 用，多材质共享一张）
let _noiseCanvas = null
// 固定种子让运行时和 GLB 导出得到相同彩绘颗粒，方便复核视觉差异。
const seededRandom = (seed) => () => {
  seed = (Math.imul(1664525, seed) + 1013904223) >>> 0
  return seed / 4294967296
}
export function clayNoiseTexture() {
  if (_noiseCanvas) return _noiseCanvas
  const c = makeCanvas(256, 256)
  const ctx = c.getContext('2d')
  const img = ctx.createImageData(256, 256)
  const random = seededRandom(20261001)
  for (let i = 0; i < img.data.length; i += 4) {
    const v = 120 + random() * 50
    img.data[i] = img.data[i + 1] = img.data[i + 2] = v
    img.data[i + 3] = 255
  }
  ctx.putImageData(img, 0, 0)
  _noiseCanvas = c
  return c
}

let normalCanvas = null
// glTF 支持 normalMap，不支持 Three.js 的 bumpMap；烘焙法线保证导出后保留陶土肌理。
export function clayNormalTexture() {
  if (normalCanvas) return normalCanvas
  const height = clayNoiseTexture().getContext('2d').getImageData(0, 0, 256, 256).data
  const canvas = makeCanvas(256, 256), ctx = canvas.getContext('2d')
  const pixels = ctx.createImageData(256, 256)
  const at = (x, y) => height[(((y + 256) % 256) * 256 + (x + 256) % 256) * 4] / 255
  for (let y = 0; y < 256; y++) for (let x = 0; x < 256; x++) {
    const dx = (at(x - 1, y) - at(x + 1, y)) * 0.12
    const dy = (at(x, y - 1) - at(x, y + 1)) * 0.12
    const length = Math.hypot(dx, dy, 1), i = (y * 256 + x) * 4
    pixels.data[i] = (dx / length * 0.5 + 0.5) * 255
    pixels.data[i + 1] = (dy / length * 0.5 + 0.5) * 255
    pixels.data[i + 2] = (1 / length * 0.5 + 0.5) * 255
    pixels.data[i + 3] = 255
  }
  ctx.putImageData(pixels, 0, 0)
  normalCanvas = canvas
  return canvas
}

// 撒细噪点模拟矿物颜料颗粒
const speckle = (ctx, w, h, count, alpha = 0.05) => {
  const random = seededRandom(w + h + count)
  for (let i = 0; i < count; i++) {
    const dark = random() > 0.5
    ctx.fillStyle = dark ? `rgba(60,40,25,${alpha})` : `rgba(255,240,210,${alpha})`
    const r = random() * 1.6 + 0.4
    ctx.beginPath()
    ctx.arc(random() * w, random() * h, r, 0, Math.PI * 2)
    ctx.fill()
  }
}

// 描金边
const goldStroke = (ctx, width = 7) => {
  ctx.strokeStyle = GLAZE.gold
  ctx.lineWidth = width
  ctx.lineCap = 'round'
  ctx.lineJoin = 'round'
}

// 回纹带（简化雷纹）
const keyFretBand = (ctx, y, w, h, color) => {
  ctx.fillStyle = color
  const cell = h * 0.9
  const n = Math.floor(w / cell)
  const size = cell * 0.42
  for (let i = 0; i < n; i++) {
    const x = i * cell + cell * 0.29
    ctx.fillRect(x, y + h * 0.2, size, size * 0.16)
    ctx.fillRect(x, y + h * 0.2, size * 0.16, size * 0.62)
    ctx.fillRect(x, y + h * 0.66, size * 0.66, size * 0.16)
  }
}

// 牡丹团花
const peony = (ctx, cx, cy, r, petal, core) => {
  ctx.save()
  ctx.translate(cx, cy)
  for (let ring = 0; ring < 3; ring++) {
    const n = 8 - ring * 2
    const rr = r * (0.62 - ring * 0.16)
    ctx.fillStyle = ring === 0 ? petal : ring === 1 ? '#d98a78' : core
    for (let i = 0; i < n; i++) {
      const a = (i / n) * Math.PI * 2 + ring * 0.3
      ctx.beginPath()
      ctx.ellipse(Math.cos(a) * rr, Math.sin(a) * rr, r * 0.26, r * 0.18, a, 0, Math.PI * 2)
      ctx.fill()
    }
  }
  ctx.fillStyle = GLAZE.goldLight
  ctx.beginPath()
  ctx.arc(0, 0, r * 0.13, 0, Math.PI * 2)
  ctx.fill()
  // 叶
  ctx.fillStyle = GLAZE.green
  for (let i = 0; i < 4; i++) {
    const a = i * Math.PI / 2 + Math.PI / 4
    ctx.beginPath()
    ctx.ellipse(Math.cos(a) * r * 0.95, Math.sin(a) * r * 0.95, r * 0.3, r * 0.13, a, 0, Math.PI * 2)
    ctx.fill()
  }
  ctx.restore()
}

// 云纹小螺旋
const cloudSpiral = (ctx, x, y, r, color) => {
  ctx.save()
  ctx.strokeStyle = color
  ctx.lineWidth = r * 0.28
  ctx.lineCap = 'round'
  ctx.beginPath()
  for (let a = 0; a < Math.PI * 2.6; a += 0.15) {
    const rr = (a / (Math.PI * 2.6)) * r
    const px = x + Math.cos(a) * rr
    const py = y + Math.sin(a) * rr
    a === 0 ? ctx.moveTo(px, py) : ctx.lineTo(px, py)
  }
  ctx.stroke()
  ctx.restore()
}

// ============================================================
// 袍服贴图（Lathe 用，使用方 rotation.y=PI，前襟在 u=0.5）
// ============================================================
export function robeTexture(kind = 'red') {
  const w = 1024
  const h = 1024
  const c = makeCanvas(w, h)
  const ctx = c.getContext('2d')

  if (kind === 'cream') {
    // 寿星米白袍
    const g = ctx.createLinearGradient(0, 0, 0, h)
    g.addColorStop(0, '#f2e8d4')
    g.addColorStop(0.5, GLAZE.cream)
    g.addColorStop(1, '#ddd0b6')
    ctx.fillStyle = g
    ctx.fillRect(0, 0, w, h)
    speckle(ctx, w, h, 2600, 0.05)

    // 下摆海水江崖纹
    ctx.fillStyle = GLAZE.cobalt
    ctx.fillRect(0, h - 132, w, 100)
    ctx.fillStyle = '#e9e2d0'
    for (let x = -40; x < w + 40; x += 90) {
      ctx.beginPath()
      ctx.arc(x, h - 32, 46, Math.PI, 0)
      ctx.fill()
    }
    ctx.fillStyle = GLAZE.cobalt
    for (let x = -40; x < w + 40; x += 90) {
      ctx.beginPath()
      ctx.arc(x, h - 30, 30, Math.PI, 0)
      ctx.fill()
    }
    goldStroke(ctx, 8)
    ctx.beginPath(); ctx.moveTo(0, h - 132); ctx.lineTo(w, h - 132); ctx.stroke()

    // 领口金纹
    ctx.fillStyle = GLAZE.gold
    ctx.fillRect(0, 0, w, 26)
    keyFretBand(ctx, 30, w, 60, 'rgba(80,60,30,0.55)')

    // 胸前寿字团（u=0.5 → x=512）
    ctx.fillStyle = GLAZE.vermilion
    ctx.beginPath(); ctx.arc(w / 2, h * 0.42, 92, 0, Math.PI * 2); ctx.fill()
    goldStroke(ctx, 10)
    ctx.beginPath(); ctx.arc(w / 2, h * 0.42, 92, 0, Math.PI * 2); ctx.stroke()
    ctx.fillStyle = GLAZE.goldLight
    ctx.font = 'bold 120px KaiTi, STKaiti, serif'
    ctx.textAlign = 'center'
    ctx.textBaseline = 'middle'
    ctx.fillText('寿', w / 2, h * 0.42 + 6)
    cloudSpiral(ctx, w * 0.2, h * 0.4, 46, 'rgba(61,107,148,0.35)')
    cloudSpiral(ctx, w * 0.8, h * 0.4, 46, 'rgba(61,107,148,0.35)')
  } else {
    // 阿福朱红袍
    const g = ctx.createLinearGradient(0, 0, 0, h)
    g.addColorStop(0, GLAZE.vermilionDark)
    g.addColorStop(0.45, GLAZE.vermilion)
    g.addColorStop(1, '#99302a')
    ctx.fillStyle = g
    ctx.fillRect(0, 0, w, h)
    speckle(ctx, w, h, 3000, 0.055)

    // 下摆/领口金边+回纹
    ctx.fillStyle = GLAZE.gold
    ctx.fillRect(0, 0, w, 30)
    ctx.fillRect(0, h - 46, w, 30)
    keyFretBand(ctx, h - 118, w, 72, 'rgba(227,197,120,0.85)')
    goldStroke(ctx, 6)
    ctx.beginPath(); ctx.moveTo(0, h - 48); ctx.lineTo(w, h - 48); ctx.stroke()
    ctx.beginPath(); ctx.moveTo(0, 32); ctx.lineTo(w, 32); ctx.stroke()

    // 前襟牡丹团花（u=0.5）
    peony(ctx, w / 2, h * 0.46, 118, '#e8b0a6', GLAZE.gold)
    // 两侧云纹（侧面 u≈0.25/0.75）
    cloudSpiral(ctx, w * 0.24, h * 0.36, 52, 'rgba(227,197,120,0.75)')
    cloudSpiral(ctx, w * 0.76, h * 0.62, 52, 'rgba(227,197,120,0.75)')
    cloudSpiral(ctx, w / 2, h * 0.82, 42, 'rgba(47,125,94,0.8)')
  }

  return toTexture(c)
}

// ============================================================
// 阿福开脸贴图（Sphere，正面 u=0.25）
// ============================================================
export function afuFaceTexture(kind = 'afu') {
  const w = 1024
  const h = 512
  const c = makeCanvas(w, h)
  const ctx = c.getContext('2d')
  const cx = w * 0.25

  // 肤底+正面柔光
  const g = ctx.createRadialGradient(cx, h * 0.5, 40, cx, h * 0.5, w * 0.32)
  g.addColorStop(0, '#f8e7cb')
  g.addColorStop(0.7, GLAZE.skin)
  g.addColorStop(1, '#dfc39e')
  ctx.fillStyle = g
  ctx.fillRect(0, 0, w, h)
  speckle(ctx, w, h, 1800, 0.04)

  // 刘海（三小撮黑发弧线）
  ctx.strokeStyle = GLAZE.ink
  ctx.lineWidth = 20
  ctx.lineCap = 'round'
  for (const dx of kind === 'shouxing' ? [] : [-70, 0, 70]) {
    ctx.beginPath()
    ctx.arc(cx + dx, h * 0.22, 42, Math.PI * 1.08, Math.PI * 1.92)
    ctx.stroke()
  }

  // 弯眉
  ctx.strokeStyle = kind === 'shouxing' ? GLAZE.white : GLAZE.ink
  ctx.lineWidth = 13
  for (const dx of [-72, 72]) {
    ctx.beginPath()
    ctx.arc(cx + dx, h * 0.4, 40, Math.PI * 1.12, Math.PI * 1.85)
    ctx.stroke()
  }

  // 笑眼（两道弯月弧）
  ctx.strokeStyle = GLAZE.ink
  ctx.lineWidth = 15
  for (const dx of [-72, 72]) {
    ctx.beginPath()
    ctx.arc(cx + dx, h * 0.47, 30, Math.PI * 1.12, Math.PI * 1.9)
    ctx.stroke()
  }

  // 腮红（两团圆艳）
  for (const dx of [-118, 118]) {
    const rg = ctx.createRadialGradient(cx + dx, h * 0.6, 4, cx + dx, h * 0.6, 46)
    rg.addColorStop(0, 'rgba(226,100,90,0.55)')
    rg.addColorStop(1, 'rgba(226,148,141,0)')
    ctx.fillStyle = rg
    ctx.beginPath()
    ctx.arc(cx + dx, h * 0.6, 46, 0, Math.PI * 2)
    ctx.fill()
  }

  // 鼻（两点小红）
  ctx.fillStyle = 'rgba(160,80,60,0.5)'
  ctx.beginPath(); ctx.arc(cx - 8, h * 0.6, 4, 0, Math.PI * 2); ctx.fill()
  ctx.beginPath(); ctx.arc(cx + 8, h * 0.6, 4, 0, Math.PI * 2); ctx.fill()

  // 笑口（朱红弯弧+下唇高光）
  ctx.strokeStyle = GLAZE.vermilion
  ctx.lineWidth = 16
  ctx.beginPath()
  ctx.arc(cx, h * 0.66, 34, Math.PI * 0.18, Math.PI * 0.82)
  ctx.stroke()
  ctx.strokeStyle = 'rgba(120,30,25,0.5)'
  ctx.lineWidth = 5
  ctx.beginPath()
  ctx.arc(cx, h * 0.665, 34, Math.PI * 0.2, Math.PI * 0.8)
  ctx.stroke()

  if (kind === 'shouxing') {
    ctx.strokeStyle = 'rgba(133,94,63,0.32)'
    ctx.lineWidth = 3
    for (const y of [0.25, 0.29, 0.33]) {
      ctx.beginPath(); ctx.ellipse(cx, h * y, 66, 10, 0, 0, Math.PI); ctx.stroke()
    }
    for (const sx of [-1, 1]) {
      ctx.beginPath(); ctx.moveTo(cx + sx * 109, h * 0.46); ctx.lineTo(cx + sx * 130, h * 0.43); ctx.stroke()
      ctx.beginPath(); ctx.moveTo(cx + sx * 109, h * 0.49); ctx.lineTo(cx + sx * 130, h * 0.5); ctx.stroke()
    }
  }
  return toTexture(c)
}

// ============================================================
// 蚕猫开脸贴图
// ============================================================
export function catFaceTexture() {
  const w = 1024
  const h = 512
  const c = makeCanvas(w, h)
  const ctx = c.getContext('2d')
  const cx = w * 0.25

  const g = ctx.createRadialGradient(cx, h * 0.52, 30, cx, h * 0.52, w * 0.34)
  g.addColorStop(0, '#fbf7ec')
  g.addColorStop(0.75, GLAZE.white)
  g.addColorStop(1, '#e3dac6')
  ctx.fillStyle = g
  ctx.fillRect(0, 0, w, h)
  speckle(ctx, w, h, 1600, 0.04)

  // 额头条纹（民间彩条）
  const stripeColors = [GLAZE.vermilion, GLAZE.green, GLAZE.gold, GLAZE.cobalt]
  stripeColors.forEach((col, i) => {
    ctx.strokeStyle = col
    ctx.lineWidth = 15
    ctx.lineCap = 'round'
    ctx.beginPath()
    ctx.moveTo(cx - 54 + i * 36, h * 0.2)
    ctx.quadraticCurveTo(cx - 40 + i * 30, h * 0.3, cx - 30 + i * 22, h * 0.37)
    ctx.stroke()
  })

  // 怒目圆睁（大眼白+黑瞳+红眼眶）
  for (const dx of [-62, 62]) {
    ctx.fillStyle = GLAZE.vermilion
    ctx.beginPath(); ctx.ellipse(cx + dx, h * 0.48, 36, 40, 0, 0, Math.PI * 2); ctx.fill()
    ctx.fillStyle = '#fffdf5'
    ctx.beginPath(); ctx.ellipse(cx + dx, h * 0.48, 28, 32, 0, 0, Math.PI * 2); ctx.fill()
    ctx.fillStyle = GLAZE.ink
    ctx.beginPath(); ctx.arc(cx + dx + 4, h * 0.5, 13, 0, Math.PI * 2); ctx.fill()
    ctx.fillStyle = '#fff'
    ctx.beginPath(); ctx.arc(cx + dx + 9, h * 0.46, 4.5, 0, Math.PI * 2); ctx.fill()
  }

  // 红鼻
  ctx.fillStyle = GLAZE.vermilion
  ctx.beginPath()
  ctx.moveTo(cx, h * 0.6)
  ctx.lineTo(cx - 14, h * 0.66)
  ctx.lineTo(cx + 14, h * 0.66)
  ctx.closePath()
  ctx.fill()

  // 嘴（人字）
  ctx.strokeStyle = GLAZE.ink
  ctx.lineWidth = 6
  ctx.lineCap = 'round'
  ctx.beginPath(); ctx.moveTo(cx, h * 0.67); ctx.lineTo(cx, h * 0.71); ctx.stroke()
  ctx.beginPath(); ctx.moveTo(cx, h * 0.71); ctx.quadraticCurveTo(cx - 16, h * 0.79, cx - 30, h * 0.72); ctx.stroke()
  ctx.beginPath(); ctx.moveTo(cx, h * 0.71); ctx.quadraticCurveTo(cx + 16, h * 0.79, cx + 30, h * 0.72); ctx.stroke()

  // 胡须点
  ctx.fillStyle = 'rgba(58,43,32,0.6)'
  for (const dx of [-24, 24]) {
    ctx.beginPath(); ctx.arc(cx + dx, h * 0.7, 4, 0, Math.PI * 2); ctx.fill()
  }

  return toTexture(c)
}

// ============================================================
// 蚕猫身体贴图（Sphere，五彩斑块）
// ============================================================
export function catBodyTexture() {
  const w = 1024
  const h = 512
  const c = makeCanvas(w, h)
  const ctx = c.getContext('2d')

  const g = ctx.createLinearGradient(0, 0, 0, h)
  g.addColorStop(0, '#fbf7ec')
  g.addColorStop(1, '#e6dcc8')
  ctx.fillStyle = g
  ctx.fillRect(0, 0, w, h)
  speckle(ctx, w, h, 2000, 0.045)

  // 不规则手绘彩斑（环绕分布）
  const patches = [
    [0.12, 0.35, 110, GLAZE.vermilion], [0.4, 0.28, 90, GLAZE.green],
    [0.62, 0.55, 130, GLAZE.gold], [0.86, 0.4, 96, GLAZE.cobalt],
    [0.28, 0.72, 80, GLAZE.cobalt], [0.74, 0.8, 100, GLAZE.vermilion],
    [0.02, 0.6, 70, GLAZE.green], [0.5, 0.85, 85, GLAZE.green],
  ]
  patches.forEach(([u, v, r, color]) => {
    ctx.fillStyle = color + 'cc'
    ctx.beginPath()
    // 软边斑块
    const x = u * w
    const y = v * h
    for (let i = 0; i <= 10; i++) {
      const a = (i / 10) * Math.PI * 2
      const rr = r * (0.75 + ((i * 37) % 10) / 22)
      const px = x + Math.cos(a) * rr
      const py = y + Math.sin(a) * rr * 0.8
      i === 0 ? ctx.moveTo(px, py) : ctx.lineTo(px, py)
    }
    ctx.closePath()
    ctx.fill()
  })

  return toTexture(c)
}
