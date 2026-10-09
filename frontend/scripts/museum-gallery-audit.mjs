import fs from 'node:fs/promises'
const origin=(process.env.AUDIT_ORIGIN || 'http://127.0.0.1:15176'),debug=(process.env.EDGE_DEBUG_URL || 'http://127.0.0.1:19223')
const target=await(await fetch(debug+'/json/new?about:blank',{method:'PUT'})).json(),socket=new WebSocket(target.webSocketDebuggerUrl)
await new Promise(resolve=>socket.onopen=resolve)
let id=0;const pending=new Map(),errors=[],checks=[]
socket.onmessage=event=>{const m=JSON.parse(event.data);if(m.id){const c=pending.get(m.id);pending.delete(m.id);m.error?c.reject(m.error):c.resolve(m.result)}else if(m.method==='Runtime.exceptionThrown')errors.push(m.params.exceptionDetails.exception?.description || m.params.exceptionDetails.text)}
const command=(method,params={})=>new Promise((resolve,reject)=>{const n=++id;pending.set(n,{resolve,reject});socket.send(JSON.stringify({id:n,method,params}))})
const evaluate=async expression=>{const r=await command('Runtime.evaluate',{expression,awaitPromise:true,returnByValue:true});if(r.exceptionDetails)throw Error(r.exceptionDetails.exception?.description||r.exceptionDetails.text);return r.result.value}
const sleep=ms=>new Promise(resolve=>setTimeout(resolve,ms))
const check=(name,passed)=>{checks.push({name,passed:!!passed});if(!passed)throw Error(name)}

try{
 await command('Page.enable');await command('Runtime.enable');await command('Page.navigate',{url:origin+'/museum'});await sleep(3000);
 for(const width of [1366,390]){
  await command('Emulation.setDeviceMetricsOverride',{width,height:900,deviceScaleFactor:1,mobile:false});await sleep(300);
  check(width+' 文化介绍九段',await evaluate('document.querySelectorAll(".chapter-body p").length===9'));
  check(width+' 六张工艺图',await evaluate('document.querySelectorAll(".craft-open").length===6'));
  await evaluate('document.querySelector(".craft-open").click();true');await sleep(500);
  check(width+' 图片查看器打开',await evaluate('!!document.querySelector(".el-image-viewer__wrapper")'));
  await evaluate('document.querySelector(".el-image-viewer__next").click();true');await sleep(300);
  check(width+' 下一张工艺图片',await evaluate('document.querySelector(".el-image-viewer__img").src.includes("material-12")'));
  await evaluate('document.querySelector(".el-image-viewer__close").click();true');await sleep(200);
  check(width+' 图片查看器关闭',await evaluate('!document.querySelector(".el-image-viewer__wrapper")'));
  check(width+' 无横向溢出',await evaluate('document.documentElement.scrollWidth-innerWidth<=2'));
  const shot=await command('Page.captureScreenshot',{format:'png',captureBeyondViewport:true});await fs.writeFile('reports/browser/museum-reading-'+width+'.png',Buffer.from(shot.data,'base64'));
 }
 check('浏览器无异常',errors.length===0);
}finally{await fs.writeFile('reports/browser/museum-gallery-audit.json',JSON.stringify({checks,errors},null,2));console.log(JSON.stringify({checks:checks.length,failed:checks.filter(c=>!c.passed),errors}));socket.close();await fetch(debug+'/json/close/'+target.id)}
