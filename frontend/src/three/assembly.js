import * as THREE from 'three'

// 显式的部件/插槽配对，防止头部接到底座、身体接到瑞狮。
const PAIRS = [
  ['clay_base', 'companion', 'lion_beast', 'bottom'],
  ['clay_base', 'accessory', 'accessory', 'bottom'],
  ['afu_body', 'companion', 'lion_beast', 'bottom'],
  ['clay_base', 'top', 'afu_body', 'bottom'],
  ['afu_body', 'top', 'afu_head', 'bottom'],
  ['afu_body', 'front', 'afu_arms', 'center'],
  ['afu_arms', 'front', 'lion_beast', 'bottom'],
  ['afu_body', 'accessory', 'accessory', 'bottom'],
]

export function findConnection(part, placed) {
  // Prefer the pedestal for companion animals; they do not occupy the hands.
  const targets = [...placed].sort((a,b)=>(b.userData.category==='base')-(a.userData.category==='base'))
  for (const target of targets) {
    for (const ta of target.userData.attachPoints || []) {
      for (const na of part.userData.attachPoints || []) {
        if (ta.used || na.used) continue
        if (part.userData.category === 'pet' && ta.name === 'front') continue
        if (PAIRS.some(([a, x, b, y]) =>
          (target.userData.partId === a && ta.name === x && part.userData.partId === b && na.name === y))) {
          return { target, ta, na }
        }
      }
    }
  }
  return null
}

export function alignConnection(part) {
  const connection = part.userData.connection
  if (!connection || part.parent?.uuid !== connection.targetUUID) return
  const offset = new THREE.Vector3(...connection.selfPosition)
    .multiply(part.scale).applyQuaternion(part.quaternion)
  part.position.fromArray(connection.targetPosition).sub(offset)
  if(part.userData.category==='head')part.position.y+=(part.userData.neckLift||0)*(part.parent.userData.dimensions?.height||1)
  if(['pet','accessory'].includes(part.userData.category)&&part.parent.userData.dimensions){
    const target=part.parent,dimensions=target.userData.dimensions
    const body=target.userData.category==='body'?target:target.children.find(child=>child.userData.category==='body')
    const radius=Math.max(dimensions.width/2,(body?.userData.dimensions?.width||0)*(body?.scale.x||1)/2)
    const side=part.userData.category==='pet'?1:-1
    // Place both companions on the same ground, outside the full figure's silhouette.
    const extent=new THREE.Box3().setFromObject(part).getSize(new THREE.Vector3())
    const parentScale=target.getWorldScale(new THREE.Vector3()).x
    part.position.x=side*(radius+extent.x/parentScale/2+.045)
    part.position.z=0
    target.updateWorldMatrix(true,true)
    const ground=target.localToWorld(new THREE.Vector3(0,0,0)).y
    const bottom=new THREE.Box3().setFromObject(part).min.y
    const worldScale=target.getWorldScale(new THREE.Vector3()).y
    if(Number.isFinite(bottom)&&worldScale>0)part.position.y+=(ground-bottom)/worldScale
  }
  if(part.userData.category==='head'){
    const neck=part.parent.getObjectByName('neck-joint')
    if(neck){
      const radius=(part.userData.dimensions.anatomicalWidth||part.userData.dimensions.width)*part.scale.x*.18
      if(neck.userData.adaptiveNeck){
        const body=part.parent,collar=body.userData.collarPosition
        const lift=(part.userData.neckLift||0)*body.userData.dimensions.height
        const height=body.userData.neckHeight+lift+body.userData.dimensions.height*.014
        neck.scale.set(radius,height,radius)
        neck.position.set(collar[0],collar[1]+(body.userData.neckHeight+lift)*.5,collar[2])
      }else neck.scale.set(radius,1,radius)
    }
  }
}

export function fittedHeadScale(head, body) {
  return Math.min(
    (body.shoulderWidth ? body.shoulderWidth * (head.shoulderRatio ?? .5) : body.width * .82) / (head.anatomicalWidth ?? head.width),
    (head.figureType === 'child' ? body.height * .34 : (body.headHeight ?? body.height * .7)) / (head.anatomicalHeight ?? head.height),
  )
}

