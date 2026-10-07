// Uses a separately launched local headless Edge instance; no external browser packages.
import fs from 'node:fs/promises'
import path from 'node:path'
const debugging = process.env.EDGE_DEBUG_URL || 'http://127.0.0.1:19223'
const directory = path.resolve('reports/browser')
await fs.mkdir(directory, { recursive: true })
const targets = await (await fetch(`${debugging}/json/list`)).json()
const target = targets.find(t => t.type === 'page' && t.url.includes('3d.hunyuan.tencent.com'))
if (!target) throw new Error('Hunyuan tab missing')
const socket = new WebSocket(target.webSocketDebuggerUrl)
await new Promise((resolve, reject) => { socket.onopen = resolve; socket.onerror = reject })
let id = 0
const pending = new Map(), errors = []
socket.onmessage = event => {
  const body = JSON.parse(event.data)
  if (body.id) { const callbacks = pending.get(body.id); pending.delete(body.id); body.error ? callbacks.reject(body.error) : callbacks.resolve(body.result) }
  if (body.method === 'Runtime.exceptionThrown') {
    const detail = body.params.exceptionDetails
    const message = detail.text + ' ' + (detail.exception?.description || '')
    if (!message.includes('chrome-extension://')) errors.push(message)
  }
}
const command = (method, params = {}) => new Promise((resolve, reject) => {
  const current = ++id
  const timeout = setTimeout(() => { pending.delete(current); reject(new Error(`CDP timeout: ${method}`)) }, 20000)
  pending.set(current, { resolve: value => { clearTimeout(timeout); resolve(value) }, reject: value => { clearTimeout(timeout); reject(value) } }); socket.send(JSON.stringify({ id: current, method, params }))
})
const evaluate = async expression => {
  const result = await command('Runtime.evaluate', { expression, awaitPromise: true, returnByValue: true })
  if (result.exceptionDetails) throw new Error(result.exceptionDetails.exception?.description||result.exceptionDetails.text)
  return result.result.value
}
const folder=path.resolve(process.env.HUNYUAN_JOBS_DIR || '../operations/deliverables/hunyuan-heads-20261006'),jobsFile=path.join(folder,'jobs.json')
const responses=[],requests=new Map();let headers,apiOrigin
socket.addEventListener('message',event=>{
 const b=JSON.parse(event.data)
 if(b.method==='Network.requestWillBeSent'&&b.params.request.url.includes('/api/3d/')){headers=b.params.request.headers;apiOrigin=new URL(b.params.request.url).origin}
 if(b.method==='Network.responseReceived'&&b.params.response.mimeType.includes('json'))requests.set(b.params.requestId,b.params.response.url)
 if(b.method==='Network.loadingFinished'&&requests.has(b.params.requestId))command('Network.getResponseBody',{requestId:b.params.requestId}).then(r=>{try{responses.push({url:requests.get(b.params.requestId),body:JSON.parse(r.body)})}catch{/* Ignore non-JSON responses. */}}).catch(()=>{})
})
const phase=process.argv[2]||'inspect',sleep=ms=>new Promise(r=>setTimeout(r,ms))
await command('Runtime.enable');await command('Network.enable')
if(phase==='inspect'){
 await evaluate("(()=>{const e=[...document.querySelectorAll('*')].filter(e=>e.children.length===0&&e.textContent.trim()==='文生3D'&&e.getBoundingClientRect().width>0).sort((a,b)=>a.getBoundingClientRect().x-b.getBoundingClientRect().x)[0];e?.click()})()")
 await sleep(500)
 console.log(await evaluate("JSON.stringify({text:document.body.innerText.slice(0,1800),state:{button:!!document.querySelector('.sideBarLeft-generateBtn'),disabled:document.querySelector('.sideBarLeft-generateBtn')?.disabled,value:document.querySelector('textarea')?.value},generate:[...document.querySelectorAll('*')].reverse().find(e=>e.textContent.trim()==='立即生成')?.parentElement.outerHTML.slice(0,1800)})"))
}else{
 if(phase!=='submit'){await command('Page.reload');for(let i=0;i<40&&!headers;i++)await sleep(500);if(!headers)throw Error('No authenticated API request captured')}
 const request=route=>evaluate(`(async()=>{const r=await fetch(${JSON.stringify(apiOrigin)}+${JSON.stringify(route)},{headers:${JSON.stringify(headers)}});if(!r.ok)throw Error('Read status '+r.status);return r.json()})()`)
 const jobs=JSON.parse(await fs.readFile(jobsFile,'utf8'))
 if(phase==='submit'){
  const quota={remainQuota:await evaluate("Number(document.body.innerText.match(/API\\n(\\d+)/)?.[1]||0)")};console.log('available quota',quota.remainQuota)
  if(!(quota.remainQuota>=jobs.filter(j=>!j.creationId).length))throw Error('Insufficient free quota; no submission')
  await evaluate("(()=>{const e=[...document.querySelectorAll('*')].filter(e=>e.children.length===0&&e.textContent.trim()==='文生3D'&&e.getBoundingClientRect().width>0).sort((a,b)=>a.getBoundingClientRect().x-b.getBoundingClientRect().x)[0];e?.click()})()")
  for(let i=0;i<40;i++){
   if(await evaluate("!!document.querySelector('textarea')"))break
   await evaluate("(()=>{const e=[...document.querySelectorAll('*')].reverse().find(e=>e.textContent.trim()==='文生3D'||e.textContent.trim()==='立即开始');e?.click()})()")
   await sleep(500)
  }
  for(const job of jobs.filter(j=>!j.creationId)){
   await evaluate(`(()=>{const e=document.querySelector('textarea');if(!e)throw Error('Text input missing');Object.getOwnPropertyDescriptor(HTMLTextAreaElement.prototype,'value').set.call(e,${JSON.stringify(job.prompt)});e.dispatchEvent(new Event('input',{bubbles:true}))})()`)
   for(let i=0;i<40;i++){if(await evaluate("!!document.querySelector('.sideBarLeft-generateBtn')&&!document.querySelector('.sideBarLeft-generateBtn').hasAttribute('disabled')"))break;await sleep(500)};const previous=responses.length
   const button=await evaluate("(()=>{const e=document.querySelector('.sideBarLeft-generateBtn');if(!e||e.hasAttribute('disabled'))throw Error('Generation control unavailable');e.scrollIntoView({block:'center'});return e.getBoundingClientRect().toJSON()})()")
   await command('Page.bringToFront')
   const x=button.x+button.width/2,y=button.y+button.height/2
   await command('Input.dispatchMouseEvent',{type:'mouseMoved',x,y});await command('Input.dispatchMouseEvent',{type:'mousePressed',button:'left',clickCount:1,x,y});await command('Input.dispatchMouseEvent',{type:'mouseReleased',button:'left',clickCount:1,x,y})
   let result
   for(let i=0;i<40;i++){result=responses.slice(previous).find(r=>new URL(r.url).pathname.includes('/generations'));if(result)break;await sleep(500)}
   if(!result?.body.creationsId){console.log(responses.slice(previous).map(r=>({path:new URL(r.url).pathname,keys:Object.keys(r.body)})));console.log(await evaluate('document.body.innerText.slice(-1800)'));throw Error('Submission not confirmed; will not retry')}
   job.creationId=result.body.creationsId;job.submitted=true;await fs.writeFile(jobsFile,JSON.stringify(jobs,null,2));console.log('submitted',job.id,job.creationId)
   await sleep(1000)
  }
 }else if(phase==='download'){
  await fs.mkdir(folder,{recursive:true});await command('Browser.setDownloadBehavior',{behavior:'allowAndName',downloadPath:folder,eventsEnabled:true})
  const downloads=[];socket.addEventListener('message',event=>{const b=JSON.parse(event.data);if(b.method==='Browser.downloadWillBegin')downloads.push(b.params)})
  for(const job of jobs){
   if(!job.creationId)continue
   const d=await request('/api/3d/creations/detail?creationsId='+encodeURIComponent(job.creationId))
   const candidates=d.result?.filter(r=>r.status==='success')||[],asset=candidates[Number(process.env.HEAD_CANDIDATE||0)]
   if(!asset){console.log('not ready',job.id,d.status);continue}
   const url=asset.urlResult.textureGlb||asset.urlResult.glb;if(!url)throw Error('No model file')
   const output=path.join(folder,job.id+'.glb');if(await fs.stat(output).catch(()=>false)){console.log('existing',job.id);continue}
   const before=downloads.length
   await evaluate(`(()=>{const a=document.createElement('a');a.href=${JSON.stringify(url)};a.download=${JSON.stringify(job.id+'.glb')};document.body.append(a);a.click();a.remove()})()`)
   let saved=false
   for(let i=0;i<90;i++){
    const event=downloads[before]
    if(event){const data=await fs.readFile(path.join(folder,event.guid)).catch(()=>null);if(data&&data.length>12&&data.readUInt32LE(0)===0x46546c67&&data.readUInt32LE(8)===data.length){await fs.rename(path.join(folder,event.guid),output);job.assetId=asset.assetId;job.modelType=d.modelType;job.originalFile=job.id+'.glb';job.downloaded=true;job.candidate=Number(process.env.HEAD_CANDIDATE||0);saved=true;console.log('downloaded',job.id,data.length);break}}
    await sleep(500)
   }
   await fs.writeFile(jobsFile,JSON.stringify(jobs,null,2));if(!saved)throw Error('Download incomplete; original task retained')
  }
 }else if(phase==='status'){
  for(const job of jobs){if(!job.creationId)continue;const d=await request('/api/3d/creations/detail?creationsId='+encodeURIComponent(job.creationId));console.log(JSON.stringify({id:job.id,status:d.status,results:d.result?.map(r=>({status:r.status,assetId:r.assetId,formats:Object.keys(r.urlResult||{})}))}))}
 }
}
socket.close()

