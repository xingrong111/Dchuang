import fs from 'node:fs/promises'
import path from 'node:path'
import { createHash } from 'node:crypto'
import { createCanvas, loadImage } from '@napi-rs/canvas'
import { MeshoptSimplifier } from 'meshoptimizer'
import { Box3, Vector3, Object3D, Matrix4 } from 'three'
const [id, sourceFile] = process.argv.slice(2)
if (!id || !sourceFile) throw Error('Usage: node scripts/import-hunyuan.mjs <product-id> <original.glb>')
const folder = path.resolve('public/models/products')
const manifest = JSON.parse(await fs.readFile(path.join(folder, 'manifest.json'), 'utf8'))
const asset = manifest.assets.find(a => a.id === id)
if (!asset) throw Error('Unknown product')
const source = await fs.readFile(sourceFile)
if (source.readUInt32LE(0) !== 0x46546c67 || source.readUInt32LE(4) !== 2 || source.readUInt32LE(8) !== source.length) throw Error('Invalid GLB')
const length = source.readUInt32LE(12), json = JSON.parse(source.subarray(20,20+length).toString())
const bin = source.subarray(28+length)
if (json.buffers.length !== 1 || json.buffers[0].uri || (json.images||[]).some(i=>i.uri)) throw Error('Only self-contained GLB supported')
const world = new Box3(), objects = json.nodes.map(n=>{const o=new Object3D();if(n.matrix){o.applyMatrix4(new Matrix4().fromArray(n.matrix))}else{if(n.translation)o.position.fromArray(n.translation);if(n.rotation)o.quaternion.fromArray(n.rotation);if(n.scale)o.scale.fromArray(n.scale)}return o})
json.nodes.forEach((n,i)=>(n.children||[]).forEach(c=>objects[i].add(objects[c])))
const root=new Object3D();for(const i of json.scenes[json.scene||0].nodes)root.add(objects[i]);root.updateMatrixWorld(true)
json.nodes.forEach((n,i)=>{if(n.mesh!==undefined)for(const p of json.meshes[n.mesh].primitives){const a=json.accessors[p.attributes.POSITION];if(!a.min||!a.max)throw Error('Position bounds missing');world.union(new Box3(new Vector3().fromArray(a.min),new Vector3().fromArray(a.max)).applyMatrix4(objects[i].matrixWorld))}})
const size=world.getSize(new Vector3()), centre=world.getCenter(new Vector3()), scale=(asset.bounds.max[1]-asset.bounds.min[1])/size.y
if(!Number.isFinite(scale)||scale<=0)throw Error('Invalid model dimensions')
const node=json.nodes.length
json.nodes.push({name:id+'-display-metres',children:json.scenes[json.scene||0].nodes,scale:[scale,scale,scale],translation:[-centre.x*scale,-world.min.y*scale,-centre.z*scale],extras:{units:'metres',source:'Tencent Hunyuan 3D V3.1',manufacturingReady:false}})
json.scenes[json.scene||0].nodes=[node]
const replacements=new Map()
await MeshoptSimplifier.ready
for(const mesh of json.meshes)for(const primitive of mesh.primitives){
 if(primitive.indices===undefined)continue
 const index=json.accessors[primitive.indices],position=json.accessors[primitive.attributes.POSITION]
 if(index.count<=300000)continue
 const iv=json.bufferViews[index.bufferView],pv=json.bufferViews[position.bufferView]
 if(iv.byteStride||pv.byteStride||position.componentType!==5126||index.componentType!==5125)throw Error('High-poly input requires packed float positions and uint32 indices')
 const indices=new Uint32Array(Uint8Array.from(bin.subarray((iv.byteOffset||0)+(index.byteOffset||0),(iv.byteOffset||0)+(index.byteOffset||0)+index.count*4)).buffer)
 const positions=new Float32Array(Uint8Array.from(bin.subarray((pv.byteOffset||0)+(position.byteOffset||0),(pv.byteOffset||0)+(position.byteOffset||0)+position.count*12)).buffer)
 const [simplified]=MeshoptSimplifier.simplify(indices,positions,3,150000,0.005,['LockBorder'])
 replacements.set(index.bufferView,Buffer.from(simplified.buffer,simplified.byteOffset,simplified.byteLength));index.count=simplified.length;index.byteOffset=0;delete index.min;delete index.max
}
const chunks=[];let offset=0
for(let i=0;i<json.bufferViews.length;i++){
 const view=json.bufferViews[i];let data=replacements.get(i)||bin.subarray(view.byteOffset||0,(view.byteOffset||0)+view.byteLength)
 const image=(json.images||[]).find(im=>im.bufferView===i)
 if(image){const bitmap=await loadImage(data),ratio=Math.min(1,1024/Math.max(bitmap.width,bitmap.height)),canvas=createCanvas(Math.max(1,Math.round(bitmap.width*ratio)),Math.max(1,Math.round(bitmap.height*ratio)));canvas.getContext('2d').drawImage(bitmap,0,0,canvas.width,canvas.height);data=await canvas.encode('png');image.mimeType='image/png'}
 view.byteOffset=offset;view.byteLength=data.length;chunks.push(data);offset+=data.length;const pad=(4-offset%4)%4;if(pad){chunks.push(Buffer.alloc(pad));offset+=pad}
}
json.buffers[0].byteLength=offset
json.asset.extras={...(json.asset.extras||{}),source:'https://3d.hunyuan.tencent.com/',modelVersion:'3.1',inputImage:id+'-studio.webp',originalSha256:createHash('sha256').update(source).digest('hex'),textureMaxSize:1024}
let encoded=Buffer.from(JSON.stringify(json));encoded=Buffer.concat([encoded,Buffer.alloc((4-encoded.length%4)%4,0x20)])
const binary=Buffer.concat(chunks),header=Buffer.alloc(20);header.writeUInt32LE(0x46546c67,0);header.writeUInt32LE(2,4);header.writeUInt32LE(28+encoded.length+binary.length,8);header.writeUInt32LE(encoded.length,12);header.writeUInt32LE(0x4e4f534a,16)
const bh=Buffer.alloc(8);bh.writeUInt32LE(binary.length,0);bh.writeUInt32LE(0x004e4942,4)
const output=Buffer.concat([header,encoded,bh,binary])
asset.source='tencent-hunyuan-3.1';asset.bytes=output.length;asset.sha256=createHash('sha256').update(output).digest('hex');asset.originalSha256=json.asset.extras.originalSha256;asset.originalFile=path.basename(sourceFile);asset.meshes=json.meshes.length;asset.triangles=json.meshes.reduce((s,m)=>s+m.primitives.reduce((t,p)=>t+(p.indices===undefined?json.accessors[p.attributes.POSITION].count:json.accessors[p.indices].count)/3,0),0);asset.bounds={min:[-size.x*scale/2,0,-size.z*scale/2],max:[size.x*scale/2,size.y*scale,size.z*scale/2]};asset.generatedAt=new Date().toISOString()
await fs.writeFile(path.join(folder,asset.file),output)
await fs.writeFile(path.join(folder,'manifest.json'),JSON.stringify(manifest,null,2)+'\n')
console.log(JSON.stringify({id,originalBytes:source.length,webBytes:output.length,triangles:asset.triangles,bounds:asset.bounds}))
