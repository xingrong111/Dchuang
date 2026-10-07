import fs from 'node:fs/promises'
const origin = process.env.AUDIT_ORIGIN || 'http://127.0.0.1:15174'
const debuggerUrl = process.env.EDGE_DEBUG_URL || 'http://127.0.0.1:19222'
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
  const fixture = JSON.parse(await fs.readFile(process.env.AUDIT_FIXTURE || '../.acceptance/fixture.json', 'utf8'))
  await navigate('/login')
  await evaluate('localStorage.clear()'); await navigate('/login')
  for(let i=0;i<40;i++){if(await evaluate(`!!document.querySelector('.login-btn')`))break;await sleep(500)}
  await evaluate(`(()=>{const inputs=document.querySelectorAll('.login-form input, .el-form input');const values=${JSON.stringify([fixture.email, fixture.password])};inputs.forEach((input,i)=>{input.value=values[i];input.dispatchEvent(new Event('input',{bubbles:true}))});document.querySelector('.login-btn').click()})()`)
  await sleep(2000)
  check('UI登录写入访问令牌', await evaluate(`!!JSON.parse(localStorage.getItem('user')||'null')?.token`))
  await command('Emulation.setDeviceMetricsOverride',{width:1440,height:1000,deviceScaleFactor:1,mobile:false})
  await navigate('/workshop/3d-editor')
  for(let i=0;i<40;i++){if(await evaluate(`document.querySelectorAll('.category-grid button').length===6`))break;await sleep(500)}
  check('six part categories',await evaluate(`document.querySelectorAll('.category-grid button').length===6`))

  await evaluate('URL.createObjectURL=((original)=>blob=>{window.exportedModelBlob=blob;return original(blob)})(URL.createObjectURL.bind(URL))')
  async function add(category,index){await evaluate('Array.from(document.querySelectorAll(".category-grid button")).find(e=>e.querySelector("strong").innerText==='+JSON.stringify(category)+').click()');for(let i=0;i<60;i++){if(await evaluate('document.querySelectorAll(".part-preview canvas").length===4&&!document.querySelector(".part-preview .model-message")'))break;await sleep(300)}await evaluate('document.querySelectorAll(".part-item>button")['+index+'].click()');await sleep(500);for(let i=0;i<60;i++){if(await evaluate('!document.querySelector(".part-item>button").disabled'))break;await sleep(300)}await evaluate('document.querySelector(".category-header button").click()');await sleep(150)}
  for(let h=0;h<4;h++)for(let b=0;b<4;b++){
   await clickText('清空模型');await sleep(150);await add('头部',h);await add('身体',b);await sleep(300)
   await evaluate('window.exportedModelBlob=null');await clickText('导出模型');await sleep(150);await clickText('确认导出');for(let i=0;i<40;i++){if(await evaluate('!!window.exportedModelBlob'))break;await sleep(300)}
   const detail=await evaluate('(async()=>{const bytes=await window.exportedModelBlob.arrayBuffer(),v=new DataView(bytes),j=JSON.parse(new TextDecoder().decode(bytes.slice(20,20+v.getUint32(12,true))));const body=j.nodes.find(n=>n.extras?.category==="body"),headIndex=j.nodes.findIndex(n=>n.extras?.category==="head"),head=j.nodes[headIndex];const T=await import("/node_modules/.vite/deps/three.js"),m=head.matrix?new T.Matrix4().fromArray(head.matrix):new T.Matrix4().compose(new T.Vector3(...(head.translation||[0,0,0])),new T.Quaternion(...(head.rotation||[0,0,0,1])),new T.Vector3(...(head.scale||[1,1,1])));const actual=new T.Vector3(...head.extras.connection.selfPosition).applyMatrix4(m),target=new T.Vector3(...head.extras.connection.targetPosition),scale=new T.Vector3().setFromMatrixScale(m);return {connected:body.children.includes(headIndex),error:actual.distanceTo(target),scale:scale.x,expected:head.extras.fittedScale,anatomyFits:scale.x*head.extras.dimensions.anatomicalWidth<=body.extras.dimensions.shoulderWidth*.5+1e-6&&scale.x*head.extras.dimensions.anatomicalHeight<=body.extras.dimensions.headHeight+1e-6,neck:j.nodes.some(n=>n.name==="neck-joint"),head:head.extras.catalogId,body:body.extras.catalogId}})()')
   check('head-first '+detail.head+' + '+detail.body,detail.connected&&detail.anatomyFits&&detail.neck&&detail.error<1e-6&&Math.abs(detail.scale-detail.expected)<1e-6)
   if(h===0&&b===0){const image=await command('Page.captureScreenshot',{format:'png'});await fs.writeFile('reports/browser/head-first-current.png',Buffer.from(image.data,'base64'))}
  }
  await fs.writeFile('reports/browser/head-first-flows.json',JSON.stringify(checks,null,2));console.log(JSON.stringify(checks))
}finally{socket.close();await fetch(debuggerUrl+'/json/close/'+target.id)}
