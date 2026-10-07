import * as THREE from 'three'

// Measure the actual cut surface, rather than the whole model's bounding box.
export function neckSocket(object, end, insertion = .045) {
  object.updateMatrixWorld(true)
  const inverse = object.matrixWorld.clone().invert()
  const points = [], point = new THREE.Vector3(), matrix = new THREE.Matrix4()
  object.traverse(mesh => {
    if (!mesh.isMesh || !mesh.geometry?.attributes.position) return
    matrix.multiplyMatrices(inverse, mesh.matrixWorld)
    const positions = mesh.geometry.attributes.position
    for (let i = 0; i < positions.count; i++) {
      point.fromBufferAttribute(positions, i).applyMatrix4(matrix)
      points.push(point.clone())
    }
  })
  if (!points.length) return [0, 0, 0]
  const bounds = new THREE.Box3().setFromPoints(points)
  const size = bounds.getSize(new THREE.Vector3())
  const center = bounds.getCenter(new THREE.Vector3())
  const candidates = end === 'top'
    ? points.filter(p => Math.abs(p.x - center.x) <= size.x * .16)
    : points
  let surfaceY = bounds.min.y
  if (end === 'top') {
    if (candidates.length) surfaceY = candidates.reduce((highest, p) => Math.max(highest, p.y), -Infinity)
    else {
      // Sparse meshes may have no vertices inside the central strip.
      const origin = new THREE.Vector3(center.x, bounds.max.y + size.y, center.z).applyMatrix4(object.matrixWorld)
      const direction = new THREE.Vector3(0, -1, 0).transformDirection(object.matrixWorld)
      const hit = new THREE.Raycaster(origin, direction).intersectObject(object, true)[0]
      surfaceY = hit ? hit.point.clone().applyMatrix4(inverse).y : bounds.max.y
    }
  }
  const surface = points.filter(p => Math.abs(p.y - surfaceY) < Math.max(size.y * .006, .0001))
  const contact = surface.length ? new THREE.Box3().setFromPoints(surface).getCenter(new THREE.Vector3()) : center
  // A small insertion into the collar avoids a visible daylight seam.
  return [contact.x, surfaceY - (end === 'top' ? size.y * insertion : 0), contact.z]
}

export function shoulderWidth(object, height, width) {
  object.updateMatrixWorld(true)
  const inverse=object.matrixWorld.clone().invert(),point=new THREE.Vector3(),matrix=new THREE.Matrix4()
  let left=Infinity,right=-Infinity
  object.traverse(mesh=>{
    const positions=mesh.geometry?.attributes.position
    if(!mesh.isMesh||!positions)return
    matrix.multiplyMatrices(inverse,mesh.matrixWorld)
    for(let i=0;i<positions.count;i++){
      point.fromBufferAttribute(positions,i).applyMatrix4(matrix)
      if(point.y>=height*.77&&point.y<=height*.9){left=Math.min(left,point.x);right=Math.max(right,point.x)}
    }
  })
  return Number.isFinite(left)?Math.min(right-left,width*.85):width*.7
}
