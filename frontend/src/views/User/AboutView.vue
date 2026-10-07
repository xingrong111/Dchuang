<template>
  <div class="about-page container">
    <div class="about-content">
      <h1>关于智绘锡承</h1>
      <div class="about-grid grid grid-2">
        <div class="about-text">
          <p>{{ content.project.audience }}</p><p>{{ content.project.position }}</p>
          <p>在数字博物馆了解泥人的造型与故事，在共创工坊把头部、袍身、双臂与瑞狮组合成自己的作品，再到社区交流创作心得。</p>
          <p>风格分析帮助观察色彩、纹饰与造型特点。模型作品结果仍需创作者审视和调整，文化解读也需要结合可靠资料。</p>
          <RouterLink to="/model-library">浏览 3D 模型与部件</RouterLink> · <RouterLink to="/shop/designs">查看原创文创提案</RouterLink>
        </div>
        <div class="about-image">
          <ModelPreview :url="`${base}models/daafu.glb`" />
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import ModelPreview from '@/components/ModelPreview.vue'
import content from '@/content/editorial.json'
const base = import.meta.env.BASE_URL
</script>

<style scoped>
.about-page {
  padding: 2rem 0;
}

.about-content h1 {
  text-align: center;
  color: #8B4513;
  margin-bottom: 2rem;
  font-size: 2.5rem;
}

.about-text p {
  font-size: 1.1rem;
  line-height: 1.8;
  color: #333;
}

.about-image {
  background: #f0f0f0;
  border-radius: 12px;
  min-height: 300px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #666;
}

@media (max-width: 768px) {
  .about-grid {
    grid-template-columns: 1fr;
    gap: 1rem;
  }

  .about-content h1 {
    font-size: 2rem;
  }
}
</style>
