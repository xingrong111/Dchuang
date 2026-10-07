// Encode the selected generated originals for delivery; no compositing or retouching.
import { createCanvas, loadImage } from '@napi-rs/canvas'
import fs from 'node:fs/promises'
import path from 'node:path'
const names = ['collection-studio', 'afu-desk-studio', 'cat-book-studio', 'notebook-studio', 'postcards-studio', 'kit-studio']
const source = path.resolve('../operations/deliverables/product-visuals')
const target = path.resolve('public/content')
await fs.mkdir(source, { recursive: true })
for (const name of names) {
  const original = path.join(source, `${name}.png`)
  try { await fs.access(original) } catch { await fs.copyFile(path.join(target, `${name}.png`), original) }
  const image = await loadImage(original)
  const canvas = createCanvas(image.width, image.height)
  canvas.getContext('2d').drawImage(image, 0, 0)
  const buffer = await canvas.encode('webp', 90)
  await fs.writeFile(path.join(target, `${name}.webp`), buffer)
  console.log(`${name}: ${Math.round(buffer.length / 1024)} KB (${image.width}x${image.height})`)
}