export function attachPart(part, connection) {
  const { target, ta, na } = connection
  const dimensions=part.userData.dimensions,body=target.userData.dimensions
  if(dimensions&&body&&target.userData.category==='body'){
    let factor=1
    if(part.userData.category==='head')factor=fittedHeadScale(dimensions,body)
    if(part.userData.category==='arms')factor=Math.min(body.width*1.06/dimensions.width,body.height*.6/dimensions.height)
    if(part.userData.category==='accessory')factor=part.userData.asset==='accessory-umbrella'?body.height*.85/dimensions.height:Math.min(body.width*.4/dimensions.width,body.height*.3/dimensions.height)
    if(part.userData.category==='pet')factor=Math.min(body.height*.3/dimensions.height,.55/dimensions.width)
    if(['head','arms','accessory','pet'].includes(part.userData.category))part.scale.setScalar(factor)
    if(part.userData.category==='head')part.userData.fittedScale=factor
  }
  if(dimensions&&target.userData.category==='base'&&['pet','accessory'].includes(part.userData.category)){
    const height=part.userData.category==='pet'?.4:part.userData.asset==='accessory-umbrella'?1.15:.45
    part.scale.setScalar(Math.min(height/dimensions.height,.75/dimensions.width))
  }
  target.add(part)
  part.userData.connection = { targetUUID: target.uuid, targetAnchor: ta.name,
    selfAnchor: na.name, targetPosition: [...ta.position], selfPosition: [...na.position] }
  ta.used = na.used = true
  alignConnection(part)
  if(part.userData.category==='head'){
    const neck=target.getObjectByName('neck-joint')
    if(neck){neck.visible=true;neck.material.color.set(part.userData.skinTone||'#e4c7a6');alignConnection(part)}
  }
}

// Keep child parts when replacing a body, arm pair or pedestal.
export function releasePart(part, parts, sceneRoot) {
  for(const child of parts.filter(p=>p.parent===part)){
    sceneRoot.attach(child);delete child.userData.connection
  }
  part.removeFromParent()
  const remaining=parts.filter(p=>p!==part)
  rebuildConnections(remaining)
  return remaining
}

export function rebuildConnections(parts) {
  for(const part of parts){const neck=part.getObjectByName('neck-joint');if(neck)neck.visible=parts.some(child=>child.userData.category==='head'&&child.userData.connection?.targetUUID===part.uuid)}
  for (const part of parts) for (const a of part.userData.attachPoints || []) a.used = false
  for (const part of parts) {
    const c = part.userData.connection
    if (!c) continue
    const target = parts.find(p => p.uuid === c.targetUUID)
    const ta = target?.userData.attachPoints?.find(a => a.name === c.targetAnchor)
    const na = part.userData.attachPoints?.find(a => a.name === c.selfAnchor)
    if (ta && na) ta.used = na.used = true
  }
}

// 补上先放子件、后放父件的连接，避免部件永远滞留在自由摆放位置。
export function connectAvailableParts(parts) {
  for(const part of parts){
    if(!['pet','accessory'].includes(part.userData.category)||part.parent?.userData.category!=='body')continue
    const anchorName=part.userData.category==='pet'?'companion':'accessory'
    const base=parts.find(p=>p.userData.category==='base'&&p.userData.attachPoints?.some(a=>a.name===anchorName&&!a.used))
    if(!base)continue
    const old=part.userData.connection
    const anchor=part.parent.userData.attachPoints.find(a=>a.name===old?.targetAnchor)
    if(anchor)anchor.used=false
    for(const a of part.userData.attachPoints)a.used=false
    delete part.userData.connection
    const connection=findConnection(part,[base]);if(connection)attachPart(part,connection)
  }
  for (const part of parts) {
    if (part.userData.connection) continue
    const connection = findConnection(part, parts.filter(target => target !== part))
    if (connection) attachPart(part, connection)
  }
  for(const part of parts)if(['pet','accessory'].includes(part.userData.category))alignConnection(part)
}
