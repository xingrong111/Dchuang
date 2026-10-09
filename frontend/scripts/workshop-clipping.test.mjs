import {test} from 'node:test'
import assert from 'node:assert/strict'
import * as THREE from 'three'
import { shapeShoulderTransition } from '../src/three/shoulderTransition.js'

test('肩颈过渡保留衣领高度和下半身，不破坏纹理坐标',()=>{
 const group=new THREE.Group(),geometry=new THREE.BoxGeometry(1,2,.5,10,20,2),mesh=new THREE.Mesh(geometry)
 mesh.position.y=1;group.add(mesh)
 const uv=Array.from(geometry.attributes.uv.array),before=Array.from(geometry.attributes.position.array)
 shapeShoulderTransition(group)
 const position=geometry.attributes.position
 let dropped=0
 for(let i=0;i<position.count;i++){
   const x=before[i*3],y=before[i*3+1]
   if(y<.8)assert.equal(position.getY(i),y)
   if(y===1&&Math.abs(x)>.4){assert.ok(position.getY(i)<y);dropped++}
   if(y===1&&Math.abs(x)<.1)assert.equal(position.getY(i),y)
 }
 assert.ok(dropped>0);assert.deepEqual(Array.from(geometry.attributes.uv.array),uv)
})
import {clipPart} from '../src/three/clipPart.js'
test('body clipping removes upper region, preserves UVs and closes the neck',()=>{
 const mesh=new THREE.Mesh(new THREE.BoxGeometry(2,2,2),new THREE.MeshPhysicalMaterial({color:'#cc6644'}));mesh.position.y=1
 const part=clipPart(mesh,'y',1,true,'#e4c7a6'),bounds=new THREE.Box3().setFromObject(part)
 assert.equal(bounds.min.y,0);assert.equal(bounds.max.y,1)
 const outer=part.children.find(c=>c.geometry.attributes.uv);assert.ok(outer)
 for(const v of outer.geometry.attributes.uv.array)assert.ok(Number.isFinite(v))
 let area=0
 for(const cap of part.children.filter(c=>!c.geometry.attributes.uv)){
  const p=cap.geometry.attributes.position
  for(let i=0;i<p.count;i+=3){const a=new THREE.Vector3().fromBufferAttribute(p,i),b=new THREE.Vector3().fromBufferAttribute(p,i+1),c=new THREE.Vector3().fromBufferAttribute(p,i+2);assert.equal(a.y,1);area+=b.sub(a).cross(c.sub(a)).length()/2}
 }
 assert.ok(Math.abs(area-4)<1e-5,'cut face must cover the original neck section')
 assert.equal(new THREE.Box3().setFromObject(mesh).max.y,2,'source remains intact')
 assert.notEqual(outer.material,mesh.material)
})
test('left and right arm clipping excludes the torso region',()=>{
 const mesh=new THREE.Mesh(new THREE.BoxGeometry(2,2,2),new THREE.MeshStandardMaterial())
 const left=clipPart(mesh,'x',-.3,true,'#e4c7a6'),right=clipPart(mesh,'x',.3,false,'#e4c7a6')
 assert.ok(new THREE.Box3().setFromObject(left).max.x<=-.3+1e-6)
 assert.ok(new THREE.Box3().setFromObject(right).min.x>=.3-1e-6)
 assert.ok(left.children.length>1&&right.children.length>1)
})
