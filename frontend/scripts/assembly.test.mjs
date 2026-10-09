import { test } from 'node:test'
import assert from 'node:assert/strict'
import * as THREE from 'three'
import { findConnection, attachPart, alignConnection, rebuildConnections, connectAvailableParts, releasePart, fittedHeadScale } from '../src/three/assembly.js'
import { neckSocket } from '../src/three/partSockets.js'
import { captureAssembly, inspectAssembly, reviewAndRepair, restoreAssembly } from '../src/three/assemblyReview.js'

test('装配复核纠正夸张头部和倾斜，允许恢复用户原始姿态', () => {
 const body=part('afu_body','top',[0,1.4,0]),head=part('afu_head','bottom',[0,0,0])
 body.userData.category='body';body.userData.dimensions={width:1,height:1.35,shoulderWidth:.7,headHeight:.27}
 head.userData.category='head';head.userData.dimensions={width:1,height:1}
 attachPart(head,findConnection(head,[body]));head.scale.setScalar(2);head.rotation.z=.5
 const root=new THREE.Group();root.add(body)
 assert.ok(inspectAssembly([body,head]).some(issue=>issue.code==='proportion'))
 const result=reviewAndRepair([body,head])
 assert.equal(result.issues.length,0);assert.equal(head.rotation.z,0)
 assert.ok(restoreAssembly(result.snapshot,[body,head]));assert.equal(head.scale.x,2);assert.equal(head.rotation.z,.5)
})
test('缺少身体时保留提示，部件替换后不允许恢复陈旧快照',()=>{
 const head=part('afu_head','bottom',[0,0,0]);head.userData.category='head'
 assert.ok(inspectAssembly([head]).some(issue=>issue.code==='missing-body'))
 assert.equal(restoreAssembly(captureAssembly([head]),[]),false)
})
function part(id, name, position) { const p = new THREE.Group(); p.userData = { partId: id, attachPoints: [{ name, position, used: false }] }; return p }

test('颈部微调保持连接、恢复可见过渡并支持撤销高度',()=>{
 const body=part('afu_body','top',[0,1.4,0]),head=part('afu_head','bottom',[0,0,0])
 body.userData.category='body';body.userData.dimensions={width:1,height:1.35,shoulderWidth:.7,headHeight:.27}
 body.userData.collarPosition=[0,1.35,0];body.userData.neckHeight=.05
 head.userData.category='head';head.userData.dimensions={width:1,height:1}
 const neck=new THREE.Mesh(new THREE.CylinderGeometry(1,1,1),new THREE.MeshStandardMaterial())
 neck.name='neck-joint';neck.userData.adaptiveNeck=true;body.add(neck)
 attachPart(head,findConnection(head,[body]))
 head.userData.neckLift=.03;alignConnection(head)
 assert.ok(Math.abs(head.position.y-(1.4+.03*1.35))<1e-8)
 assert.equal(inspectAssembly([body,head]).length,0)
 neck.visible=false
 assert.ok(inspectAssembly([body,head]).some(issue=>issue.code==='neck'))
 const result=reviewAndRepair([body,head])
 assert.equal(result.issues.length,0);assert.equal(neck.visible,true);assert.equal(head.userData.neckLift,0)
 restoreAssembly(result.snapshot,[body,head]);assert.equal(head.userData.neckLift,.03)
 assert.ok(neck.scale.y>.05)
})

