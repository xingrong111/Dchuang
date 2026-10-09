<template>
  <div class="concept-page page-container"><figure class="collection-hero"><img :src="asset('collection-studio.webp')" alt="五款文创系列的产品图片，暂无实物销售" /><figcaption>产品图片 · 生活文创系列</figcaption></figure><header class="intro"><span class="eyebrow">WUXI COLLECTION · 无锡文创</span><h1>把祝福，放进日常</h1><p>从阿福的轮廓、蚕猫的神态与彩塑的配色中寻找灵感。系列原创文创，让文化阅读延伸到生活设计。</p><div class="notice">文创产品可加入购物车。当前暂未开售，不能购买、结算或定制。</div></header>
    <div class="filters"><label class="search">搜索设计<el-input v-model="keyword" placeholder="名称、灵感或材料" clearable /></label><div class="category-buttons"><button v-for="cat in categories" :key="cat" :class="{active:category===cat}" @click="category=cat">{{ cat }}</button></div></div><p class="result-count">{{ filtered.length }} 款文创产品</p>
    <div class="product-grid"><article v-for="product in filtered" :key="product.id" class="product"><button class="image-button" :aria-label="`查看${product.name}设计`" @click="selected=product"><img :src="asset(product.image)" :alt="product.name+'产品图片，非实物照片'" loading="lazy" /></button><div class="product-body"><span class="eyebrow">{{ product.category }} · 无锡文创</span><h2>{{ product.name }}</h2><p>{{ product.intro }}</p><button class="detail-button" @click="selected=product">阅读作品说明 ↗</button><el-button :loading="cartBusy" @click="addDesignToCart(product)">加入购物车</el-button></div></article></div><div v-if="!filtered.length" class="empty"><p>没有匹配的设计，试试“阿福”或“纸品”。</p><button @click="keyword='';category='全部'">清除筛选</button></div>
    <section class="process"><h2>无锡文化，融入日常</h2><p>以泥塑、锡绣与江南风物为灵感，探索摆件、文具与生活用品中的无锡文化。</p><RouterLink to="/museum">了解文化灵感</RouterLink><RouterLink to="/workshop">进入数字共创工坊</RouterLink></section>
    <el-dialog :model-value="!!selected" :title="selected?.name" width="820px" @update:model-value="value=>{if(!value)selected=null}"><div v-if="selected" class="detail"><div class="visual-panel"><div class="view-buttons"><button :class="{active:visualMode==='image'}" @click="visualMode='image'">产品图片</button><button :class="{active:visualMode==='model'}" @click="visualMode='model'">旋转3D模型</button></div><img v-if="visualMode==='image'" :src="asset(selected.image)" :alt="selected.name+'产品图片'" /><ModelPreview v-else :key="selected.id" :url="`${base}${selected.model}`" /><p class="visual-caption">{{ visualMode==='image' ? '查看产品造型、材质与使用场景。' : (selected.modelSource ? selected.modelSource+'，可旋转观察作品细节。' : '可旋转观察作品细节。') }}</p><a :href="`${base}${selected.model}`" :download="selected.id+'.glb'">下载 GLB 展示模型</a> · <RouterLink :to="{path:'/workshop/3d-editor',query:{modelAsset:selected.id}}">在工坊使用</RouterLink></div><div><p class="eyebrow">原创文创 · 暂未开售</p><p>{{ selected.story }}</p><dl><dt>材料方向</dt><dd>{{ selected.material }}</dd><dt>参考规格</dt><dd>{{ selected.size }}</dd></dl><ul><li v-for="feature in selected.features" :key="feature">{{ feature }}</li></ul><p class="notice">暂未开售，可加入购物车保留选品，当前不能购买。</p><el-button type="primary" :loading="cartBusy" @click="addDesignToCart(selected)">加入购物车</el-button><el-button @click="ElMessage.info('暂未开售，当前不能购买')">立即购买</el-button><RouterLink to="/shop">查看购物车</RouterLink> · <RouterLink to="/museum">查看相关文化资料</RouterLink></div></div></el-dialog>
  </div>
