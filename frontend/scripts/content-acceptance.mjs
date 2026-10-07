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
const input=value=>evaluate(`(()=>{const i=document.querySelector('.filters input,.section-heading input');i.value=${JSON.stringify(value)};i.dispatchEvent(new Event('input',{bubbles:true}))})()`)
const wait=()=>sleep(250)
const ready=async selector=>{for(let i=0;i<30;i++){if(await evaluate(`!!document.querySelector(${JSON.stringify(selector)})`))return;await sleep(500)}throw Error(`Page not ready: ${selector}`)}
try {
 for(const width of [1440,390]) {
  await command('Emulation.setDeviceMetricsOverride',{width,height:1000,deviceScaleFactor:1,mobile:width===390})
  await command('Page.navigate',{url:origin+'/shop/designs'});await ready('.product')
  check(`${width}:five concepts`,await evaluate(`document.querySelectorAll('.product').length===5`))
  check(`${width}:no purchase controls`,await evaluate(`![...document.querySelectorAll('button')].some(b=>/立即购买|购物车|去结算/.test(b.textContent))`))
  await click('纸品文具');await wait();check(`${width}:category`,await evaluate(`document.querySelectorAll('.product').length===2`))
  await input('not-found-xyz');await wait();check(`${width}:empty`,await evaluate(`!!document.querySelector('.empty')`))
  await click('清除筛选');await wait();check(`${width}:reset`,await evaluate(`document.querySelectorAll('.product').length===5`))
  await click('阅读设计说明 ↗');await wait();check(`${width}:detail`,await evaluate(`document.querySelector('.el-dialog').innerText.includes('材料方向')`))
  check(`${width}:detail fits`,await evaluate(`document.documentElement.scrollWidth<=innerWidth+2`))
  await command('Page.captureScreenshot',{format:'png'}).then(r=>fs.writeFile(path.join(directory,`${width}-concept-detail.png`),Buffer.from(r.data,'base64')))
  await evaluate(`document.querySelector('.el-dialog__headerbtn').click()`);await wait()
  await command('Page.navigate',{url:origin+'/museum'});await ready('.exhibit-grid article')
  check(`${width}:five exhibits`,await evaluate(`document.querySelectorAll('.exhibit-grid article').length===5`))
  await click('地域对照');await wait();check(`${width}:regional split`,await evaluate(`document.querySelectorAll('.exhibit-grid article').length===2`))
  await click('惠山泥人');await wait();check(`${width}:huishan split`,await evaluate(`document.querySelectorAll('.exhibit-grid article').length===3`))
  await click('观察细节与来源 ↗');await wait();check(`${width}:source disclosure`,await evaluate(`document.querySelector('.el-dialog').innerText.includes('使用许可待确认')`))
  await evaluate(`document.querySelector('.gallery button:nth-child(2)').click()`);await wait();check(`${width}:gallery`,await evaluate(`document.querySelector('.main-photo').src.endsWith('material-06.webp')`))
  check(`${width}:all images load`,await evaluate(`(async()=>{document.querySelectorAll('img').forEach(i=>i.loading='eager');await Promise.all([...document.images].map(i=>Promise.race([i.decode().catch(()=>{}),new Promise(r=>setTimeout(r,6000))])));return [...document.images].every(i=>i.naturalWidth>0)})()`))
 }
 check('no application exceptions',errors.length===0)
 await fs.writeFile(path.join(directory,'content-flows.json'),JSON.stringify(checks,null,2));console.log(JSON.stringify({checks:checks.length,passed:true}))
}finally{socket.close();await fetch(`${debugging}/json/close/${target.id}`)}
