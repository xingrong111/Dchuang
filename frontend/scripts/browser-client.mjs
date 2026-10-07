// 无第三方依赖的本地浏览器验收工具，使用 Chrome DevTools Protocol。
import { writeFile } from 'node:fs/promises'
export async function connectBrowser(port = 19225) {
  const targets = await (await fetch(`http://127.0.0.1:${port}/json/list`)).json()
  const target = targets.find(tab => tab.type === 'page')
  if (!target) throw new Error('无浏览器页面，请先启动本地无界面 Edge/Chrome')
  const socket = new WebSocket(target.webSocketDebuggerUrl)
  await new Promise((resolve, reject) => { socket.addEventListener('open', resolve, { once: true }); socket.addEventListener('error', reject, { once: true }) })
  let sequence = 0
  const pending = new Map(), errors = [], network = []
  socket.addEventListener('message', event => {
    const message = JSON.parse(event.data)
    if (message.id) {
      const promise = pending.get(message.id)
      if (promise) { pending.delete(message.id); clearTimeout(promise.timer); message.error ? promise.reject(new Error(message.error.message)) : promise.resolve(message.result) }
    }
    if (message.method === 'Runtime.exceptionThrown') {
      const details = message.params.exceptionDetails
      const description = details.exception?.description || ''
      if (!description.includes('chrome-extension://') && !details.url?.startsWith('chrome-extension://')) errors.push(details.text + ': ' + description)
    }
    if (message.method === 'Network.responseReceived' && message.params.response.status >= 400) network.push({ status: message.params.response.status, url: message.params.response.url })
  })
  const send = (method, params = {}) => new Promise((resolve, reject) => {
    const id = ++sequence, timer = setTimeout(() => { pending.delete(id); reject(new Error(`CDP timeout: ${method}`)) }, 45000)
    pending.set(id, { resolve, reject, timer }); socket.send(JSON.stringify({ id, method, params }))
  })
  const evaluate = async expression => {
    const response = await send('Runtime.evaluate', { expression, awaitPromise: true, returnByValue: true })
    if (response.exceptionDetails) throw new Error(response.exceptionDetails.exception?.description || response.exceptionDetails.text)
    return response.result.value
  }
  const waitFor = async (expression, timeout = 15000) => {
    const deadline = Date.now() + timeout
    while (Date.now() < deadline) {
      if (await evaluate(expression)) return
      await new Promise(resolve => setTimeout(resolve, 100))
    }
    throw new Error('等待页面条件超时: ' + expression)
  }
  const navigate = async url => { await send('Page.navigate', { url }); await waitFor(`location.href === ${JSON.stringify(url)} && document.readyState === 'complete' && !!document.querySelector('.app-nav')`) }
  const click = async (selector, text) => evaluate(`(() => { const element = [...document.querySelectorAll(${JSON.stringify(selector)})].find(e => ${text === undefined ? 'true' : `e.textContent.trim() === ${JSON.stringify(text)}`}); if (!element) throw new Error('缺少按钮/链接'); element.click(); })()`)
  const fill = async (selector, value) => evaluate(`(() => { const element=document.querySelector(${JSON.stringify(selector)}); if (!element) throw new Error('缺少输入框'); const proto=element.tagName==='TEXTAREA'?HTMLTextAreaElement.prototype:HTMLInputElement.prototype; Object.getOwnPropertyDescriptor(proto,'value').set.call(element,${JSON.stringify(value)}); element.dispatchEvent(new Event('input',{bubbles:true})); element.dispatchEvent(new Event('change',{bubbles:true})); })()`)
  await send('Page.enable'); await send('Runtime.enable'); await send('Network.enable')
  return { send, evaluate, waitFor, navigate, click, fill, errors, network,
    screenshot: async path => { const data = await send('Page.captureScreenshot', { captureBeyondViewport: true }); await writeFile(path, Buffer.from(data.data, 'base64')) },
    close: () => socket.close() }
}
