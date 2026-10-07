// Uses a separately launched local headless Edge instance; no external browser packages.
import fs from 'node:fs/promises'
import path from 'node:path'
const debugging = process.env.EDGE_DEBUG_URL || 'http://127.0.0.1:19222'
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
await command('Runtime.enable')
await command('Page.enable')
await command('Page.bringToFront')
await command('Emulation.setDeviceMetricsOverride',{width:1440,height:1000,deviceScaleFactor:1,mobile:false})
const sleep = ms => new Promise(resolve => setTimeout(resolve, ms))
if(process.env.HUNYUAN_DOWNLOAD){await fs.mkdir(path.resolve(process.env.HUNYUAN_DOWNLOAD),{recursive:true});await command('Browser.setDownloadBehavior',{behavior:'allow',downloadPath:path.resolve(process.env.HUNYUAN_DOWNLOAD),eventsEnabled:true})}
if(process.env.HUNYUAN_HOVER_DOWNLOAD){for(let i=0;i<40;i++){if(await evaluate("!!document.querySelector('button.native-edit__viewport-actionBar-download')"))break;await sleep(1000)}const r=await evaluate("document.querySelector('button.native-edit__viewport-actionBar-download').getBoundingClientRect().toJSON()");await command('Input.dispatchMouseEvent',{type:'mouseMoved',x:r.x+r.width/2,y:r.y+r.height/2});await sleep(500)}
if(process.env.HUNYUAN_SELECTOR){const selector=JSON.stringify(process.env.HUNYUAN_SELECTOR);const r=await evaluate(`(()=>{const e=document.querySelector(${selector});e.scrollIntoView({block:'center'});return e.getBoundingClientRect().toJSON()})()`);const x=r.x+r.width/2,y=r.y+r.height/2;await command('Input.dispatchMouseEvent',{type:'mouseMoved',x,y});await command('Input.dispatchMouseEvent',{type:'mousePressed',x,y,button:'left',clickCount:1});await command('Input.dispatchMouseEvent',{type:'mouseReleased',x,y,button:'left',clickCount:1});await sleep(4000)}
if (process.env.HUNYUAN_MOUSE) { const [x,y]=process.env.HUNYUAN_MOUSE.split(',').map(Number); await command('Input.dispatchMouseEvent',{type:'mouseMoved',x,y}); if(process.env.HUNYUAN_CLICK){await command('Input.dispatchMouseEvent',{type:'mousePressed',x,y,button:'left',clickCount:1});await command('Input.dispatchMouseEvent',{type:'mouseReleased',x,y,button:'left',clickCount:1})} }
if (process.env.HUNYUAN_FILE) {
 const doc = await command('DOM.getDocument'); const node = await command('DOM.querySelector', {nodeId:doc.root.nodeId,selector:'input[type=file]'});
 await command('DOM.setFileInputFiles', {nodeId:node.nodeId,files:[path.resolve(process.env.HUNYUAN_FILE)]});
 await sleep(6000)
}
if (process.env.HUNYUAN_ACTION) console.log(await evaluate(process.env.HUNYUAN_ACTION))
await sleep(1500)
console.log(await evaluate('document.body.innerText.slice(0,12000)'))
const photo=await command('Page.captureScreenshot',{format:'png'});await fs.writeFile(path.join(directory,'hunyuan-entry.png'),Buffer.from(photo.data,'base64'))
socket.close()
