import * as THREE from 'three'
import { alignConnection, connectAvailableParts, fittedHeadScale } from './assembly.js'

// Review only transforms: never rewrite or dispose the user's selected geometry.
export function captureAssembly(parts) {
  return parts.map(part => ({ part, position: part.position.clone(), quaternion: part.quaternion.clone(), scale: part.scale.clone(), neckLift: part.userData.neckLift||0 }))
}
export function restoreAssembly(snapshot, parts) {
  if (!snapshot || snapshot.some(item => !parts.includes(item.part))) return false
  for (const item of snapshot) {
    item.part.position.copy(item.position)
    item.part.quaternion.copy(item.quaternion)
    item.part.scale.copy(item.scale)
    item.part.userData.neckLift=item.neckLift||0
  }
  for (const part of parts) alignConnection(part)
  return true
}
function ownBounds(part) {
  part.updateWorldMatrix(true, true)
  const box = new THREE.Box3()
  part.traverse(object => {
    if (!object.isMesh || !object.geometry || !object.visible) return
    let owner = object.parent
    while (owner && owner !== part && !owner.userData.category) owner = owner.parent
    if (owner !== part) return
    object.geometry.computeBoundingBox()
    box.union(object.geometry.boundingBox.clone().applyMatrix4(object.matrixWorld))
  })
  return box
}
export function inspectAssembly(parts) {
  const issues = []
  const body = parts.find(part => part.userData.category === 'body')
  for (const part of parts) {
    const category = part.userData.category
    if (!category) continue
    if (!Number.isFinite(part.scale.x) || part.scale.x <= 0) issues.push({ code: 'scale', part, text: `${part.name}尺寸无效` })
    if (Math.abs(part.rotation.x) > .12 || Math.abs(part.rotation.z) > .12) issues.push({ code: 'tilt', part, text: `${part.name}倾斜过大` })
    if (category === 'head' && body) {
      const desired = fittedHeadScale(part.userData.dimensions, body.userData.dimensions)
      if (Math.abs(part.scale.x / desired - 1) > .08) issues.push({ code: 'proportion', part, text: '头部与肩宽、身体高度的比例需要调整' })
    }
    const connection = part.userData.connection
    if (connection && !['pet', 'accessory'].includes(category)) {
      const a = part.parent.localToWorld(new THREE.Vector3(...connection.targetPosition))
      if(category==='head')a.copy(part.parent.localToWorld(new THREE.Vector3(...connection.targetPosition).add(new THREE.Vector3(0,(part.userData.neckLift||0)*(part.parent.userData.dimensions?.height||1),0))))
      const b = part.localToWorld(new THREE.Vector3(...connection.selfPosition))
      if (a.distanceTo(b) > .008) issues.push({ code: 'seam', part, text: `${part.name}连接处存在间隙` })
    }
    if(category==='head'&&connection){
      const neck=part.parent.getObjectByName('neck-joint')
      if(neck?.userData.adaptiveNeck&&(!neck.visible||neck.scale.y<=0))issues.push({code:'neck',part,text:'颈部过渡结构需要恢复'})
    }
    if (['pet', 'accessory'].includes(category) && connection) {
      const box = ownBounds(part), ground = part.parent.localToWorld(new THREE.Vector3(0, 0, 0)).y
      if (!box.isEmpty() && Math.abs(box.min.y - ground) > .015) issues.push({ code: 'ground', part, text: `${part.name}没有落在展示平面上` })
      if (body && !box.isEmpty() && box.intersectsBox(ownBounds(body))) issues.push({ code: 'overlap', part, text: `${part.name}与人物重叠` })
    }
  }
  if (parts.some(part => part.userData.category === 'head') && !body) issues.push({ code: 'missing-body', text: '添加身体后才能完成头身装配' })
  return issues
}

// A bounded local agent: observe -> select allowed corrections -> execute -> verify.
// No API credentials, geometry generation or claims of visual LLM judgement.
export function reviewAndRepair(parts) {
  const snapshot = captureAssembly(parts), before = inspectAssembly(parts), changes = []
  connectAvailableParts(parts)
  for (const part of parts) {
    if (!part.userData.category) continue
    if (Math.abs(part.rotation.x) > .12 || Math.abs(part.rotation.z) > .12) {
      part.rotation.x = 0; part.rotation.z = 0
      changes.push(`${part.name}恢复直立`)
    }
    if (part.userData.category === 'head' && part.parent?.userData.category === 'body') {
      const fit = fittedHeadScale(part.userData.dimensions, part.parent.userData.dimensions)
      if (Math.abs(part.scale.x - fit) > .0001) changes.push('根据肩宽与身体高度调整头部比例')
      part.scale.setScalar(fit); part.userData.fittedScale = fit
      part.rotation.y = 0
      if(part.userData.neckLift){part.userData.neckLift=0;changes.push('恢复自然颈部衔接高度')}
      const neck=part.parent.getObjectByName('neck-joint')
      if(neck){neck.visible=true;neck.material.color.set(part.userData.skinTone||'#e4c7a6')}
    }
    alignConnection(part)
  }
  for (let pass = 0; pass < 3; pass++) {
    const issues = inspectAssembly(parts)
    for (const issue of issues) {
      const part = issue.part
      if (!part || !['ground', 'overlap'].includes(issue.code)) continue
      const scale = part.parent.getWorldScale(new THREE.Vector3())
      if (issue.code === 'ground') {
        const ground = part.parent.localToWorld(new THREE.Vector3(0, 0, 0)).y
        part.position.y += (ground - ownBounds(part).min.y) / scale.y
      } else part.position.x += (part.userData.category === 'pet' ? 1 : -1) * .08 / scale.x
      changes.push(`${part.name}${issue.code === 'ground' ? '调整落地高度' : '避开人物轮廓'}`)
    }
    if (!issues.some(issue => ['ground', 'overlap'].includes(issue.code))) break
  }
  return { snapshot, before, issues: inspectAssembly(parts), changes: [...new Set(changes)] }
}
