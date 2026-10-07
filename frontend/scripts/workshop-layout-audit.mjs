import fs from 'node:fs/promises'
const debug='http://127.0.0.1:19223',origin='http://127.0.0.1:15176'
const target=await(await fetch(debug+'/json/new?about:blank',{method:'PUT'})).json(),socket=new WebSocket(target.webSocketDebuggerUrl)
await new Promise(resolve=>socket.onopen=resolve)
let id=0;const pending=new Map()
socket.onmessage=e=>{const m=JSON.parse(e.data);if(m.id){const c=pending.get(m.id);pending.delete(m.id);m.error?c.reject(m.error):c.resolve(m.result)}}
const command=(method,params={})=>new Promise((resolve,reject)=>{const n=++id;pending.set(n,{resolve,reject});socket.send(JSON.stringify({id:n,method,params}))})
const evaluate=async expression=>{const r=await command('Runtime.evaluate',{expression,returnByValue:true,awaitPromise:true});if(r.exceptionDetails)throw Error(r.exceptionDetails.exception?.description||r.exceptionDetails.text);return r.result.value}
const sleep=ms=>new Promise(resolve=>setTimeout(resolve,ms))
const click=async title=>evaluate(`(()=>{const button=[...document.querySelectorAll('button')].find(b=>b.innerText.trim()===${JSON.stringify(title)});if(!button)throw Error('Missing button '+${JSON.stringify(title)});button.click();return true})()`)
const add=async(category,name)=>{
 if(await evaluate(`!!document.querySelector('.category-header button')`))await click('‹ 全部分类')
 await evaluate(`(()=>{const button=[...document.querySelectorAll('.category-grid button')].find(b=>b.querySelector('strong').textContent===${JSON.stringify(category)});button.click();return true})()`)
 await sleep(300)
 await evaluate(`(()=>{const article=[...document.querySelectorAll('.part-item')].find(a=>a.querySelector('p').textContent===${JSON.stringify(name)});const button=article.querySelector(':scope > button');if(button.disabled)throw Error('Part still loading');button.click();return true})()`)
 for(let i=0;i<80;i++){await sleep(150);if(await evaluate(`!document.querySelector('.part-item>button:disabled')`))break}
 await sleep(300)
}
try{
 await command('Page.enable');await command('Page.bringToFront');await command('Page.navigate',{url:origin+'/workshop/3d-editor'});await sleep(3500)
 await command('Emulation.setDeviceMetricsOverride',{width:1440,height:1000,deviceScaleFactor:1,mobile:false})
 if(!(await evaluate(`!!document.querySelector('.category-grid')`)))throw Error('Editor unavailable to visitors')
 for(const [cat,name] of [['宠物','铃铛福犬'],['配件','梅花油纸伞'],['头部','微笑小孩'],['身体','童趣短褂'],['底座','雕花木台']])await add(cat,name)
 await click('重置视角').catch(()=>{});await sleep(400)
 let shot=await command('Page.captureScreenshot',{format:'png'});await fs.writeFile('reports/browser/workshop-layout-child.png',Buffer.from(shot.data,'base64'))
 await add('头部','阳光男子');await add('身体','江南长衫')
 shot=await command('Page.captureScreenshot',{format:'png'});await fs.writeFile('reports/browser/workshop-layout-adult.png',Buffer.from(shot.data,'base64'))
 const result=await evaluate(`({canvas:!!document.querySelector('.canvas-container canvas'),errors:[...document.querySelectorAll('.el-message--error')].map(e=>e.textContent)})`)
 if(!result.canvas||result.errors.length)throw Error(JSON.stringify(result))
 await command('Emulation.setDeviceMetricsOverride',{width:390,height:844,deviceScaleFactor:1,mobile:false});await sleep(500)
 const mobile=await evaluate(`({overflow:document.documentElement.scrollWidth-innerWidth,canvasWidth:document.querySelector('.canvas-container canvas').getBoundingClientRect().width})`)
 if(mobile.overflow>2||mobile.canvasWidth<=0)throw Error('Mobile layout '+JSON.stringify(mobile))
 shot=await command('Page.captureScreenshot',{format:'png'});await fs.writeFile('reports/browser/workshop-layout-mobile.png',Buffer.from(shot.data,'base64'))
 console.log(JSON.stringify({guestEditor:true,added:['pet','accessory','head','body','base'],replaced:['head','body'],mobile,...result}))
}finally{socket.close();await fetch(debug+'/json/close/'+target.id)}
