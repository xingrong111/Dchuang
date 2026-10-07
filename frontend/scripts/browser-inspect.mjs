import { connectBrowser } from './browser-client.mjs'
const browser = await connectBrowser()
try {
  await browser.navigate(process.argv[2] || 'http://127.0.0.1:15173/')
  await new Promise(resolve => setTimeout(resolve, 1000))
  console.log(JSON.stringify({ url: await browser.evaluate('location.href'), text: await browser.evaluate('document.body.innerText.slice(0,3500)'), errors: browser.errors, network: browser.network }, null, 2))
} finally { browser.close() }
