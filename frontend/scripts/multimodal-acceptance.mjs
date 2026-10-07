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

  await command('Page.addScriptToEvaluateOnNewDocument',{source:`window.SpeechRecognition=class {start(){window.testSpeech=this} stop(){this.onend?.()} abort(){window.speechAborts=(window.speechAborts||0)+1;this.onend?.()}}`})
  await navigate('/workshop/multi-modal-input')
  await clickText('提交创作');await sleep(200)
  check('empty text blocked',await evaluate(`document.body.innerText.includes('请先填写作品描述')`))
  await evaluate(`(()=>{const e=document.querySelector('#creation-text');e.value='朱红衣袍阿福';e.dispatchEvent(new Event('input',{bubbles:true}))})()`)
  await clickText('提交创作');await sleep(6000)
  check('text task result',await evaluate(`document.body.innerText.includes('演示任务完成')&&!!document.querySelector('.preview-panel canvas')`))
  await clickText('语音输入');await clickText('开始语音输入');await sleep(100)
  check('voice listening state',await evaluate(`document.body.innerText.includes('停止收音')`))
  await evaluate(`testSpeech.onresult({results:[[{transcript:'青绿陶土猫'}]]});testSpeech.onend()`)
  check('voice transcription editable',await evaluate(`document.querySelector('#voice-text').value==='青绿陶土猫'&&!document.querySelector('#voice-text').disabled`))
  await clickText('开始语音输入');await evaluate(`testSpeech.onerror({error:'not-allowed'});testSpeech.onend()`)
  check('microphone permission error',await evaluate(`document.body.innerText.includes('麦克风权限被拒绝')`))
  await clickText('开始语音输入');await clickText('图像输入');await sleep(100)
  check('switch stops microphone',await evaluate(`speechAborts>0`))
  const upload=async(path)=>{const {root}=await command('DOM.getDocument');const {nodeId}=await command('DOM.querySelector',{nodeId:root.nodeId,selector:'#reference-image'});await command('DOM.setFileInputFiles',{nodeId,files:[path]});await sleep(600)}
  await upload(process.cwd()+'/package.json')
  check('invalid file blocked',await evaluate(`document.body.innerText.includes('请选择PNG')&&!document.querySelector('.image-preview')`))
  const files=await fs.readdir('public/content');const webp=files.find(name=>name.endsWith('.webp'))
  await upload(process.cwd()+'/public/content/'+webp)
  check('webp preview decoded',await evaluate(`document.querySelector('.image-preview')?.naturalWidth>0`))
  await clickText('风格分析');await sleep(2500)
  check('image upload and analysis',await evaluate(`!!document.querySelector('.analyze-result')`))
  await clickText('以图创作');await sleep(6000)
  check('image task result',await evaluate(`document.body.innerText.includes('演示任务完成')`))
  await upload(process.cwd()+'/package.json')
  check('invalid replacement clears old image',await evaluate(`!document.querySelector('.image-preview')&&[...document.querySelectorAll('button')].find(e=>e.innerText==='以图创作').disabled`))
  await upload(process.cwd()+'/public/content/'+webp);await clickText('移除图片')
  check('image removal',await evaluate(`!document.querySelector('.image-preview')`))
  await evaluate(`(async()=>{const blob=await(await fetch('/content/'+${JSON.stringify(webp)})).blob();const dt=new DataTransfer();dt.items.add(new File([blob],'dropped.webp',{type:'image/webp'}));document.querySelector('.drag-area').dispatchEvent(new DragEvent('drop',{bubbles:true,dataTransfer:dt}))})()`);await sleep(600)
  check('image drag and drop',await evaluate(`document.querySelector('.image-preview')?.naturalWidth>0`))
  for(const route of ['/','/museum','/workshop','/shop','/shop/designs','/community','/about','/help','/profile']){
    await navigate(route)
    check('visible wording '+route,await evaluate(`!/(\bAI\b|AI生成|人工智能)/i.test(document.body.innerText)`))
  }
  await fs.writeFile('reports/browser/multimodal.json',JSON.stringify({checks,provider:'mock',voiceHandlersSimulated:true,realMicrophoneTested:false},null,2));console.log(JSON.stringify(checks))
}finally{socket.close();await fetch(debuggerUrl+'/json/close/'+target.id)}

