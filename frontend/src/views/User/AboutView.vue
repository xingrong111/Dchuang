<template>
  <div class="about-page container">
    <div class="about-content">
      <h1>关于智绘锡承</h1>
      <div class="about-grid grid grid-2">
        <div class="about-text">
          <p>智绘锡承是一个致力于非遗文化数字化传承与创新的平台...</p>
        </div>
        <div class="about-image">
          <!-- 图片区域 -->
        </div>
      </div>
    </div>
  </div>
</template>

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
