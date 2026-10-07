import { test } from 'node:test'
import assert from 'node:assert/strict'
import fs from 'node:fs'
import { createHash } from 'node:crypto'
const folder = new URL('../public/models/products/', import.meta.url)
const manifest = JSON.parse(fs.readFileSync(new URL('manifest.json', folder)))
for (const asset of manifest.assets) test(`product GLB: ${asset.id}`, () => {
  const buffer = fs.readFileSync(new URL(asset.file, folder))
  assert.equal(buffer.readUInt32LE(0), 0x46546c67)
  assert.equal(buffer.readUInt32LE(4), 2)
  assert.equal(buffer.readUInt32LE(8), buffer.length)
  assert.equal(createHash('sha256').update(buffer).digest('hex'), asset.sha256)
  const json = JSON.parse(buffer.subarray(20, 20 + buffer.readUInt32LE(12)).toString())
  const binaryLength=buffer.length-28-buffer.readUInt32LE(12)
  for(const view of json.bufferViews)assert.ok((view.byteOffset||0)+view.byteLength<=binaryLength,'buffer views stay inside GLB binary')
  if(asset.source==='tencent-hunyuan-3.1'){
    const original=fs.readFileSync(new URL('../../operations/deliverables/hunyuan/'+asset.originalFile,import.meta.url))
    assert.equal(createHash('sha256').update(original).digest('hex'),asset.originalSha256,'original model provenance')
  }
  assert.ok(json.meshes.length)
  assert.ok(json.nodes.some(node => node.extras?.units === 'metres'))
  for (const image of json.images || []) assert.ok(Number.isInteger(image.bufferView), 'textures must be embedded')
  for (const accessor of json.accessors) {
    for (const value of [...(accessor.min || []), ...(accessor.max || [])]) assert.ok(Number.isFinite(value))
  }
  const extents = asset.bounds.max.map((max, i) => max - asset.bounds.min[i])
  assert.ok(extents.every(value => value > 0 && value < 0.6), 'plausible desktop product dimensions, in metres')
})
