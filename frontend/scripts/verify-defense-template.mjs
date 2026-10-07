import fs from 'node:fs/promises'
import { createCanvas, loadImage } from '@napi-rs/canvas'
const base = 'http://127.0.0.1:19222'
const target = await (await fetch(base + '/json/new?about:blank', { method: 'PUT' })).json()
const ws = new WebSocket(target.webSocketDebuggerUrl)
await new Promise((resolve, reject) => { ws.onopen = resolve; ws.onerror = reject })
let id = 0
const pending = new Map()
ws.onmessage = event => { const body = JSON.parse(event.data); if (body.id) { const entry = pending.get(body.id); pending.delete(body.id); body.error ? entry.reject(body.error) : entry.resolve(body.result) } }
const command = (method, params = {}) => new Promise((resolve, reject) => { const current=++id; const timeout=setTimeout(()=>reject(Error(method)),15000);pending.set(current,{resolve:value=>{clearTimeout(timeout);resolve(value)},reject:error=>{clearTimeout(timeout);reject(error)}});ws.send(JSON.stringify({id:current,method,params})) })
try {
  await command('Page.enable')
  await command('Emulation.setDeviceMetricsOverride',{width:1280,height:760,deviceScaleFactor:1,mobile:false})
  await command('Page.navigate',{url:'http://127.0.0.1:18081/'+encodeURIComponent('答辩模板.html')})
  await new Promise(resolve=>setTimeout(resolve,1200))
  const count = (await command('Runtime.evaluate',{expression:"document.querySelectorAll('.slide').length",returnByValue:true})).result.value
  if(count!==9)throw Error('答辩页数不正确')
  const collage=createCanvas(1440,810),ctx=collage.getContext('2d')
  await fs.mkdir('../operations/deliverables/review',{recursive:true})
  for(let i=0;i<count;i++){
    await command('Runtime.evaluate',{expression:`document.querySelectorAll('.slide')[${i}].scrollIntoView();document.querySelector('nav').style.display='none'`})
    const result=await command('Page.captureScreenshot',{format:'png',captureBeyondViewport:false})
    const buffer=Buffer.from(result.data,'base64')
    await fs.writeFile(`../operations/deliverables/review/slide-${i+1}.png`,buffer)
    ctx.drawImage(await loadImage(buffer),(i%3)*480,Math.floor(i/3)*270,480,270)
  }
  await fs.writeFile('../operations/deliverables/review/contact-sheet.png',collage.toBuffer('image/png'))
  console.log('HTML答辩模板9页渲染完成')
}finally{ws.close();await fetch(base+'/json/close/'+target.id)}
