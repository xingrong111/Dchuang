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
  for(const category of ['底座','身体','头部','手臂','配件','宠物']){
   await evaluate(`Array.from(document.querySelectorAll('.category-grid button')).find(e=>e.querySelector('strong').innerText===${JSON.stringify(category)}).click()`)
   await sleep(200)
   for(let i=0;i<60;i++){if(await evaluate(`document.querySelectorAll('.part-preview canvas').length===4&&!document.querySelector('.part-preview .model-message')`))break;await sleep(500)}
   check(category+': four working previews',await evaluate(`document.querySelectorAll('.part-preview canvas').length===4&&!document.querySelector('.part-preview .model-message')`))
   await command('Page.bringToFront');await sleep(700)
   const image=await command('Page.captureScreenshot',{format:'png'});await fs.writeFile('reports/browser/parts-'+category+'.png',Buffer.from(image.data,'base64'))
   if(category==='手臂'){check('integrated body prevents duplicate arms',await evaluate(`document.querySelector('.part-item>button').disabled&&document.body.innerText.includes('身体已含双臂')`));await evaluate(`document.querySelector('.category-header button').click()`);continue}
   await evaluate(`document.querySelector('.part-item>button').click()`);await sleep(600)
   check(category+': added to editor',await evaluate(`document.querySelector('.params-panel input')?.disabled===false||document.body.innerText.includes('已自动拼接')`))
   await evaluate(`document.querySelector('.category-header button').click()`);await sleep(300)
  }
  await evaluate(`URL.createObjectURL=((original)=>blob=>{window.exportedModelBlob=blob;return original(blob)})(URL.createObjectURL.bind(URL))`)
  await clickText('导出模型');await sleep(200);await clickText('确认导出')
  for(let i=0;i<40;i++){if(await evaluate(`!!window.exportedModelBlob`))break;await sleep(500)}
  check('five-part assembly exports GLB',await evaluate(`(async()=>{const b=await window.exportedModelBlob.arrayBuffer(),v=new DataView(b),j=JSON.parse(new TextDecoder().decode(b.slice(20,20+v.getUint32(12,true))));window.assemblyExport=j;return v.getUint32(0,true)===0x46546c67&&j.meshes.length>=6&&j.images.length>=3})()`))
  check('assembly grounded and companion attached to pedestal',await evaluate(`(()=>{const j=window.assemblyExport,base=j.nodes.find(n=>n.extras?.category==='base'),pet=j.nodes.findIndex(n=>n.extras?.category==='pet');return Math.abs((base.translation?.[1]??base.matrix?.[13]??0)-.11)<1e-5&&base.children.includes(pet)&&j.nodes.filter(n=>n.extras?.category).length===5})()`))
  await command('Page.bringToFront');await sleep(500)
  const assembled=await command('Page.captureScreenshot',{format:'png'});await fs.writeFile('reports/browser/assembled-current.png',Buffer.from(assembled.data,'base64'))
  await evaluate(`document.body.dispatchEvent(new KeyboardEvent('keydown',{key:'Delete',bubbles:true}))`);await sleep(200)
  check('delete selected part resets anchors',await evaluate(`document.body.innerText.includes('部件已删除，锚点已重置')`))
  await evaluate(`(()=>{const dt=new DataTransfer();dt.setData('partId','pet-lion');document.querySelector('.canvas-container').dispatchEvent(new DragEvent('drop',{bubbles:true,dataTransfer:dt}))})()`);await sleep(500)
  check('drag part into editor',await evaluate(`document.body.innerText.includes('已自动拼接')`))
  for(const category of ['头部','身体']){
    await evaluate(`Array.from(document.querySelectorAll('.category-grid button')).find(e=>e.querySelector('strong').innerText===${JSON.stringify(category)}).click()`)
    await sleep(1800)
    await evaluate(`document.querySelectorAll('.part-item>button')[1].click()`);await sleep(1500)
    await evaluate(`document.querySelector('.category-header button').click();window.exportedModelBlob=null`)
    await clickText('导出模型');await sleep(200);await clickText('确认导出')
    for(let i=0;i<40;i++){if(await evaluate(`!!window.exportedModelBlob`))break;await sleep(500)}
    check(category+': replacement preserves five connected parts',await evaluate(`(async()=>{const b=await window.exportedModelBlob.arrayBuffer(),v=new DataView(b),j=JSON.parse(new TextDecoder().decode(b.slice(20,20+v.getUint32(12,true))));const parts=j.nodes.filter(n=>n.extras?.category),body=j.nodes.find(n=>n.extras?.category==='body');return parts.length===5&&parts.filter(n=>n.extras.category==='head').length===1&&['head','accessory'].every(c=>body.children.includes(j.nodes.findIndex(n=>n.extras?.category===c)))})()`))
  }
  await clickText('清空模型');await sleep(200)
  check('clear scene',await evaluate(`document.body.innerText.includes('模型已清空')`))
  await clickText('载入模型');await sleep(2500)
  check('load complete Hunyuan product',await evaluate(`document.body.innerText.includes('混元文创模型已载入')`))
  await command('Emulation.setDeviceMetricsOverride',{width:390,height:844,deviceScaleFactor:1,mobile:true})
  await evaluate(`Array.from(document.querySelectorAll('.category-grid button')).find(e=>e.innerText.includes('头部')).click()`);await sleep(2500)
  check('mobile category without horizontal overflow',await evaluate(`document.querySelectorAll('.part-preview canvas').length===4&&document.documentElement.scrollWidth<=innerWidth+2`))
  await fs.writeFile('reports/browser/workshop-parts-flows.json',JSON.stringify(checks,null,2));console.log(JSON.stringify(checks))
}finally{socket.close();await fetch(`${debuggerUrl}/json/close/${target.id}`)}



