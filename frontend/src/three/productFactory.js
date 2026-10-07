import * as THREE from 'three'
import { RoundedBoxGeometry } from 'three/examples/jsm/geometries/RoundedBoxGeometry.js'
import { createDaAfu, createCanMao } from './modelFactory.js'

// Dimensions are in metres. These are visual prototypes, not manufacturing meshes.
const palette = { teal: '#376b6c', cream: '#efe4ce', gold: '#c8a56c', paper: '#fbf6eb', kraft: '#b38c63' }
const material = (color, roughness = 0.6, metalness = 0) => new THREE.MeshStandardMaterial({ color, roughness, metalness })
const box = (group, size, position, color, radius = 0.001, roughness = 0.6, metalness = 0) => {
  const mesh = new THREE.Mesh(new RoundedBoxGeometry(...size, 3, radius), material(color, roughness, metalness))
  mesh.position.set(...position); group.add(mesh); return mesh
}
const figure = (group, create, height, position) => {
  const figure = create()
  figure.updateMatrixWorld(true)
  const bounds = new THREE.Box3().setFromObject(figure), size = bounds.getSize(new THREE.Vector3())
  const scale = height / size.y
  const holder = new THREE.Group()
  figure.position.set(-(bounds.min.x + bounds.max.x) / 2, -bounds.min.y, -(bounds.min.z + bounds.max.z) / 2)
  holder.add(figure); holder.scale.setScalar(scale); holder.position.set(...position); group.add(holder)
  return holder
}
const disc = (group, radius, height, pos, color) => {
  const mesh = new THREE.Mesh(new THREE.CylinderGeometry(radius, radius, height, 48), material(color))
  mesh.position.set(...pos); group.add(mesh); return mesh
}
const printed = (kind = 'afu') => {
  const canvas = document.createElement('canvas'); canvas.width = 512; canvas.height = 640
  const c = canvas.getContext('2d'); c.fillStyle = kind === 'afu' ? palette.teal : palette.cream; c.fillRect(0, 0, 512, 640)
  c.strokeStyle = palette.gold; c.lineWidth = 3; c.strokeRect(30, 30, 452, 580)
  c.save(); c.translate(256, 300)
  if (kind === 'afu') {
    c.fillStyle = '#c96543'; c.beginPath(); c.ellipse(0, 85, 110, 100, 0, 0, Math.PI * 2); c.fill()
    c.fillStyle = '#efcfaa'; c.beginPath(); c.arc(0, -45, 79, 0, Math.PI * 2); c.fill()
    c.fillStyle = '#263e37'; for (const x of [-62, 62]) { c.beginPath(); c.arc(x, -108, 26, 0, Math.PI * 2); c.fill() }
    c.strokeStyle = '#263e37'; c.lineWidth = 7
    for (const x of [-30, 30]) { c.beginPath(); c.arc(x, -40, 14, Math.PI, 0); c.stroke() }
    c.beginPath(); c.arc(0, -8, 22, 0.1, Math.PI - 0.1); c.stroke()
    c.strokeStyle = palette.gold; c.beginPath(); c.arc(0, 80, 55, 0.2, Math.PI - 0.2); c.stroke()
  } else {
    c.fillStyle = '#d6a343'; c.beginPath(); c.moveTo(-100,100); c.lineTo(-100,-60); c.lineTo(-70,-115); c.lineTo(-30,-65); c.lineTo(30,-65); c.lineTo(70,-115); c.lineTo(100,-60); c.lineTo(100,100); c.closePath(); c.fill()
    c.strokeStyle = palette.teal; c.lineWidth = 7; c.beginPath(); c.moveTo(-55,-15); c.lineTo(-20,-5); c.moveTo(55,-15); c.lineTo(20,-5); c.moveTo(-20,30); c.lineTo(0,45); c.lineTo(20,30); c.stroke()
  }
  c.restore()
  // Seeded paper grain, not externally sourced artwork.
  let seed = 42
  for (let i = 0; i < 4500; i++) { seed = (seed * 1664525 + 1013904223) >>> 0; const x = seed % 512; seed = (seed * 1664525 + 1013904223) >>> 0; c.fillStyle = 'rgba(255,255,255,.045)'; c.fillRect(x, seed % 640, 1, 1) }
  const texture = new THREE.CanvasTexture(canvas); texture.colorSpace = THREE.SRGBColorSpace
  return new THREE.MeshStandardMaterial({ map: texture, roughness: 0.87 })
}
const cover = (group, width, height, depth, pos, kind = 'afu') => {
  const mesh = box(group, [width, height, depth], pos, kind === 'afu' ? palette.teal : palette.cream)
  mesh.material = [material(palette.teal), material(palette.teal), material(palette.cream), material(palette.cream), printed(kind), material(palette.teal)]
  return mesh
}
export const PRODUCT_IDS = ['afu-desk', 'cat-book', 'notebook', 'postcards', 'kit']
export function createProduct(id) {
  if (!PRODUCT_IDS.includes(id)) throw new Error(`Unknown product: ${id}`)
  const group = new THREE.Group(); group.name = id; group.userData = { source: 'procedural', units: 'metres', prototype: true, assetId: id }
  if (id === 'afu-desk') {
    disc(group, 0.042, 0.008, [0, 0.004, 0], palette.cream)
    figure(group, createDaAfu, 0.10, [0, 0.008, 0])
  } else if (id === 'cat-book') {
    for (const side of [-1, 1]) {
      box(group, [0.09, 0.004, 0.105], [side * 0.103, 0.002, 0], palette.teal, 0.001, 0.4, 0.6)
      box(group, [0.004, 0.14, 0.105], [side * 0.06, 0.074, 0], palette.teal, 0.001, 0.4, 0.6)
      figure(group, createCanMao, 0.10, [side * 0.106, 0.004, 0.005])
    }
    // Show actual-use proportions with three plain books between the bookends.
    for (let i = 0; i < 3; i++) {
      const x = (i - 1) * 0.035
      box(group, [0.03, 0.155 + i * 0.008, 0.09], [x, (0.155 + i * 0.008) / 2, 0], [palette.kraft, palette.cream, palette.teal][i])
      box(group, [0.027, 0.149 + i * 0.008, 0.086], [x, (0.155 + i * 0.008) / 2, 0.003], palette.paper, 0.0005)
    }
  } else if (id === 'notebook') {
    box(group, [0.142, 0.204, 0.018], [0, 0.105, 0], palette.paper)
    cover(group, 0.148, 0.21, 0.0025, [0, 0.105, 0.011])
    box(group, [0.148, 0.21, 0.0025], [0, 0.105, -0.011], palette.teal)
    box(group, [0.008, 0.21, 0.025], [-0.074, 0.105, 0], palette.teal)
    box(group, [0.004, 0.03, 0.0007], [0.045, -0.004, 0.003], '#ba664d')
  } else if (id === 'postcards') {
    for (let i = 0; i < 4; i++) {
      const card = cover(group, 0.10, 0.15, 0.0012, [(i - 1.5) * 0.026, 0.081 + i * 0.004, i * 0.002], i % 2 ? 'cat' : 'afu')
      card.rotation.z = (i - 1.5) * -0.1
    }
  } else {
    box(group, [0.24, 0.012, 0.18], [0, 0.006, 0], palette.kraft)
    for (const z of [-0.087, 0.087]) box(group, [0.24, 0.044, 0.004], [0, 0.028, z], palette.kraft)
    for (const x of [-0.117, 0.117]) box(group, [0.004, 0.044, 0.18], [x, 0.028, 0], palette.kraft)
    const blank = figure(group, createDaAfu, 0.082, [-0.047, 0.012, 0])
    blank.traverse(child => { if (child.isMesh) child.material = material(palette.cream, 0.86) })
    for (let i = 0; i < 6; i++) {
      const x = 0.035 + (i % 2) * 0.027, z = -0.05 + Math.floor(i / 2) * 0.03
      disc(group, 0.01, 0.017, [x, 0.02, z], '#efede7')
      disc(group, 0.011, 0.003, [x, 0.031, z], ['#bc4835', '#376b6c', '#d6a343', '#e8d8bf', '#243e37', '#d98068'][i])
    }
    for (let i = 0; i < 2; i++) {
      const brush = new THREE.Group(); group.add(brush)
      const handle = new THREE.Mesh(new THREE.CylinderGeometry(0.0018, 0.0018, 0.12, 12), material('#926943')); handle.rotation.z = Math.PI / 2; handle.position.set(0, 0.017, 0.063 + i * 0.007); brush.add(handle)
      box(brush, [0.012, 0.003, 0.003], [0.065, 0.017, 0.063 + i * 0.007], '#dbc3a0')
    }
    cover(group, 0.09, 0.065, 0.001, [-0.045, 0.045, -0.056])
  }
  group.traverse(child => { if (child.isMesh) { child.castShadow = true; child.receiveShadow = true } })
  group.updateMatrixWorld(true)
  return group
}
