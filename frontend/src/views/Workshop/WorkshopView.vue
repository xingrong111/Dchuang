<template>
  <div class="workshop page-container">
    <div class="page-header">
      <div>
        <h1 class="page-title">共创工坊</h1>
        <p class="page-subtitle">用文字、图片和三维部件创作你的非遗作品</p>
      </div>
    </div>

    <nav class="sub-nav">
      <button :class="{ active: currentTab === 'multi-modal' }" @click="currentTab = 'multi-modal'">
        <el-icon><Brush /></el-icon>
        多模态输入
      </button>
      <button :class="{ active: currentTab === '3d-editor' }" @click="currentTab = '3d-editor'">
        <el-icon><Box /></el-icon>
        3D编辑画布
      </button>
    </nav>

    <div class="content-area">
      <KeepAlive>
        <MultiModalInputView v-if="currentTab === 'multi-modal'" />
        <AIWorkshopView v-else />
      </KeepAlive>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue';
import { Brush, Box } from '@element-plus/icons-vue';
import MultiModalInputView from '@/views/Workshop/MultiModalInputView.vue';
import AIWorkshopView from '@/views/Workshop/AIWorkshopView.vue';

const currentTab = ref('multi-modal');
</script>

<style scoped>
.workshop :deep(.page-container){padding:20px;max-width:none}.workshop :deep(.ai-workshop-view){height:min(860px,calc(100vh - 210px));min-height:660px}@media(max-width:600px){.workshop .sub-nav{padding:10px;gap:8px}.workshop .sub-nav button{padding:12px 16px;font-size:14px}.workshop :deep(.ai-workshop-view){height:auto}}
.workshop {
  max-width: 1400px;
}

.page-header {
  margin-bottom: 30px;
}

.sub-nav {
  display: flex;
  gap: 15px;
  margin-bottom: 25px;
  padding: 15px 20px;
  background: white;
  border-radius: 16px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.06);
  justify-content: center;
}

.sub-nav button {
  padding: 14px 30px;
  border: none;
  background: #f5f5f5;
  border-radius: 12px;
  cursor: pointer;
  font-weight: 600;
  font-size: 1rem;
  color: #666;
  transition: all 0.3s;
  display: flex;
  align-items: center;
  gap: 10px;
}

.sub-nav button:hover {
  background: #e8e8e8;
}

.sub-nav button.active {
  background: linear-gradient(135deg, #4a90a4, #2d6172);
  color: white;
  box-shadow: 0 4px 12px rgba(74, 144, 164, 0.3);
}

.content-area {
  width: 100%;
  min-height: 600px;
  background: white;
  border-radius: 16px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.06);
  padding: 0;
  overflow: hidden;
}
</style>
