<template>
  <div class="ai-workshop-view">
    <div class="parts-panel">
      <div class="panel-header">
        <h3><el-icon><CirclePlus /></el-icon> 零件选择</h3>
        <p>拖拽零件到右侧画布进行组装</p>
      </div>
      <div class="parts-grid">
        <div
          v-for="part in parts"
          :key="part.id"
          class="part-item"
          draggable="true"
          @dragstart="onDragStart(part, $event)"
        >
          <div class="part-icon">{{ part.icon }}</div>
          <p>{{ part.name }}</p>
        </div>
      </div>
    </div>

    <div class="canvas-container">
      <div class="canvas-header">
        <h3><el-icon><Box /></el-icon> 3D编辑画布</h3>
        <div class="canvas-actions">
          <el-button size="small" @click="resetCanvas">
            <el-icon><Refresh /></el-icon>
            重置
          </el-button>
          <el-button size="small" type="primary" @click="exportModel">
            <el-icon><Download /></el-icon>
            导出模型
          </el-button>
        </div>
      </div>
      <div class="canvas-wrapper">
        <AIWorkshopCanvas />
      </div>
      <div class="canvas-tips">
        <el-icon><Mouse /></el-icon>
        <span>支持鼠标拖拽旋转，滚轮缩放</span>
      </div>
    </div>
  </div>
</template>

<script setup>
import { CirclePlus, Box, Refresh, Download, Mouse } from '@element-plus/icons-vue';
import AIWorkshopCanvas from '@/components/AIWorkshopCanvas.vue';

const parts = [
  { id: 1, name: '头部', icon: '😊' },
  { id: 2, name: '身体', icon: '👕' },
  { id: 3, name: '手臂', icon: '💪' },
  { id: 4, name: '腿部', icon: '🦵' },
];

const onDragStart = (part, event) => {
  event.dataTransfer.setData('partId', part.id);
};

const resetCanvas = () => {
  console.log('Reset canvas');
};

const exportModel = () => {
  console.log('Export model');
};
</script>

<style scoped>
.ai-workshop-view {
  display: flex;
  height: 700px;
}

.parts-panel {
  width: 280px;
  flex-shrink: 0;
  background: #f9f9f9;
  padding: 20px;
  border-right: 1px solid #eee;
}

.panel-header {
  margin-bottom: 20px;
}

.panel-header h3 {
  margin: 0;
  font-size: 1rem;
  font-weight: 600;
  color: #2c3e50;
  display: flex;
  align-items: center;
  gap: 8px;
}

.panel-header p {
  margin: 8px 0 0;
  font-size: 0.85rem;
  color: #999;
}

.parts-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 12px;
}

.part-item {
  text-align: center;
  cursor: grab;
  border: 2px solid transparent;
  border-radius: 12px;
  padding: 16px;
  background: white;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.06);
  transition: all 0.3s;
}

.part-item:hover {
  border-color: #4a90a4;
  transform: translateY(-3px);
  box-shadow: 0 6px 16px rgba(0, 0, 0, 0.1);
}

.part-item:active {
  cursor: grabbing;
}

.part-icon {
  font-size: 3rem;
  margin-bottom: 10px;
}

.part-item p {
  margin: 0;
  font-size: 0.85rem;
  color: #333;
  font-weight: 500;
}

.canvas-container {
  flex: 1;
  display: flex;
  flex-direction: column;
  background: #f5f5f5;
}

.canvas-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px 20px;
  background: white;
  border-bottom: 1px solid #eee;
}

.canvas-header h3 {
  margin: 0;
  font-size: 1rem;
  font-weight: 600;
  color: #2c3e50;
  display: flex;
  align-items: center;
  gap: 8px;
}

.canvas-actions {
  display: flex;
  gap: 10px;
}

.canvas-wrapper {
  flex: 1;
  position: relative;
}

.canvas-tips {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  padding: 12px;
  background: rgba(255, 255, 255, 0.8);
  font-size: 0.85rem;
  color: #999;
}

@media (max-width: 768px) {
  .ai-workshop-view {
    flex-direction: column;
    height: auto;
  }

  .parts-panel {
    width: 100%;
    border-right: none;
    border-bottom: 1px solid #eee;
  }

  .parts-grid {
    grid-template-columns: repeat(4, 1fr);
  }

  .canvas-wrapper {
    height: 500px;
  }
}
</style>