test('配饰与宠物先加入、后加身体和底座，最终分居两侧且落在地面',()=>{
 const root=new THREE.Group()
 const model=(type,category,width,height,anchors)=>{
  const p=new THREE.Group(),mesh=new THREE.Mesh(new THREE.BoxGeometry(width,height,.4),new THREE.MeshStandardMaterial())
  mesh.position.y=height/2;p.add(mesh)
  p.userData={partId:type,category,dimensions:{width,height},attachPoints:anchors.map(([name,position])=>({name,position,used:false}))}
  return p
 }
 const pet=model('lion_beast','pet',.6,.58,[['bottom',[0,0,0]]])
 const accessory=model('accessory','accessory',.4,.65,[['bottom',[0,0,0]]])
 const body=model('afu_body','body',2.4,1.35,[['bottom',[0,0,0]],['companion',[1.2,0,0]],['accessory',[-1.2,0,0]]])
 const base=model('clay_base','base',1.8,.3,[['top',[0,.3,0]],['companion',[.9,0,0]],['accessory',[-.9,0,0]]])
 const parts=[]
 for(const p of [pet,accessory,body,base]){root.add(p);parts.push(p);connectAvailableParts(parts)}
 root.updateMatrixWorld(true)
 assert.equal(pet.parent,base);assert.equal(accessory.parent,base)
 for(const p of [pet,accessory])assert.ok(Math.abs(new THREE.Box3().setFromObject(p).min.y)<1e-7)
 const torso=new THREE.Box3().setFromObject(body),animal=new THREE.Box3().setFromObject(pet),prop=new THREE.Box3().setFromObject(accessory)
 assert.ok(animal.min.x>torso.max.x)
 assert.ok(prop.max.x<torso.min.x)
 body.scale.setScalar(1.3);connectAvailableParts(parts);root.updateMatrixWorld(true)
 assert.ok(new THREE.Box3().setFromObject(pet).min.x>new THREE.Box3().setFromObject(body).max.x)
})

test('头部受真实肩宽与解剖头高约束，不随宽袖或宽底座放大',()=>{
 const head={width:1.4,height:1.1,anatomicalWidth:1.05,anatomicalHeight:.8}
 const body={width:1,height:1.35,shoulderWidth:.7,headHeight:.27}
 const fit=fittedHeadScale(head,body)
 assert.ok(fit*head.anatomicalWidth<=body.shoulderWidth*.5+1e-8)
 assert.ok(fit*head.anatomicalHeight<=body.headHeight+1e-8)
 assert.equal(fittedHeadScale(head,{...body,width:100}),fit)
 assert.ok(fittedHeadScale(head,{...body,shoulderWidth:.4})<fit)
})

test('颈部随头部显示，移除头部后隐藏且重新添加时恢复',()=>{
 const body=part('afu_body','top',[0,1.4,0]),head=part('afu_head','bottom',[0,0,0])
 body.userData.category='body';body.userData.dimensions={width:1,height:1.35,shoulderWidth:.7,headHeight:.27}
 head.userData.category='head';head.userData.dimensions={width:1,height:1}
 const neck=new THREE.Mesh(new THREE.CylinderGeometry(.1,.1,.06),new THREE.MeshStandardMaterial())
 neck.name='neck-joint';neck.visible=false;body.add(neck)
 attachPart(head,findConnection(head,[body]));assert.equal(neck.visible,true)
 head.removeFromParent();rebuildConnections([body]);assert.equal(neck.visible,false)
 const replacement=part('afu_head','bottom',[0,0,0]);replacement.userData.category='head';replacement.userData.dimensions={width:1,height:1}
 attachPart(replacement,findConnection(replacement,[body]));assert.equal(neck.visible,true)
})

