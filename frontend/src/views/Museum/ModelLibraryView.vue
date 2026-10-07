<template>
  <main class="library page-container">
    <h1>惠山泥人 · 3D 资产库</h1>
    <p class="intro">探索完整的非遗主题文创模型。点击设计进入三维预览，拖动查看各个角度；工程组装原型收纳在下方。</p>
    <p><RouterLink to="/workshop">进入共创工坊</RouterLink></p>
    <section><h2>混元文创模型</h2><p class="note">生活文创与主题摆件由腾讯混元 3D V3.1 制作。点击设计进入效果图与3D对照，GLB不代表可直接制造的模型。</p><div class="asset-grid"><article v-for="item in editorial.products" :key="item.id"><RouterLink :to="{path:'/shop/designs',query:{design:item.id}}"><img class="product-photo" :src="`${base}content/${item.image}`" :alt="item.name+'设计效果图'" loading="lazy" /></RouterLink><div class="caption"><h3>{{ item.name }}</h3><a :href="`${base}${item.model}`" :download="item.id+'.glb'">下载 GLB</a></div></article></div></section>
    <details @toggle="legacyExpanded=$event.target.open"><summary>工程组装原型与部件（用于编辑器练习）</summary>
    <template v-if="legacyExpanded"><section v-for="section in sections" :key="section.title">
      <h2>{{ section.title }}</h2>
      <div class="asset-grid">
        <article v-for="item in section.items" :key="item.id">
          <ModelPreview :url="`${base}models/${item.path}.glb`" />
          <div class="caption"><h3>{{ item.name }}</h3><a :href="`${base}models/${item.path}.glb`" download>下载 GLB</a></div>
        </article>
      </div>
    </section>
    </template></details>
    <p class="note">文创模型来自腾讯混元网站；下方工程组装资产由项目程序化工厂制作。工坊微笑小孩与阳光男子头部来自腾讯混元，已调整颈口与组装比例。模型均为展示资产，未进行实物制造验证。</p>
  </main>
</template>
<script setup>
import { ref } from 'vue'
const legacyExpanded=ref(false)
import ModelPreview from '@/components/ModelPreview.vue'
import editorial from '@/content/editorial.json'
const base = import.meta.env.BASE_URL
const sections = [
  { title: '经典成品', items: [{ id: 'daafu', path: 'daafu', name: '大阿福' }, { id: 'canmao', path: 'canmao', name: '蚕猫' }, { id: 'shouxing', path: 'shouxing', name: '老寿星' }] },
  { title: '组装部件', items: [{ id: 'afu_head', name: '阿福头部' }, { id: 'afu_body', name: '阿福身体' }, { id: 'afu_arms', name: '环抱双臂' }, { id: 'clay_base', name: '描金底座' }, { id: 'lion_beast', name: '瑞狮' }].map(item => ({ ...item, path: `parts/${item.id}` })) },
]
</script>
<style scoped>
details{margin:32px 0}summary{cursor:pointer;padding:16px;background:#eee8dd;border-radius:12px}.library { max-width: 1250px; padding-bottom: 40px; color: #40382f; }
.product-photo{width:100%;aspect-ratio:3/2;object-fit:contain;display:block}
h1 { font-size: 30px; } h2 { margin-top: 32px; font-size: 22px; }
.intro, .note { line-height: 1.8; color: #766b5e; }
.asset-grid { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 20px; }
article { border: 1px solid #ded5c8; background: #faf7f0; border-radius: 14px; overflow: hidden; }
.caption { display: flex; justify-content: space-between; align-items: center; padding: 0 16px; }
h3 { font-size: 17px; } a { color: #2d6172; }
@media (max-width: 850px) { .asset-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); } }
@media (max-width: 550px) { .asset-grid { grid-template-columns: 1fr; } }
</style>

