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
import { mkdirSync, writeFileSync, existsSync, readFileSync } from 'node:fs'
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
const MODELS_DIR = join(__dirname, '..', 'public', 'models', 'products')
const { PRODUCT_IDS, createProduct } = await import(pathToFileURL(join(__dirname,'..','src','three','productFactory.js')).href)
const priorPath=join(MODELS_DIR,'manifest.json')
const prior=existsSync(priorPath)?JSON.parse(readFileSync(priorPath,'utf8')).assets:[]
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

for (const id of PRODUCT_IDS) {
 const imported=prior.find(a=>a.id===id&&a.source!=='procedural')
 if(imported){assets.push(imported);console.log('Preserving imported asset: '+id);continue}
 await exportGlb(createProduct(id),join(MODELS_DIR,id+'.glb'),id,id,'product')
}
writeFileSync(join(MODELS_DIR,'manifest.json'),JSON.stringify({version:1,units:'metres',manufacturingReady:false,assets},null,2))
