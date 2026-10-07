import fs from 'node:fs/promises'
const origin='http://127.0.0.1:15176',debug='http://127.0.0.1:19223'
const target=await(await fetch(debug+'/json/new?about:blank',{method:'PUT'})).json(),socket=new WebSocket(target.webSocketDebuggerUrl)
await new Promise(resolve=>socket.onopen=resolve)
let id=0;const pending=new Map(),errors=[],checks=[]
socket.onmessage=event=>{const m=JSON.parse(event.data);if(m.id){const c=pending.get(m.id);pending.delete(m.id);m.error?c.reject(m.error):c.resolve(m.result)}else if(m.method==='Runtime.exceptionThrown')errors.push(m.params.exceptionDetails.text)}
const command=(method,params={})=>new Promise((resolve,reject)=>{const n=++id;pending.set(n,{resolve,reject});socket.send(JSON.stringify({id:n,method,params}))})
const evaluate=async expression=>{const r=await command('Runtime.evaluate',{expression,awaitPromise:true,returnByValue:true});if(r.exceptionDetails)throw Error(r.exceptionDetails.exception?.description||r.exceptionDetails.text);return r.result.value}
const sleep=ms=>new Promise(resolve=>setTimeout(resolve,ms))
const check=(name,passed)=>{checks.push({name,passed:!!passed});if(!passed)throw Error(name)}
try{
 await command('Page.enable');await command('Page.bringToFront');await command('Runtime.enable');await command('Page.navigate',{url:origin});await sleep(3000)
 await evaluate(`localStorage.clear();window.router=document.querySelector('#app').__vue_app__.config.globalProperties.$router;true`)
 const routes=['/','/museum','/workshop','/community','/shop','/community','/museum','/community','/shop/designs','/model-library','/about','/help','/privacy','/terms','/login','/register','/forgot-password']
 for(const width of [1366,390]){
  await command('Emulation.setDeviceMetricsOverride',{width,height:900,deviceScaleFactor:1,mobile:false})
  for(const path of routes){
   await evaluate(`router.push(${JSON.stringify(path)})`);await sleep(1000)
   for(let i=0;i<20;i++){if(await evaluate(`!document.querySelector('.loading-state')&&!document.querySelector('.products-area .el-loading-mask')`))break;await sleep(300)}
   const state=await evaluate(`({path:location.pathname,title:document.querySelector('main h1, main h2, main .page-title')?.textContent,works:document.querySelectorAll('.work-card').length,products:document.querySelectorAll('.product-card').length,overflow:document.documentElement.scrollWidth-innerWidth,images:[...document.querySelectorAll('main img')].filter(img=>img.complete&&!img.naturalWidth).map(img=>img.getAttribute('src')),text:document.querySelector('main')?.innerText})`)
   check(width+' '+path+' 内容可见',!!state.title||path==='/workshop')
   check(width+' '+path+' 无横向溢出',state.overflow<=2)
   check(width+' '+path+' 图片可用',state.images.length===0)
   if(path==='/community')check(width+' 社区无需刷新显示六件作品',state.works===6)
   if(path==='/shop'){check(width+' 商城显示十款文创',state.products===10);check(width+' 商城无设计展示字样',!state.text.includes('设计展示'));check(width+' 商城完整显示产品封面',await evaluate("[...document.querySelectorAll('.product-image img')].every(img=>getComputedStyle(img).objectFit==='contain')"))}
   if(path==='/')check('首页没有重复博物馆文化章节',!state.text.includes('从一抔泥土，认识彩塑'))
   if(['/community','/shop','/museum','/'].includes(path)){const shot=await command('Page.captureScreenshot',{format:'png'});await fs.writeFile('reports/browser/page-'+(path==='/'?'home':path.slice(1))+'-'+width+'.png',Buffer.from(shot.data,'base64'))}
  }
 }
 await evaluate(`router.push('/community')`);await sleep(1000)
 await evaluate(`(()=>{const input=document.querySelector('.search-bar input');input.value='莲生';input.dispatchEvent(new Event('input',{bubbles:true}));return true})()`);await sleep(900)
 check('社区关键词搜索',await evaluate(`document.querySelectorAll('.work-card').length===1&&document.querySelector('.work-title').textContent.includes('莲生')`))
 await evaluate(`document.querySelector('.view-detail-btn').click();true`)
 for(let i=0;i<80;i++){await sleep(150);if(await evaluate(`!!document.querySelector('.work-detail .model-preview canvas')&&!document.querySelector('.work-detail .model-message')`))break}
 check('社区详情三维模型加载成功',await evaluate(`!!document.querySelector('.work-detail .model-preview canvas')&&!document.querySelector('.work-detail .model-message')`))
 await evaluate(`router.push('/shop')`);await sleep(1000)
 await evaluate(`(()=>{const input=document.querySelector('.search-bar input');input.value='手账';input.dispatchEvent(new Event('input',{bubbles:true}));return true})()`);await sleep(900)
 check('商城关键词搜索',await evaluate(`document.querySelectorAll('.product-card').length===1&&document.querySelector('.product-name').textContent.includes('手账')`))
 check('无浏览器异常',errors.length===0)
}finally{await fs.writeFile('reports/browser/public-pages-audit.json',JSON.stringify({checks,errors},null,2));console.log(JSON.stringify({checks:checks.length,failed:checks.filter(c=>!c.passed),errors}));socket.close();await fetch(debug+'/json/close/'+target.id)}


