import assert from 'node:assert/strict'
import { readFileSync, readdirSync } from 'node:fs'
import { createHash } from 'node:crypto'
import { loadImage, createCanvas } from '@napi-rs/canvas'
const root = new URL('../public/models/', import.meta.url)
const files = [...readdirSync(root).filter(f => f.endsWith('.glb')),
  ...readdirSync(new URL('parts/', root)).map(f => 'parts/' + f).filter(f => f.endsWith('.glb'))]
assert.equal(files.length, 8)
const manifest = JSON.parse(readFileSync(new URL('manifest.json', root), 'utf8'))
assert.equal(manifest.assets.length, files.length)
for (const file of files) {
  const data = readFileSync(new URL(file, root))
  const asset = manifest.assets.find(item => item.file === file)
  assert.ok(asset, `${file}: 缺少清单记录`)
  assert.equal(asset.bytes, data.length)
  assert.equal(asset.sha256, createHash('sha256').update(data).digest('hex'), `${file}: 资产与清单不一致，请重新导出`)
  assert.equal(data.toString('ascii', 0, 4), 'glTF')
  assert.equal(data.readUInt32LE(8), data.length)
  const length = data.readUInt32LE(12)
  const gltf = JSON.parse(data.toString('utf8', 20, 20 + length))
  const binary = data.subarray(28 + length)
  assert.ok(gltf.meshes.length)
  assert.ok(gltf.materials.some(material => material.normalTexture), `${file}: 缺少陶土法线贴图`)
  for (const im of gltf.images || []) {
    const view = gltf.bufferViews[im.bufferView]
    const start = view.byteOffset || 0
    const decoded = await loadImage(binary.subarray(start, start + view.byteLength))
    const canvas = createCanvas(decoded.width, decoded.height), ctx = canvas.getContext('2d')
    ctx.drawImage(decoded, 0, 0)
    const pixels = ctx.getImageData(0, 0, canvas.width, canvas.height).data
    assert.ok(pixels.some((v, i) => i % 4 === 3 && v !== 0), `${file}: 空贴图`)
    assert.ok(pixels.some((v, i) => i % 4 !== 3 && v !== 0), `${file}: 黑贴图`)
  }
  console.log(`通过 ${file}: ${gltf.images?.length || 0} 张有效贴图`)
}
