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
  await navigate('/shop/account')
  await evaluate(`[...document.querySelectorAll('.el-tabs__item')].find(e=>e.innerText.includes('收货地址')).click()`)
  await evaluate(`(()=>{const fields=document.querySelectorAll('.account .el-form input,.account .el-form textarea');['商城验收','13800000000','测试环境，不实际发货'].forEach((value,i)=>{fields[i].value=value;fields[i].dispatchEvent(new Event('input',{bubbles:true}));})})()`)
  await clickText('保存地址');await sleep(800)
  check('UI保存默认地址',await evaluate(`document.body.innerText.includes('商城验收')&&document.body.innerText.includes('默认')`))
  await navigate('/shop');await evaluate(`(()=>{const b=[...document.querySelectorAll('button')].find(b=>b.innerText.trim()==='收藏');if(b)b.click()})()`);await sleep(600)
  check('UI商品收藏',await evaluate(`document.body.innerText.includes('已收藏')`))
  await clickText('加入购物车');await sleep(600)
  await evaluate(`document.querySelector('.cart-btn').click()`);await sleep(300);await clickText('去结算');await sleep(800)
  check('结算自动填入默认地址',await evaluate(`document.querySelector('input[placeholder="请输入收货人姓名"]').value==='商城验收'`))
  await clickText('提交订单');await sleep(800)
  await evaluate(`(async()=>{const headers={'Authorization':'Bearer '+JSON.parse(localStorage.getItem('user')).token,'Content-Type':'application/json'};const list=await(await fetch('/api/shop/orders',{headers})).json();const order=list.data.find(o=>o.status==='待确认'&&o.receiver==='商城验收');if(!order)throw Error('Order missing');sessionStorage.setItem('commerceOrder',order.id);for(const data of [{status:'待发货'},{status:'已发货',carrier:'测试物流',tracking_number:'ACCEPTANCE-ONLY'}]){const r=await fetch('/api/admin/orders/'+order.id,{method:'PUT',headers,body:JSON.stringify(data)});if(!r.ok)throw Error('Shipment failed')}})()`)
  await navigate('/shop/account')
  check('订单与运单记录显示',await evaluate(`document.body.innerText.includes('ACCEPTANCE-ONLY')`))
  await clickText('确认收货');await sleep(300);await evaluate(`document.querySelector('.el-message-box__btns button:last-child').click()`);await sleep(800)
  check('UI确认收货',await evaluate(`document.body.innerText.includes('已完成')`))
  await clickText('评价商品');await sleep(300)
  await evaluate(`(()=>{const input=document.querySelector('.el-dialog textarea');input.value='隔离验收环境的测试评价';input.dispatchEvent(new Event('input',{bubbles:true}))})()`)
  await clickText('提交评价');await sleep(700)
  await navigate('/shop');await clickText('详情');await sleep(700)
  check('评价显示在商品详情',await evaluate(`document.body.innerText.includes('隔离验收环境的测试评价')`))
  await navigate('/workshop/3d-editor?modelAsset=afu-desk')
  for(let i=0;i<30;i++){if(await evaluate(`document.querySelector('.params-panel input')?.disabled===false`))break;await sleep(500)}
  check('混元模型载入工坊',await evaluate(`document.querySelector('.params-panel input')?.disabled===false`))
  await evaluate(`URL.createObjectURL=((original)=>blob=>{window.exportedModelBlob=blob;return original(blob)})(URL.createObjectURL.bind(URL))`)
  await clickText('导出模型');await sleep(200);await clickText('确认导出')
  for(let i=0;i<40;i++){if(await evaluate(`!!window.exportedModelBlob`))break;await sleep(500)}
  check('工坊导出真实GLB',await evaluate(`(async()=>{const buffer=await window.exportedModelBlob.arrayBuffer();const view=new DataView(buffer);const model=JSON.parse(new TextDecoder().decode(buffer.slice(20,20+view.getUint32(12,true))));return view.getUint32(0,true)===0x46546c67&&model.images.length>=3&&model.meshes.length>0})()`))
  await fs.mkdir('reports/browser',{recursive:true});await fs.writeFile('reports/browser/commerce-flows.json',JSON.stringify(checks,null,2));console.log(JSON.stringify(checks))
}finally{socket.close();await fetch(`${debuggerUrl}/json/close/${target.id}`)}