test('颈部插槽使用中央衣领截面，不被高肩饰和发饰的包围盒偏移', () => {
  const body = new THREE.Group()
  const torso = new THREE.Mesh(new THREE.BoxGeometry(1, 2, .6))
  torso.position.set(.1, 1, -.2)
  const shoulder = new THREE.Mesh(new THREE.BoxGeometry(.2, .8, .2))
  shoulder.position.set(.9, 2.1, .3)
  body.add(torso, shoulder)
  const top = neckSocket(body, 'top')
  assert.ok(Math.abs(top[0] - .1) < 1e-6)
  assert.ok(Math.abs(top[2] + .2) < 1e-6)
  assert.ok(top[1] < 2 && top[1] > 1.8)

  const head = new THREE.Group()
  const neck = new THREE.Mesh(new THREE.BoxGeometry(.3, .2, .3))
  neck.position.set(.15, .1, -.12)
  const hat = new THREE.Mesh(new THREE.BoxGeometry(1.2, .4, .5))
  hat.position.set(-.2, .8, .1)
  head.add(neck, hat)
  head.position.set(5, 3, -2)
  const bottom = neckSocket(head, 'bottom')
  assert.ok(new THREE.Vector3(...bottom).distanceTo(new THREE.Vector3(.15, 0, -.12)) < 1e-6)
})
test('连接点在父件旋转缩放、子件旋转缩放后仍重合', () => {
  const base = part('clay_base', 'top', [0, 0.02, 0]), body = part('afu_body', 'bottom', [0, -0.82, 0])
  base.rotation.set(0.2, 0.7, 0.4); base.scale.setScalar(1.8)
  attachPart(body, findConnection(body, [base]))
  body.rotation.z = 0.3; body.scale.setScalar(1.4); alignConnection(body); base.updateMatrixWorld(true)
  const a = base.localToWorld(new THREE.Vector3(0, 0.02, 0)), b = body.localToWorld(new THREE.Vector3(0, -0.82, 0))
  assert.ok(a.distanceTo(b) < 1e-8)
  assert.equal(findConnection(part('afu_head', 'bottom', [0, -0.88, 0]), [base]), null)
  body.removeFromParent(); rebuildConnections([base]); assert.equal(base.userData.attachPoints[0].used, false)
})

test('替换身体保留头部并重新适配尺寸和连接点',()=>{
 const root=new THREE.Group(),body=part('afu_body','top',[0,1.3,0]),head=part('afu_head','bottom',[0,0,0])
 body.userData.category='body';body.userData.dimensions={width:1.2,height:1.35};head.userData.category='head';head.userData.dimensions={width:1.4,height:1.1}
 root.add(body,head);attachPart(head,findConnection(head,[body]))
 const before=head.scale.x,remaining=releasePart(body,[body,head],root)
 assert.equal(remaining.length,1);assert.equal(head.parent,root);assert.equal(head.userData.connection,undefined)
 const next=part('afu_body','top',[0,1,0]);next.userData.category='body';next.userData.dimensions={width:.7,height:1}
 root.add(next);connectAvailableParts([...remaining,next]);root.updateMatrixWorld(true)
 assert.equal(head.parent,next);assert.ok(head.scale.x<before)
 assert.ok(head.getWorldPosition(new THREE.Vector3()).distanceTo(next.localToWorld(new THREE.Vector3(0,1,0)))<1e-8)
})

test('宠物优先连接底座旁边，不连接手臂；后加底座也能迁移',()=>{
 const root=new THREE.Group(),body=part('afu_body','companion',[1,0,0]),arms=part('afu_arms','front',[0,0,1]),pet=part('lion_beast','bottom',[0,0,0])
 body.userData.category='body';arms.userData.category='arms';pet.userData.category='pet';root.add(body,arms,pet)
 assert.equal(findConnection(pet,[arms]),null);attachPart(pet,findConnection(pet,[body,arms]))
 const base=part('clay_base','companion',[1.3,0,.2]);base.userData.category='base';root.add(base)
 connectAvailableParts([pet,body,arms,base]);root.updateMatrixWorld(true)
 assert.equal(pet.parent,base);assert.equal(body.userData.attachPoints[0].used,false)
 assert.ok(pet.getWorldPosition(new THREE.Vector3()).distanceTo(new THREE.Vector3(1.3,0,.2))<1e-8)
})

test('先添加头部、后添加身体与底座也能补齐连接', () => {
  const root = new THREE.Group()
  const head = part('afu_head', 'bottom', [0, -0.88, 0])
  const body = part('afu_body', 'bottom', [0, -0.82, 0])
  body.userData.attachPoints.push({ name: 'top', position: [0, 1, 0], used: false })
  const base = part('clay_base', 'top', [0, 0, 0])
  root.add(head, body, base)
  connectAvailableParts([head, body, base])
  root.updateMatrixWorld(true)
  assert.equal(head.parent, body)
  assert.equal(body.parent, base)
  assert.equal(root.children.length, 1)
  assert.ok(Math.abs(head.getWorldPosition(new THREE.Vector3()).y - 2.7) < 1e-8)
})
