<template>
  <div class="ai-workshop-view">
    <div class="editor-heading">
      <p>头部与身体自动按人物比例适配，保留自然颈部衔接。身体已含双臂，可再搭配底座、配件与宠物。</p>
      <RouterLink to="/model-library">查看成品与部件</RouterLink>
    </div>
    <AIWorkshopCanvas />
  </div>
</template>
<script setup>
import AIWorkshopCanvas from '@/components/AIWorkshopCanvas.vue'
</script>
<style scoped>
.ai-workshop-view { height: 740px; display: flex; flex-direction: column; }
.editor-heading { display: flex; align-items: center; justify-content: space-between; gap: 16px; padding: 12px 20px; color: #655b4e; background: #faf6ed; }
.editor-heading p { margin: 0; }
.editor-heading a { white-space: nowrap; color: #2d6172; }
.ai-workshop-view :deep(.ai-workshop) { flex: 1; min-height: 0; }
@media (max-width: 768px) {
  .ai-workshop-view { height: auto; }
  .ai-workshop-view :deep(.ai-workshop) { flex: none; min-height: 900px; }
  .editor-heading { flex-direction: column; align-items: flex-start; }
}
</style>
