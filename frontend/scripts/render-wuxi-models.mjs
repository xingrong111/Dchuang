import fs from 'node:fs/promises'
const debug='http://127.0.0.1:19223', origin='http://127.0.0.1:15176'
const target=await(await fetch(debug+'/json/new?about:blank',{method:'PUT'})).json()
const socket=new WebSocket(target.webSocketDebuggerUrl)
await new Promise((resolve,reject)=>{socket.onopen=resolve;socket.onerror=reject})
let next=0;const pending=new Map()
socket.onmessage=event=>{const message=JSON.parse(event.data);if(message.id){const callback=pending.get(message.id);pending.delete(message.id);message.error?callback.reject(message.error):callback.resolve(message.result)}}
const command=(method,params={})=>new Promise((resolve,reject)=>{const id=++next;pending.set(id,{resolve,reject});socket.send(JSON.stringify({id,method,params}))})
const evaluate=async expression=>{const result=await command('Runtime.evaluate',{expression,awaitPromise:true,returnByValue:true});if(result.exceptionDetails)throw Error(result.exceptionDetails.exception?.description||result.exceptionDetails.text);return result.result.value}

const jobs=JSON.parse(await fs.readFile('../operations/deliverables/wuxi-hunyuan-20261007/jobs.json','utf8'));
try{
 await command('Page.enable');await command('Page.navigate',{url:origin});await new Promise(r=>setTimeout(r,2500));
 await command('Emulation.setDeviceMetricsOverride',{width:900,height:700,deviceScaleFactor:1,mobile:false});
 await evaluate(`(async()=>{window.T=await import('/node_modules/.vite/deps/three.js');window.Loader=(await import('/node_modules/three/examples/jsm/loaders/GLTFLoader.js')).GLTFLoader;document.body.innerHTML='';document.body.style.cssText='margin:0;background:#eee8dd';window.renderer=new T.WebGLRenderer({antialias:true,preserveDrawingBuffer:true});renderer.setSize(900,700);document.body.append(renderer.domElement);return true})()`);
 for(const job of [...jobs,{id:'afu-desk',downloaded:true,folder:'products'}].filter(j=>!process.env.RENDER_ONLY||j.id===process.env.RENDER_ONLY)){
  if(!job.downloaded)continue;
  const data=await evaluate(`(async()=>{const root=(await new Loader().loadAsync('/models/${job.folder||'workshop'}/${job.id}.glb')).scene;root.updateMatrixWorld(true);const bounds=new T.Box3().setFromObject(root),size=bounds.getSize(new T.Vector3()),center=bounds.getCenter(new T.Vector3());const scene=new T.Scene();scene.background=new T.Color('#eee8dd');scene.add(root,new T.HemisphereLight(0xffffff,0x887966,2));const light=new T.DirectionalLight(0xffffff,3);light.position.set(3,5,5);scene.add(light);const camera=new T.PerspectiveCamera(32,900/700,.01,100),distance=Math.max(size.y,size.x/(900/700))*2.1;camera.position.set(center.x+size.x*.12,center.y+size.y*.05,center.z+distance);camera.lookAt(center);renderer.render(scene,camera);const front=renderer.domElement.toDataURL('image/png').split(',')[1];camera.position.set(center.x+distance,center.y+size.y*.05,center.z);camera.lookAt(center);renderer.render(scene,camera);const side=renderer.domElement.toDataURL('image/png').split(',')[1];root.traverse(o=>{o.geometry?.dispose();if(o.material){for(const m of [].concat(o.material)){for(const v of Object.values(m))if(v?.isTexture)v.dispose();m.dispose()}}});return {front,side}})()`);
  await fs.writeFile('public/content/'+job.id+'.png',Buffer.from(data.front,'base64'));await fs.writeFile('reports/browser/'+job.id+'-side.png',Buffer.from(data.side,'base64'));console.log('rendered',job.id);
 }
}finally{socket.close();await fetch(debug+'/json/close/'+target.id)}
