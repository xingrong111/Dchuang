// Uses a separately launched local headless Edge instance; no external browser packages.
import fs from 'node:fs/promises'
import path from 'node:path'
const debugging = 'http://127.0.0.1:19223'
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
  if (result.exceptionDetails) throw new Error(result.exceptionDetails.text)
  return result.result.value
}



const sleep=ms=>new Promise(r=>setTimeout(r,ms)),folder=path.resolve('../operations/deliverables/workshop-hunyuan');const jobs=JSON.parse(await fs.readFile(path.join(folder,'jobs.json'),'utf8'))
let headers,apiOrigin
socket.addEventListener('message',event=>{const b=JSON.parse(event.data);if(b.method==='Network.requestWillBeSent'&&b.params.request.url.includes('/api/3d/creations/')){headers=b.params.request.headers;apiOrigin=new URL(b.params.request.url).origin}})
const downloadEvents=[]
socket.addEventListener('message',event=>{const b=JSON.parse(event.data);if(b.method==='Browser.downloadWillBegin')downloadEvents.push(b.params)})
await command('Network.enable');await command('Runtime.enable');await command('Browser.setDownloadBehavior',{behavior:'allowAndName',downloadPath:folder,eventsEnabled:true})
await command('Page.reload')
for(let i=0;i<30&&!headers;i++)await sleep(1000)
if(!headers)throw Error('No active task request captured')
const request=async route=>evaluate(`(async()=>{const r=await fetch(${JSON.stringify(apiOrigin)}+${JSON.stringify(route)},{headers:${JSON.stringify(headers)},...(${JSON.stringify(route)}.endsWith('/list')?{method:'POST',body:'{}'}:{})});if(!r.ok)throw Error('read status '+r.status);return r.json()})()`)
const list=await request('/api/3d/creations/list')
console.log('listed',list.totalCount,list.creations?.length)
const sage=list.creations?.find(c=>c.prompt?.includes('寿星头部'));if(sage)jobs.find(j=>j.id==='head-sage').creationId=sage.id
for(const job of jobs){
 if(!job.creationId){console.log('missing task id',job.id);continue}
 const detail=await request('/api/3d/creations/detail?creationsId='+encodeURIComponent(job.creationId))
 job.prompt=detail.prompt;job.modelType=detail.modelType
 const asset=detail.result?.filter(r=>r.status==='success')[Number(process.env.PART_CANDIDATE||0)]
 if(!asset){console.log('not ready',job.id);continue}
 const url=asset.urlResult.textureGlb||asset.urlResult.glb
 if(!url){console.log('no GLB',job.id);continue}
 const output=path.join(folder,job.id+'.glb');if(await fs.stat(output).catch(()=>false)){console.log('existing',job.id);continue}
 const previous=downloadEvents.length
 await evaluate(`(()=>{const a=document.createElement('a');a.href=${JSON.stringify(url)};a.download=${JSON.stringify(job.id+'.glb')};document.body.append(a);a.click();a.remove()})()`)
 for(let i=0;i<90;i++){const event=downloadEvents[previous];if(event){const file=path.join(folder,event.guid);const data=await fs.readFile(file).catch(()=>null);if(data&&data.length>=12&&data.readUInt32LE(0)===0x46546c67&&data.readUInt32LE(8)===data.length){await fs.rename(file,output);job.assetId=asset.assetId;job.originalFile=job.id+'.glb';job.downloaded=true;console.log('downloaded',job.id,data.length);break}}await sleep(1000)}
 await fs.writeFile(path.join(folder,'jobs.json'),JSON.stringify(jobs,null,2))
}
await fs.writeFile(path.join(folder,'jobs.json'),JSON.stringify(jobs,null,2));socket.close()

