import * as THREE from 'three'
const cloneMaterial=m=>{const c=m.clone();for(const [key,v]of Object.entries(c))if(v?.isTexture)c[key]=v.clone();return c}
// Clip triangle polygons at a plane, retain interpolated UVs/normals, close cut loops.
export function clipPart(object,axis,cutoff,below,capColor,largestIsland=false){
 object.updateMatrixWorld(true)
 const result=new THREE.Group(),axisIndex={x:0,y:1,z:2}[axis],projection=axis==='x'?['z','y']:['x','z']
 object.traverse(mesh=>{
  if(!mesh.isMesh)return
  const geometry=mesh.geometry.clone().applyMatrix4(mesh.matrixWorld),attributes=geometry.attributes,indices=geometry.index,output=Object.fromEntries(Object.keys(attributes).map(k=>[k,[]]))
  let segments=[]
  const vertex=i=>Object.fromEntries(Object.entries(attributes).map(([k,a])=>[k,Array.from({length:a.itemSize},(_,n)=>a.array[i*a.itemSize+n])]))
  const distance=v=>(v.position[axisIndex]-cutoff)*(below?1:-1)
  const interpolate=(a,b,t)=>Object.fromEntries(Object.keys(attributes).map(k=>[k,a[k].map((v,n)=>v+(b[k][n]-v)*t)]))
  const add=v=>{for(const k of Object.keys(attributes))output[k].push(...v[k])}
  const count=indices?indices.count:attributes.position.count
  for(let i=0;i<count;i+=3){
   const polygon=[0,1,2].map(n=>vertex(indices?indices.getX(i+n):i+n)),clipped=[],crossings=[]
   for(let n=0;n<3;n++){const a=polygon[n],b=polygon[(n+1)%3],da=distance(a),db=distance(b),insideA=da<=0,insideB=db<=0
    if(insideA)clipped.push(a)
    if(insideA!==insideB){const v=interpolate(a,b,da/(da-db));v.position[axisIndex]=cutoff;clipped.push(v);crossings.push(new THREE.Vector3(...v.position))}
   }
   if(crossings.length===2)segments.push(crossings)
   for(let n=1;n<clipped.length-1;n++){add(clipped[0]);add(clipped[n]);add(clipped[n+1])}
  }
  geometry.dispose()
  if(!output.position.length)return
  if(largestIsland){
   const parent=new Map(),pointKeys=[]
   const find=k=>{let root=k;while(parent.get(root)!==root)root=parent.get(root);while(k!==root){const next=parent.get(k);parent.set(k,root);k=next}return root}
   for(let i=0;i<output.position.length;i+=3){const k=output.position.slice(i,i+3).map(v=>Math.round(v*1e5)).join(',');pointKeys.push(k);if(!parent.has(k))parent.set(k,k)}
   for(let i=0;i<pointKeys.length;i+=3){parent.set(find(pointKeys[i+1]),find(pointKeys[i]));parent.set(find(pointKeys[i+2]),find(pointKeys[i]))}
   const counts=new Map();for(let i=0;i<pointKeys.length;i+=3){const root=find(pointKeys[i]);counts.set(root,(counts.get(root)||0)+1)}
   const largest=[...counts].sort((a,b)=>b[1]-a[1])[0][0],retained=new Set()
   for(let i=0;i<pointKeys.length;i+=3)if(find(pointKeys[i])===largest)for(let n=0;n<3;n++)retained.add(i+n)
   for(const [name,attribute]of Object.entries(attributes)){const data=[];for(const index of retained)data.push(...output[name].slice(index*attribute.itemSize,(index+1)*attribute.itemSize));output[name]=data}
   segments=segments.filter(([p])=>{const k=[p.x,p.y,p.z].map(v=>Math.round(v*1e5)).join(',');return parent.has(k)&&find(k)===largest})
  }
  const g=new THREE.BufferGeometry()
  for(const [k,data]of Object.entries(output))g.setAttribute(k,new THREE.Float32BufferAttribute(data,attributes[k].itemSize))
  g.computeBoundingBox();g.computeBoundingSphere()
  const surface=new THREE.Mesh(g,Array.isArray(mesh.material)?mesh.material.map(cloneMaterial):cloneMaterial(mesh.material));surface.castShadow=surface.receiveShadow=true;result.add(surface)
  const key=p=>[p.x,p.y,p.z].map(v=>Math.round(v*1e5)).join(','),points=new Map(),links=new Map()
  for(const [a,b]of segments){const ka=key(a),kb=key(b);if(ka===kb)continue;points.set(ka,a);points.set(kb,b);for(const [u,v]of [[ka,kb],[kb,ka]]){if(!links.has(u))links.set(u,new Set());links.get(u).add(v)}}
  const visited=new Set()
  for(const start of links.keys()){
   if(visited.has(start))continue
   const loop=[];let current=start,previous=null,closed=false
   for(let n=0;n<=links.size;n++){visited.add(current);loop.push(points.get(current));const next=[...links.get(current)].find(k=>k!==previous);if(!next)break;if(next===start){closed=true;break}if(visited.has(next))break;previous=current;current=next}
   if(!closed||loop.length<3)continue
   const contour=loop.map(p=>new THREE.Vector2(p[projection[0]],p[projection[1]])),faces=THREE.ShapeUtils.triangulateShape(contour,[]),positions=[]
   for(const face of faces)for(const index of face)positions.push(...loop[index].toArray())
   const cap=new THREE.BufferGeometry();cap.setAttribute('position',new THREE.Float32BufferAttribute(positions,3));cap.computeVertexNormals()
   const end=new THREE.Mesh(cap,new THREE.MeshPhysicalMaterial({color:capColor,roughness:.6,clearcoat:.2,side:THREE.DoubleSide}));end.castShadow=end.receiveShadow=true;result.add(end)
  }
 })
 return result
}
