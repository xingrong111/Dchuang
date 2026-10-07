// ============================================================
// 智绘锡承 - 惠山泥人 3D 资产导出脚本（Node 端）
// 位置: frontend/scripts/export-models.mjs
//
// 用法: cd frontend && node scripts/export-models.mjs
// 产出: public/models/{daafu,canmao,shouxing}.glb
//       public/models/parts/{afu_head,afu_body,afu_arms,clay_base,lion_beast}.glb
// 依赖: three（GLTFExporter 在 Node 需要 window/FileReader polyfill）
// ============================================================
import * as THREE from 'three'
import { GLTFExporter } from 'three/examples/jsm/exporters/GLTFExporter.js'
import { mkdirSync, writeFileSync } from 'node:fs'
import { dirname, join } from 'node:path'
import { fileURLToPath, pathToFileURL } from 'node:url'
import { createHash } from 'node:crypto'

// --- Node 环境 polyfill ---
// 1) document.createElement('canvas')：用 @napi-rs/canvas 提供真实 2D 绘制，
//    使程序化彩绘贴图（textureFactory.js）能在 Node 端生成并烘焙进 GLB。
import { createCanvas, Canvas, ImageData } from '@napi-rs/canvas'

// GLTFExporter 通过 instanceof HTMLCanvasElement 选择 drawImage 分支
if (typeof globalThis.HTMLCanvasElement === 'undefined') {
  globalThis.HTMLCanvasElement = Canvas
}
// napi Canvas 自带 .data，会被误判为 DataTexture 而走 ImageData 分支
if (typeof globalThis.ImageData === 'undefined') {
  globalThis.ImageData = ImageData
}

if (typeof globalThis.document === 'undefined') {
  globalThis.document = {
    createElement(tag) {
      if (tag === 'canvas') {
        const c = createCanvas(32, 32)
        // napi 的 data 是函数，Exporter 会把它误当 RGBA 数组，导出全零贴图。
        // 隐藏该属性，让 Exporter 使用真实 Canvas drawImage 路径。
        Object.defineProperty(c, 'data', { value: undefined })
        // GLTFExporter binary 模式调用 canvas.toBlob；napi 用 encode 实现
        c.toBlob = function (cb) {
          this.encode('png').then(buf => cb(new Blob([buf], { type: 'image/png' })))
        }
        return c
      }
      return {}
    },
  }
}

// 2) FileReader（GLTFExporter 读取 Blob 转 ArrayBuffer）
if (typeof globalThis.window === 'undefined') globalThis.window = globalThis
if (typeof globalThis.FileReader === 'undefined') {
  globalThis.FileReader = class {
    readAsArrayBuffer(blob) {
      Promise.resolve(blob.arrayBuffer ? blob.arrayBuffer() : new ArrayBuffer(0))
        .then(buf => {
          this.result = buf
          if (this.onloadend) this.onloadend({ target: this })
          if (this.onload) this.onload({ target: this })
        })
        .catch(err => this.onerror && this.onerror(err))
    }
  }
}

const __dirname = dirname(fileURLToPath(import.meta.url))
const MODELS_DIR = join(__dirname, '..', 'public', 'models')
const PARTS_DIR = join(MODELS_DIR, 'parts')

const { CLASSIC_MODELS, PART_CATALOG } = await import(
  pathToFileURL(join(__dirname, '..', 'src', 'three', 'modelFactory.js')).href
)

const assets = []
function exportGlb(object3d, outPath, id, name, kind) {
  return new Promise((resolve, reject) => {
    const exporter = new GLTFExporter()
    exporter.parse(
      object3d,
      result => {
        // binary: true 时 result 为 ArrayBuffer
        const buffer = result instanceof ArrayBuffer ? Buffer.from(result) : Buffer.from(JSON.stringify(result))
        mkdirSync(dirname(outPath), { recursive: true })
        writeFileSync(outPath, buffer)
        const bounds = new THREE.Box3().setFromObject(object3d)
        let triangles = 0, meshes = 0
        object3d.traverse(child => {
          if (!child.isMesh) return
          meshes++
          triangles += (child.geometry.index?.count || child.geometry.attributes.position.count) / 3
        })
        assets.push({ id, name, kind, file: `${kind === 'part' ? 'parts/' : ''}${id}.glb`,
          source: 'procedural', bytes: buffer.length, sha256: createHash('sha256').update(buffer).digest('hex'),
          meshes, triangles, bounds: { min: bounds.min.toArray(), max: bounds.max.toArray() },
          anchors: object3d.userData.attachPoints || [] })
        console.log(`  [OK] ${outPath} (${(buffer.length / 1024).toFixed(1)} KB)`)
        resolve()
      },
      err => reject(err),
      { binary: true }
    )
  })
}

async function main() {
  console.log('开始导出惠山泥人 3D 资产...')

  for (const [id, item] of Object.entries(CLASSIC_MODELS)) {
    const model = item.create()
    model.updateMatrixWorld(true)
    model.userData = { ...model.userData, source: 'procedural', assetId: id, assetVersion: 3 }
    await exportGlb(model, join(MODELS_DIR, `${id}.glb`), id, item.name, 'classic')
  }

  for (const part of PART_CATALOG) {
    const model = part.create()
    model.updateMatrixWorld(true)
    model.userData = { ...model.userData, source: 'procedural', partId: part.id, assetVersion: 3 }
    await exportGlb(model, join(PARTS_DIR, `${part.id}.glb`), part.id, part.name, 'part')
  }

  writeFileSync(join(MODELS_DIR, 'manifest.json'), JSON.stringify({ version: 3, assets }, null, 2))
  console.log('全部导出完成，已生成 manifest.json。')
}

main().catch(err => {
  console.error('导出失败:', err)
  process.exit(1)
})
