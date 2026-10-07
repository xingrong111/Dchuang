import {test} from 'node:test'
import assert from 'node:assert/strict'
import fs from 'node:fs'
import {createHash} from 'node:crypto'
const folder=new URL('../public/models/workshop/',import.meta.url),manifest=JSON.parse(fs.readFileSync(new URL('manifest.json',folder)))
test('twenty-eight distinct sourced workshop models',()=>{
 assert.equal(manifest.assets.length,28)
 assert.equal(new Set(manifest.assets.map(a=>a.sha256)).size,28)
})
for(const asset of manifest.assets)test('workshop GLB '+asset.id,()=>{
 const buffer=fs.readFileSync(new URL(asset.file,folder)),original=fs.readFileSync(new URL('../../operations/deliverables/workshop-hunyuan/'+asset.originalFile,import.meta.url))
 assert.equal(buffer.readUInt32LE(0),0x46546c67);assert.equal(buffer.readUInt32LE(8),buffer.length)
 assert.equal(createHash('sha256').update(buffer).digest('hex'),asset.sha256)
 assert.equal(createHash('sha256').update(original).digest('hex'),asset.originalSha256)
 const json=JSON.parse(buffer.subarray(20,20+buffer.readUInt32LE(12))),binaryLength=buffer.length-28-buffer.readUInt32LE(12)
 assert.ok(asset.triangles>10000&&asset.triangles<55000)
 assert.ok(json.meshes.length&&json.images.length)
 for(const image of json.images)assert.ok(Number.isInteger(image.bufferView)&&!image.uri)
 for(const view of json.bufferViews)assert.ok((view.byteOffset||0)+view.byteLength<=binaryLength)
 for(const accessor of json.accessors)for(const bound of [...(accessor.min||[]),...(accessor.max||[])])assert.ok(Number.isFinite(bound))
 assert.equal(json.asset.extras.source,'https://3d.hunyuan.tencent.com/')
})
