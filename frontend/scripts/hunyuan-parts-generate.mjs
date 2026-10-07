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


const sleep=ms=>new Promise(r=>setTimeout(r,ms)),folder=path.resolve('../operations/deliverables/workshop-hunyuan');await fs.mkdir(folder,{recursive:true})
const jobs=JSON.parse(await fs.readFile(path.join(folder,'jobs.json'),'utf8'));const responses=[];const requests=new Map();
socket.addEventListener('message',async event=>{const b=JSON.parse(event.data);if(b.method==='Network.requestWillBeSent'&&b.params.request.url.includes('/creations/'))console.log('api request',new URL(b.params.request.url).pathname,b.params.request.method,[...new URL(b.params.request.url).searchParams.keys()],b.params.request.postData?JSON.parse(b.params.request.postData):[]);if(b.method==='Network.responseReceived'&&b.params.response.mimeType.includes('json'))requests.set(b.params.requestId,b.params.response.url);if(b.method==='Network.loadingFinished'&&requests.has(b.params.requestId)){try{const url=requests.get(b.params.requestId),result=await command('Network.getResponseBody',{requestId:b.params.requestId});responses.push({url,body:JSON.parse(result.body)})}catch{/* Response may have been evicted. */}}})
await command('Network.enable');await command('Runtime.enable')
if(process.env.PART_SUBMIT==='1')for(const job of jobs.filter(j=>!j.submitted)){
 await evaluate(`(()=>{const e=document.querySelector('textarea');Object.getOwnPropertyDescriptor(HTMLTextAreaElement.prototype,'value').set.call(e,${JSON.stringify(job.prompt)});e.dispatchEvent(new Event('input',{bubbles:true}));return true})()`);await sleep(200)
 const previous=responses.length
 const ok=await evaluate(`(()=>{const e=document.querySelector('button.sideBarLeft-generateBtn');if(!e||e.disabled)return false;e.click();return true})()`)
 if(!ok){console.log('generation button unavailable; stopped');break}
 for(let i=0;i<30;i++){if(responses.slice(previous).some(r=>new URL(r.url).pathname==='/api/3d/creations/generations'))break;await sleep(1000)}
 const creation=responses.slice(previous).find(r=>new URL(r.url).pathname==='/api/3d/creations/generations')?.body.creationsId
 if(!creation){console.log('submission unconfirmed; stopped without retry',job.id);break}
 job.submitted=true;job.creationId=creation;await fs.writeFile(path.join(folder,'jobs.json'),JSON.stringify(jobs,null,2));console.log('submitted',job.id);await sleep(1000)
 const quota=responses.findLast(r=>new URL(r.url).pathname==='/api/3d/quotainfo')?.body.remainQuota;if(quota===0)break
}
await sleep(5000)
const details=responses.filter(r=>new URL(r.url).pathname==='/api/3d/creations/detail')
console.log(JSON.stringify(details.slice(-3).map(r=>({origin:new URL(r.url).origin,queryKeys:[...new URL(r.url).searchParams.keys()],id:r.body.id,status:r.body.status,result:r.body.result?.map(s=>({status:s.status,keys:Object.keys(s.urlResult||{})}))}))))
const listed=responses.findLast(r=>new URL(r.url).pathname==='/api/3d/creations/list');if(listed)console.log('list structure',Object.keys(listed.body))
socket.close()