</template>
<script setup>
import { computed, ref, watch, defineAsyncComponent } from 'vue'
const ModelPreview=defineAsyncComponent(()=>import('@/components/ModelPreview.vue'))
const base=import.meta.env.BASE_URL
const visualMode=ref('image')
import content from '@/content/editorial.json'
import { useRoute } from 'vue-router'
import { useCartStore } from '@/store/cartStore'
import { useUserStore } from '@/store/userStore'
import { getProducts } from '@/api/shop'
import { ElMessage } from 'element-plus'
const cartStore=useCartStore(),userStore=useUserStore(),cartBusy=ref(false)
const addDesignToCart=async product=>{
 if(!userStore.user?.token)return ElMessage.warning('请先登录后加入购物车')
 if(cartBusy.value)return
 cartBusy.value=true
 try{
  const response=await getProducts({page:1,per_page:100})
  const entry=response.data.find(item=>item.specs?.design_id===product.id)
  if(!entry)return ElMessage.warning('该产品暂未加入商城目录')
  if(await cartStore.addToCart(entry))ElMessage.success('已加入购物车，该产品暂未开售，不能购买')
 }catch{ /* 请求错误由统一提示处理 */ }finally{cartBusy.value=false}
}
const keyword=ref(''),category=ref('全部'),selected=ref(null)
watch(selected,()=>{visualMode.value='image'})
const route=useRoute()
watch(()=>route.query.design,id=>{selected.value=content.products.find(p=>p.id===id)||null},{immediate:true})
const categories=['全部',...new Set(content.products.map(p=>p.category))]
const asset=name=>`${import.meta.env.BASE_URL}content/${name}`
const filtered=computed(()=>content.products.filter(p=>(category.value==='全部'||p.category===category.value)&&[p.name,p.intro,p.story,p.category,p.material].join(' ').toLowerCase().includes(keyword.value.trim().toLowerCase())))
</script>
<style scoped>
.collection-hero{margin:0 0 20px;position:relative}.collection-hero img{width:100%;height:420px;object-fit:cover;border-radius:18px}.collection-hero figcaption{position:absolute;bottom:16px;left:16px;background:#fff8e7df;border-radius:8px;padding:8px 12px;font-size:13px;color:#64543f}.view-buttons{display:flex;gap:8px;margin-bottom:12px}.view-buttons button{padding:8px 12px;border:1px solid #ddd3bd;border-radius:8px;background:white;color:#365e58}.view-buttons .active{background:#365e58;color:white}.visual-caption{font-size:12px;color:#776e5f;line-height:1.7}.image-button img{aspect-ratio:3/2;object-fit:cover}@media(max-width:600px){.collection-hero img{height:230px}}

.concept-page{max-width:1240px}.intro{padding:24px 0 32px;max-width:850px}.eyebrow{color:#a55a3c;font-size:12px;letter-spacing:1px}.intro h1{font-size:42px;color:#2d6172;margin:12px 0}.intro p,.process p{font-size:17px;line-height:1.9;color:#5d6b67}.notice{background:#edf1e9;padding:14px 18px;border-left:3px solid #6c896d;color:#526751;font-size:14px;line-height:1.8}.filters{display:flex;gap:24px;justify-content:space-between;align-items:end;flex-wrap:wrap}.search{display:grid;gap:8px;width:300px;max-width:100%;font-size:13px}.category-buttons{display:flex;gap:8px;flex-wrap:wrap}button{cursor:pointer;font:inherit}.category-buttons button,.empty button{border:1px solid #d9ddd6;background:white;border-radius:30px;padding:10px 18px;color:#536b60}.category-buttons .active{background:#2d6172;color:white;border-color:#2d6172}.result-count{font-size:13px;color:#738078;margin:24px 0}.product-grid{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:24px}.product{border:1px solid #e7e1d5;background:white;border-radius:14px;overflow:hidden}.image-button{padding:0;border:0;width:100%;display:block;background:#f2ebde}.image-button img{width:100%;display:block}.product-body{padding:22px}.product h2{font-size:21px;color:#365e58;margin:10px 0}.product p{color:#67726a;line-height:1.8;min-height:56px}.detail-button{border:0;background:none;color:#a55a3c;padding:8px 0}.process{margin:48px 0 10px;padding-top:24px;border-top:1px solid #ddd3bd}.process h2{color:#365e58}.process a{display:inline-block;color:#2d6172;margin-right:24px;text-decoration:underline}.detail{display:grid;grid-template-columns:1fr 1fr;gap:24px;line-height:1.9}.detail img{width:100%;border-radius:12px}.detail dt{font-weight:bold;color:#365e58}.detail dd{margin:0 0 10px}.detail a{color:#2d6172}.empty{padding:40px;text-align:center}@media(max-width:900px){.product-grid{grid-template-columns:repeat(2,minmax(0,1fr))}}@media(max-width:600px){.product-grid,.detail{grid-template-columns:1fr}.intro h1{font-size:31px}.intro p{font-size:15px}.product p{min-height:0}.category-buttons button{padding:8px 12px}}
</style>
