import { test } from 'node:test'
import assert from 'node:assert/strict'
import { createCanvas } from '@napi-rs/canvas'
import * as THREE from 'three'
import { attachPart, findConnection } from '../src/three/assembly.js'
globalThis.document = { createElement: () => createCanvas(1, 1) }
const { createPartById, createDaAfu, createCanMao, createShouXing, normalizeModel } = await import('../src/three/modelFactory.js')

test('五部件组装和馆藏阿福使用同一几何布局', () => {
  const root = new THREE.Group(), placed = []
  for (const id of ['clay_base', 'afu_body', 'afu_head', 'afu_arms', 'lion_beast']) {
    const part = createPartById(id)
    const connection = findConnection(part, placed)
    if (placed.length) assert.ok(connection, id)
    if (connection) attachPart(part, connection)
    else root.add(part)
    placed.push(part)
  }
  root.updateMatrixWorld(true)
  const classic = createDaAfu(); classic.updateMatrixWorld(true)
  const centers = object => {
    const points = []
    object.traverse(child => { if (child.isMesh) points.push(child.getWorldPosition(new THREE.Vector3()).toArray().map(v => v.toFixed(6)).join(',')) })
    return points.sort()
  }
  assert.deepEqual(centers(root), centers(classic))
})

test('寿星与蚕猫的底座接触主体，未埋入袍身或悬空', () => {
  for (const create of [createCanMao, createShouXing]) {
    const model = create(), [figure, base] = model.children
    const bodyBounds = new THREE.Box3().setFromObject(figure)
    // 底座装饰描金高于台面，比较圆柱顶面而不是装饰包围盒。
    const surfaceY = base.position.y
    assert.ok(Math.abs(bodyBounds.min.y - surfaceY) < 0.04)
  }
})

test('三个成品归一化后居中且高度一致', () => {
  for (const create of [createDaAfu, createCanMao, createShouXing]) {
    const bounds = new THREE.Box3().setFromObject(normalizeModel(create()))
    assert.ok(Math.abs(bounds.getSize(new THREE.Vector3()).y - 2.6) < 1e-7)
    assert.ok(bounds.getCenter(new THREE.Vector3()).length() < 1e-7)
  }
})

test('阿福抱兽不遮挡嘴部，寿星高额不遮挡五官', () => {
  const afu = createDaAfu(), lion = afu.children[4]
  const lionBounds = new THREE.Box3().setFromObject(lion)
  assert.ok(lionBounds.max.y < 2.2)
  const figure = createShouXing().children[0]
  const head = figure.children.find(child => child.material?.map && child.geometry.type === 'SphereGeometry')
  const headBounds = new THREE.Box3().setFromObject(head)
  assert.ok(headBounds.max.y > 1.8)
  assert.equal(figure.children.filter(child => child.position.y > 1.4 && !child.material?.map).length, 0)
})
