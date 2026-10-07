import * as THREE from 'three'
import { GLTFLoader } from 'three/examples/jsm/loaders/GLTFLoader.js'
import { clipPart } from './clipPart.js'
import { neckSocket, shoulderWidth } from './partSockets.js'
const sources=new Map()
const source=async(id,folder='products')=>{
 const key=folder+'/'+id
 if(!sources.has(key))sources.set(key,new GLTFLoader().loadAsync(import.meta.env.BASE_URL+'models/'+key+'.glb').then(g=>{g.scene.updateMatrixWorld(true);return g.scene}).catch(error=>{sources.delete(key);throw error}))
 return sources.get(key)
}
const copyMaterial=m=>{const c=m.clone();for(const [key,value] of Object.entries(c))if(value?.isTexture)c[key]=value.clone();return c}
const category=(id,name,type,entries)=>({id,name,parts:entries.map(([partId,title,asset])=>({id:partId,name:title,asset,type,category:id}))})
export const WORKSHOP_CATEGORIES=[
 category('head','头部','afu_head',[['head-red','微笑小孩','head-child-smile'],['head-jade','寿星长眉','head-sage'],['head-gold','点翠旦角','head-opera'],['head-peach','阳光男子','head-man-sunny']]),
 category('body','身体','afu_body',[['body-red','盘坐花袍','body-robe'],['body-jade','戏曲长裙','body-opera'],['body-gold','江南长衫','body-scholar'],['body-ivory','童趣短褂','body-jacket']]),
 category('arms','手臂','afu_arms',[['arms-hug','拱手宽袖','arms-hug'],['arms-open','迎宾展开袖','arms-open'],['arms-left','举福窄袖','arms-lift'],['arms-right','护腕铠甲臂','arms-armor']]),
 category('base','底座','clay_base',[['base-clay','莲瓣台座','base-lotus'],['base-jade','祥云台座','base-cloud'],['base-gold','太湖石台座','base-rock'],['base-wood','雕花木台','base-wood']]),
 category('accessory','配件','accessory',[['accessory-book','锦纹小书','notebook'],['accessory-card','祝福卡片','postcards'],['accessory-brush','梅花油纸伞','accessory-umbrella'],['accessory-flower','青玉如意','accessory-ruyi']]),
 category('pet','宠物','lion_beast',[['pet-left','蚕猫书挡','cat-book'],['pet-right','铃铛福犬','pet-dog'],['pet-jade','桂花玉兔','pet-rabbit'],['pet-lion','绣球瑞狮','pet-lion']])
]
export const WORKSHOP_PARTS=WORKSHOP_CATEGORIES.flatMap(c=>c.parts)
const heights={head:1.1,body:1.35,arms:.66,base:.28,accessory:.65,pet:.58}
const maxWidths={head:1.4,body:1.8,arms:1.6,base:2.3,accessory:.8,pet:.85}
const disposeObject=object=>object.traverse(mesh=>{mesh.geometry?.dispose();for(const m of [mesh.material].flat().filter(Boolean)){for(const value of Object.values(m))if(value?.isTexture)value.dispose();m.dispose()}})
export async function createWorkshopPart(id){
 const part=WORKSHOP_PARTS.find(p=>p.id===id);if(!part)return null
 let object
 {
  const product=['notebook','postcards','cat-book'].includes(part.asset)
  object=(await source(part.asset,product?'products':'workshop')).clone(true)
  object.traverse(mesh=>{if(mesh.isMesh){mesh.geometry=mesh.geometry.clone();mesh.material=Array.isArray(mesh.material)?mesh.material.map(copyMaterial):copyMaterial(mesh.material);mesh.castShadow=mesh.receiveShadow=true}})
 }
 if(['body-robe','body-opera','body-jacket'].includes(part.asset)){
  const b=new THREE.Box3().setFromObject(object),fractions={'body-robe':.72,'body-opera':.86,'body-jacket':.69},cut=b.min.y+(b.max.y-b.min.y)*fractions[part.asset]
  const clipped=clipPart(object,'y',cut,true,'#e4c7a6');disposeObject(object);object=clipped
 }
 if(['arms-open','arms-lift'].includes(part.asset)){
  const b=new THREE.Box3().setFromObject(object),center=(b.min.x+b.max.x)/2,gap=(b.max.x-b.min.x)*.18
  const pair=new THREE.Group();pair.add(clipPart(object,'x',center-gap,true,'#caad86',true),clipPart(object,'x',center+gap,false,'#caad86',true));disposeObject(object);object=pair
 }
 if(part.asset==='cat-book'){
  const b=new THREE.Box3().setFromObject(object),low=clipPart(object,'y',b.min.y+(b.max.y-b.min.y)*.47,true,'#e6d9b8')
  const cat=clipPart(low,'x',(b.min.x+b.max.x)/2-(b.max.x-b.min.x)*.15,true,'#e6d9b8',true);disposeObject(low);disposeObject(object);object=cat
 }
 // The generated head assets include busts. Remove the shoulders before docking.
 const headCuts={'head-sage':.35,'head-opera':.18,'head-child-smile':.32,'head-man-sunny':.34}
 if(headCuts[part.asset]){
  const b=new THREE.Box3().setFromObject(object),cut=b.min.y+(b.max.y-b.min.y)*headCuts[part.asset]
  const clipped=clipPart(object,'y',cut,false,'#e4c7a6');disposeObject(object);object=clipped
 }
 if(part.asset==='head-opera')object.rotation.y+=Math.PI/2
 if(['pet-dog','pet-rabbit'].includes(part.asset))object.rotation.y+=Math.PI/2

 const bounds=new THREE.Box3().setFromObject(object),size=bounds.getSize(new THREE.Vector3())
 if(!Number.isFinite(size.y)||size.y<=0)throw Error('部件没有可用几何体')
 const desiredHeight=part.asset==='accessory-umbrella'?1.25:heights[part.category]
 const center=bounds.getCenter(new THREE.Vector3()),scale=Math.min(desiredHeight/size.y,maxWidths[part.category]/size.x)
 const normalized=new THREE.Group();object.position.sub(new THREE.Vector3(center.x,bounds.min.y,center.z));normalized.add(object)
 const baseScale=part.category==='base'?Math.min(1.8/size.x,1.8/size.z):scale
 const verticalScale=part.category==='base'?Math.min(baseScale,.65/size.y):scale
 normalized.scale.set(baseScale,verticalScale,baseScale)
 const root=new THREE.Group();root.name=part.name;root.add(normalized)
 const height=size.y*verticalScale,depth=size.z*baseScale,width=size.x*baseScale
 root.userData={partId:part.type,catalogId:part.id,category:part.category,source:'Tencent Hunyuan 3D V3.1',asset:part.asset,dimensions:{height,depth,width},attachPoints:[]}

 if(part.category==='accessory'){
  // Presentation mounts give loose props an actual support surface.
  normalized.position.y=.035
  const wood=new THREE.MeshStandardMaterial({color:'#71503a',roughness:.85})
  const pad=new THREE.Mesh(new THREE.BoxGeometry(width*1.06,.035,Math.max(depth*1.08,.18)),wood)
  pad.position.y=.0175;pad.name='accessory-display-mount';root.add(pad)
  if(part.asset==='accessory-umbrella'){
   const holder=new THREE.Mesh(new THREE.CylinderGeometry(width*.04,width*.055,height*.28,20),wood.clone())
   holder.position.set(-width*.1,height*.14+.035,0);root.add(holder)
  }
  if(part.asset==='postcards'){
   const backing=new THREE.Mesh(new THREE.BoxGeometry(width*1.03,height*1.03,.025),wood.clone())
   backing.position.set(0,height*.5+.035,-depth*.55-.015);root.add(backing)
  }
  const mountedSize=new THREE.Box3().setFromObject(root).getSize(new THREE.Vector3())
  root.userData.dimensions={width:mountedSize.x,height:mountedSize.y,depth:mountedSize.z}
 }

 const anchor=(name,position)=>root.userData.attachPoints.push({name,position,accept:['any'],used:false})
 if(part.category==='base'){anchor('top',[0,height,0]);anchor('companion',[width*.5,0,0]);anchor('accessory',[-width*.5,0,0])}
 else if(part.category==='body'){
  const shoulders=shoulderWidth(root,height,width),collar=neckSocket(root,'top',.008),neckHeight=height*.02
  root.userData.dimensions.shoulderWidth=shoulders
  root.userData.dimensions.headHeight=height*({'body-robe':.29,'body-opera':.19,'body-scholar':.2,'body-jacket':.23}[part.asset]||.2)
  root.userData.integratedArms=true
  const neck=new THREE.Mesh(new THREE.CylinderGeometry(1,1.08,neckHeight+height*.014,24),new THREE.MeshStandardMaterial({color:'#e4c7a6',roughness:.85}))
  neck.name='neck-joint';neck.visible=false;neck.position.set(collar[0],collar[1]+neckHeight*.5,collar[2]);neck.scale.set(shoulders*.075,1,shoulders*.075);root.add(neck)
  anchor('bottom',[0,0,0]);anchor('top',[collar[0],collar[1]+neckHeight,collar[2]]);anchor('front',[0,height*.65,depth*.22]);anchor('accessory',[-width*.5,0,0]);anchor('companion',[width*.5,0,0])
 }
 else if(part.category==='head'){
  const anatomy={'head-child-smile':[.92,.9],'head-sage':[.72,.88],'head-opera':[.68,.78],'head-man-sunny':[.92,.91]}[part.asset]
  root.userData.dimensions.anatomicalHeight=height*anatomy[0]
  root.userData.dimensions.anatomicalWidth=width*anatomy[1]
  root.userData.skinTone={'head-child-smile':'#e4c7a6','head-sage':'#d8af8c','head-opera':'#ead1bc','head-man-sunny':'#e4b899'}[part.asset]
  anchor('bottom',neckSocket(root,'bottom'))
 }
 else if(part.category==='arms'){anchor('center',[0,height*.5,0]);anchor('front',[0,height*.42,depth*.48])}
 else anchor('bottom',[0,0,0])
 return root
}


