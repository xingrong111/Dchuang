// Uses a separately launched local headless Edge instance; no external browser packages.
import fs from 'node:fs/promises'
import path from 'node:path'
const origin = process.env.AUDIT_ORIGIN || 'http://127.0.0.1:15174'
const debugging = process.env.EDGE_DEBUG_URL || 'http://127.0.0.1:19222'
const directory = path.resolve('reports/browser')
await fs.mkdir(directory, { recursive: true })
const target = await (await fetch(`${debugging}/json/new?about:blank`, { method: 'PUT' })).json()
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
const sleep = ms => new Promise(resolve => setTimeout(resolve, ms))
const checks=[]
const check=(name,value)=>{if(!value)throw new Error(name);checks.push({name,passed:true});console.log(name)}
const click=label=>evaluate(`(()=>{const b=[...document.querySelectorAll('button')].find(x=>x.textContent.trim()===${JSON.stringify(label)});if(!b)throw Error('Button missing');b.click()})()`)
const ready=async selector=>{for(let i=0;i<30;i++){if(await evaluate(`!!document.querySelector(${JSON.stringify(selector)})`))return;await sleep(500)}throw Error(`Page not ready: ${selector}`)}
try {
 for(const width of [1440,390]) {
  await command('Emulation.setDeviceMetricsOverride',{width,height:1000,deviceScaleFactor:1,mobile:width===390})
  await command('Page.navigate',{url:origin+'/shop/designs'});await ready('.product')
  for(let index=0;index<5;index++) {
   await evaluate(`document.querySelectorAll('.detail-button')[${index}].click()`);await sleep(250)
   await ready('.view-buttons');await click('旋转3D模型');await ready('.model-preview canvas')
   for(let attempt=0;attempt<40;attempt++){if(await evaluate(`!document.querySelector('.model-message')`))break;await sleep(500)}
   check(`${width}:${index}:model loaded`,await evaluate(`!document.querySelector('.model-message')`))
   check(`${width}:${index}:model bounds`,await evaluate(`(()=>{const b=document.querySelector('.model-preview canvas').getBoundingClientRect();return b.width>100&&b.height>100&&b.right<=innerWidth+2})()`))
   check(`${width}:${index}:GLB download`,await evaluate(`(async()=>{const a=[...document.querySelectorAll('.visual-panel a')].find(a=>a.download);const r=await fetch(a.href);return r.ok&&new DataView(await r.arrayBuffer()).getUint32(0,true)===0x46546c67})()`))
   await click('重置视角');await sleep(250)
   const picture=await command('Page.captureScreenshot',{format:'png'});await fs.writeFile(path.join(directory,`${width}-product-${index}-3d.png`),Buffer.from(picture.data,'base64'))
   await click('设计效果图');await sleep(250)
   check(`${width}:${index}:viewer cleanup`,await evaluate(`!document.querySelector('.model-preview canvas')`))
   await evaluate(`document.querySelector('.el-dialog__headerbtn').click()`);await sleep(600)
  }
 }
 check('no application exceptions',errors.length===0)
 await fs.writeFile(path.join(directory,'product-model-flows.json'),JSON.stringify(checks,null,2));console.log(JSON.stringify({checks:checks.length,passed:true}))
}finally{socket.close();await fetch(`${debugging}/json/close/${target.id}`)}
