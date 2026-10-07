import fs from 'node:fs/promises'
const debug='http://127.0.0.1:19223', origin='http://127.0.0.1:15176'
const target=await(await fetch(debug+'/json/new?about:blank',{method:'PUT'})).json()
const socket=new WebSocket(target.webSocketDebuggerUrl)
await new Promise((resolve,reject)=>{socket.onopen=resolve;socket.onerror=reject})
let next=0;const pending=new Map()
socket.onmessage=event=>{const message=JSON.parse(event.data);if(message.id){const callback=pending.get(message.id);pending.delete(message.id);message.error?callback.reject(message.error):callback.resolve(message.result)}}
const command=(method,params={})=>new Promise((resolve,reject)=>{const id=++next;pending.set(id,{resolve,reject});socket.send(JSON.stringify({id,method,params}))})
const evaluate=async expression=>{const result=await command('Runtime.evaluate',{expression,awaitPromise:true,returnByValue:true});if(result.exceptionDetails)throw Error(result.exceptionDetails.exception?.description||result.exceptionDetails.text);return result.result.value}
const configurations=[
 ['spring-child','head-red','body-ivory','base-clay','pet-jade','accessory-card'],
 ['sunny-scholar','head-peach','body-red','base-wood','pet-left','accessory-book'],
 ['opera-stage','head-gold','body-jade','base-jade','pet-jade','accessory-brush'],
 ['longevity','head-jade','body-red','base-jade','pet-lion','accessory-flower'],
 ['young-guard','head-peach','body-gold','base-gold','pet-right','accessory-book'],
 ['child-reading','head-red','body-ivory','base-wood','pet-left','accessory-card']
]
try{
 await command('Page.enable');await command('Page.navigate',{url:origin});await new Promise(resolve=>setTimeout(resolve,3000))
 await command('Emulation.setDeviceMetricsOverride',{width:900,height:700,deviceScaleFactor:1,mobile:false})
 await evaluate(`(async()=>{window.T=await import('/node_modules/.vite/deps/three.js');window.parts=await import('/src/three/workshopParts.js');window.assembly=await import('/src/three/assembly.js');window.Exporter=(await import('/node_modules/three/examples/jsm/exporters/GLTFExporter.js')).GLTFExporter;document.body.innerHTML='';document.body.style.cssText='margin:0;background:#eee8dd';window.renderer=new T.WebGLRenderer({antialias:true,preserveDrawingBuffer:true});renderer.setSize(900,700);document.body.append(renderer.domElement);return true})()`)
 await fs.mkdir('public/models/community',{recursive:true})
 for(const [name,...ids] of configurations){
  const result=await evaluate(`(async()=>{const ids=${JSON.stringify(ids)},objects=await Promise.all(ids.map(parts.createWorkshopPart)),root=new T.Group();root.add(...objects);assembly.connectAvailableParts(objects);root.updateMatrixWorld(true);const bounds=new T.Box3().setFromObject(root),size=bounds.getSize(new T.Vector3()),center=bounds.getCenter(new T.Vector3());const scene=new T.Scene();scene.background=new T.Color('#eee8dd');scene.add(root,new T.HemisphereLight(0xffffff,0x887966,2));const light=new T.DirectionalLight(0xffffff,3);light.position.set(3,5,5);scene.add(light);const floor=new T.Mesh(new T.PlaneGeometry(30,30),new T.MeshStandardMaterial({color:'#eee8dd',roughness:1}));floor.rotation.x=-Math.PI/2;floor.position.y=-.015;scene.add(floor);const camera=new T.PerspectiveCamera(32,900/700,.01,100),distance=Math.max(size.y,size.x/(900/700))*2.2;camera.position.set(center.x+.18,center.y+.22,distance);camera.lookAt(center);renderer.render(scene,camera);window.exportRoot=root;const grounded=objects.filter(p=>['pet','accessory'].includes(p.userData.category)).map(p=>({category:p.userData.category,minY:new T.Box3().setFromObject(p).min.y,x:p.getWorldPosition(new T.Vector3()).x}));return {grounded,bounds:size.toArray()}})()`)
  const shot=await evaluate(`renderer.domElement.toDataURL('image/png').split(',')[1]`)
  await fs.writeFile('public/content/community-'+name+'.png',Buffer.from(shot,'base64'))
  if(process.argv.includes('--covers-only')){console.log(name,JSON.stringify(result));continue}
  const encoded=await evaluate(`(async()=>{const {mergeVertices}=await import('/node_modules/three/examples/jsm/utils/BufferGeometryUtils.js');exportRoot.traverse(mesh=>{if(mesh.isMesh){const old=mesh.geometry;mesh.geometry=mergeVertices(old,1e-6);old.dispose()}});const data=await new Exporter().parseAsync(exportRoot,{binary:true,maxTextureSize:512});return await new Promise(resolve=>{const reader=new FileReader();reader.onload=()=>resolve(reader.result.split(',')[1]);reader.readAsDataURL(new Blob([data]))})})()`)
  await fs.writeFile('public/models/community/'+name+'.glb',Buffer.from(encoded,'base64'))
  console.log(name,JSON.stringify(result))
 }
}finally{socket.close();await fetch(debug+'/json/close/'+target.id)}
