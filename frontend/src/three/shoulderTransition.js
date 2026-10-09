import * as THREE from 'three'

// Preserve the source UVs and sleeves, while shaping the flat cut into a
// shoulder slope with a raised central collar. Operates before normalization.
export function shapeShoulderTransition(object) {
  object.updateMatrixWorld(true)
  const box=new THREE.Box3().setFromObject(object),size=box.getSize(new THREE.Vector3()),center=box.getCenter(new THREE.Vector3())
  const band=size.y*.1, collarRadius=size.x*.12
  if(!band||!size.x)return
  object.traverse(mesh=>{
    if(!mesh.isMesh||!mesh.geometry?.attributes.position)return
    const attribute=mesh.geometry.attributes.position,inverse=mesh.matrixWorld.clone().invert(),point=new THREE.Vector3()
    for(let i=0;i<attribute.count;i++){
      point.fromBufferAttribute(attribute,i).applyMatrix4(mesh.matrixWorld)
      const influence=THREE.MathUtils.smoothstep(point.y,box.max.y-band,box.max.y)
      if(!influence)continue
      const distance=Math.abs(point.x-center.x)
      const slope=THREE.MathUtils.smoothstep(distance,collarRadius,size.x*.46)
      point.y-=size.y*.055*slope*influence
      point.applyMatrix4(inverse);attribute.setXYZ(i,point.x,point.y,point.z)
    }
    attribute.needsUpdate=true;mesh.geometry.computeVertexNormals();mesh.geometry.computeBoundingBox();mesh.geometry.computeBoundingSphere()
  })
}
