import fs from 'node:fs/promises'
const origin = process.env.AUDIT_ORIGIN || 'http://127.0.0.1:15174'
const debuggerUrl = 'http://127.0.0.1:19222'
const target = await (await fetch(`${debuggerUrl}/json/new?about:blank`, { method: 'PUT' })).json()
const socket = new WebSocket(target.webSocketDebuggerUrl)
await new Promise((resolve, reject) => { socket.onopen = resolve; socket.onerror = reject })
let id = 0
const pending = new Map(), checks = []
socket.onmessage = event => { const body = JSON.parse(event.data); if (body.id) { const entry = pending.get(body.id); pending.delete(body.id); body.error ? entry.reject(body.error) : entry.resolve(body.result) } }
const command = (method, params = {}) => new Promise((resolve, reject) => {
  const current = ++id, timer = setTimeout(() => { pending.delete(current); reject(Error(method + ' timeout')) }, 20000)
  pending.set(current, { resolve: result => { clearTimeout(timer); resolve(result) }, reject: error => { clearTimeout(timer); reject(error) } })
  socket.send(JSON.stringify({ id: current, method, params }))
})
const evaluate = async expression => {
  const result = await command('Runtime.evaluate', { expression, awaitPromise: true, returnByValue: true })
  if (result.exceptionDetails) throw Error(result.exceptionDetails.exception?.description || result.exceptionDetails.text)
  return result.result.value
}
const sleep = ms => new Promise(resolve => setTimeout(resolve, ms))
const navigate = async route => { await command('Page.navigate', { url: origin + route }); await sleep(1500) }
const clickText = async text => evaluate(`(()=>{const b=[...document.querySelectorAll('button')].find(b=>b.innerText.trim().includes(${JSON.stringify(text)}));if(!b)throw Error('按钮未找到');b.click();return true})()`)
const check = (name, passed) => { checks.push({ name, passed: !!passed }); if (!passed) throw Error(name) }
try {
  await command('Page.enable'); await command('Runtime.enable'); await command('Page.bringToFront')
  const fixture = JSON.parse(await fs.readFile('../.acceptance/fixture.json', 'utf8'))
  await navigate('/login')
  await evaluate('localStorage.clear()'); await navigate('/login')
  await evaluate(`(()=>{const inputs=document.querySelectorAll('.login-form input, .el-form input');const values=${JSON.stringify([fixture.email, fixture.password])};inputs.forEach((input,i)=>{input.value=values[i];input.dispatchEvent(new Event('input',{bubbles:true}))});document.querySelector('.login-btn').click()})()`)
  await sleep(2000)
  check('UI登录写入访问令牌', await evaluate(`!!JSON.parse(localStorage.getItem('user')||'null')?.token`))
  await navigate('/community')
  await clickText('查看详情'); await sleep(700)
  check('作品详情打开', await evaluate(`!!document.querySelector('.work-detail')`))
  await evaluate(`(()=>{const input=document.querySelector('.comments-section input');input.value='本地浏览器验收评论';input.dispatchEvent(new Event('input',{bubbles:true}))})()`)
  await clickText('发表评论'); await sleep(700)
  check('UI评论写入并显示', await evaluate(`document.querySelector('.comment-list').innerText.includes('本地浏览器验收评论')`))
  await navigate('/shop')
  await clickText('加入购物车'); await sleep(700)
  await evaluate(`document.querySelector('.cart-btn').click()`); await sleep(500)
  await clickText('去结算'); await sleep(500)
  await evaluate(`(()=>{const fields=document.querySelectorAll('.checkout-address input[placeholder^=请输入],.checkout-address textarea');const values=['本地验收','13800000000','独立测试环境，不实际发货','浏览器验收'];fields.forEach((field,i)=>{field.value=values[i];field.dispatchEvent(new Event('input',{bubbles:true}));});})()`)
  await clickText('提交订单'); await sleep(1000)
  await navigate('/profile')
  await evaluate(`[...document.querySelectorAll('.el-tabs__item')].find(item=>item.innerText.includes('我的订单')).click()`); await sleep(700)
  check('UI订单创建并显示', await evaluate(`document.body.innerText.includes('待确认') && document.body.innerText.includes('验收泥人')`))
  await clickText('取消订单'); await sleep(700)
  check('UI取消订单', await evaluate(`document.body.innerText.includes('已取消')`))
  await navigate('/workshop/multi-modal-input')
  await evaluate(`(()=>{const field=document.querySelector('textarea');field.value='惠山泥人阿福，朱红袍服，怀抱瑞狮';field.dispatchEvent(new Event('input',{bubbles:true}))})()`)
  await clickText('提交创作'); await sleep(3500)
  check('演示创作结果', await evaluate(`document.body.innerText.includes('演示') && !!document.querySelector('canvas')`))
  await navigate('/workshop/3d-editor')
  check('3D编辑器六个部件分类',await evaluate(`document.querySelectorAll('.category-grid button').length===6`))
  await evaluate(`Array.from(document.querySelectorAll('.category-grid button')).find(e=>e.innerText.includes('底座')).click()`);await sleep(2500)
  check('四个具体底座预览',await evaluate(`document.querySelectorAll('.part-preview canvas').length===4`))
  await evaluate(`document.querySelector('.part-item>button').click()`);await sleep(500)
  check('3D编辑器部件可添加',await evaluate(`document.querySelector('.canvas-container canvas').width>200`))
  await fs.mkdir('reports/browser', { recursive: true })
  await fs.writeFile('reports/browser/flows.json', JSON.stringify({ checks, provider: 'mock', realExternalServices: false }, null, 2))
  console.log(JSON.stringify(checks))
} catch (error) {
  await fs.mkdir('reports/browser', { recursive: true })
  await fs.writeFile('reports/browser/flows.json', JSON.stringify({ checks, failure: error.message }, null, 2))
  throw error
} finally { socket.close(); await fetch(`${debuggerUrl}/json/close/${target.id}`) }
