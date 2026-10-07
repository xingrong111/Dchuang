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
const pending = new Map(), errors = [], reports = []
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
try {
  const fixture = JSON.parse(await fs.readFile('../.acceptance/fixture.json', 'utf8'))
  for (const width of [1440, 390]) {
    await command('Emulation.setDeviceMetricsOverride', { width, height: width === 390 ? 844 : 1000, deviceScaleFactor: 1, mobile: width === 390 })
    for (const route of (process.env.AUDIT_ROUTES?.split(',') || ['/', '/museum', '/model-library', '/community', '/shop', '/login', '/register', '/forgot-password', '/about', '/workshop', '/workshop/3d-editor', '/workshop/multi-modal-input', '/profile', '/admin'])) {
      console.log(`${width} ${route}`)
      const start = errors.length
      if (route === '/login') await evaluate(`localStorage.removeItem('user')`)
      await command('Page.navigate', { url: origin + route })
      await sleep(1800)
      if (route === '/shop/account' || route === '/profile' || route === '/admin' || route.startsWith('/workshop')) {
        const credentials = JSON.stringify({ email: fixture.email, password: fixture.password })
        await evaluate(`(async()=>{const r=await fetch('/api/auth/login',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(${credentials})});const j=await r.json();if(j.code!==200)throw Error('验收登录失败');localStorage.setItem('user',JSON.stringify(j.data));})()`)
        await command('Page.navigate', { url: origin + route }); await sleep(1800)
      }
      for (let attempt = 0; attempt < 20; attempt++) {
        if (!(await evaluate(`document.body.innerText.includes('模型加载中')`))) break
        await sleep(1000)
      }
      await sleep(700)
      const state = await evaluate(`({title:document.title,path:location.pathname,body:document.body.innerText.slice(0,220),overflow:document.documentElement.scrollWidth>innerWidth+2,width:innerWidth,canvas:document.querySelectorAll('canvas').length})`)
      const image = await command('Page.captureScreenshot', { format: 'png', captureBeyondViewport: false })
      const name = `${width}-${route.replace(/[^a-zA-Z0-9_-]/g, '-') || 'home'}.png`
      await fs.writeFile(path.join(directory, name), Buffer.from(image.data, 'base64'))
      reports.push({ route, width, ...state, exceptions: errors.slice(start), screenshot: name })
    }
  }
  await fs.writeFile(path.join(directory, process.env.AUDIT_REPORT || 'acceptance.json'), JSON.stringify(reports, null, 2))
  console.log(JSON.stringify({ pages: reports.length, exceptions: errors.length, overflows: reports.filter(item => item.overflow).map(item => `${item.width}:${item.route}`) }))
} finally { socket.close(); await fetch(`${debugging}/json/close/${target.id}`) }
