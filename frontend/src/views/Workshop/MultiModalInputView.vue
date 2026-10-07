<template>
  <div class="multi-modal-view">
    <!-- 左侧多模态输入 -->
    <div class="input-panel">
      <h3>多模态输入</h3>
      <AdvancedMultiModalInput :disabled="isBusy" @generate="handleGenerate" @analyze="handleAnalyze" />

      <!-- 任务状态区 -->
      <div v-if="statusMessage" class="task-status" :class="taskStatusClass">
        <el-icon v-if="isBusy" class="is-loading"><Loading /></el-icon>
        <span>{{ statusMessage }}</span>
        <el-button v-if="pollPaused && currentTaskId" @click="startPolling(currentTaskId)">恢复查询</el-button>
        <el-button v-if="taskStatus === 'FAILED' && currentTaskId" size="small" type="warning" @click="handleRetry">
          重试任务
        </el-button>
      </div>

      <!-- 风格分析结果 -->
      <div v-if="analyzeResult" class="analyze-result">
        <h4>风格分析结果</h4>
        <p v-if="analyzeResult.style"><strong>风格：</strong>{{ analyzeResult.style }}</p>
        <ul v-if="analyzeResult.features && analyzeResult.features.length">
          <li v-for="(f, i) in analyzeResult.features" :key="i">{{ f }}</li>
        </ul>
        <details v-if="analyzeResult.report?.classifier"><summary>大小模型协作结果</summary><p>小模型分类：{{ analyzeResult.report.classifier.style }}</p><p>大模型描述：{{ analyzeResult.report.vision.style }}</p><p v-if="analyzeResult.report.needs_review">分类置信度较低，建议人工核对</p></details>
        <el-button size="small" text type="primary" @click="analyzeResult = null">收起</el-button>
      </div>

      <!-- 积分显示 -->
      <div class="credits-line">
        <el-icon><Wallet /></el-icon>
        <span>积分余额：<strong>{{ credits ?? '--' }}</strong></span>
      </div>
    </div>

    <!-- 右侧3D模型预览 -->
    <div class="preview-panel">
      <ModelPreview :url="modelUrl" />
      <div v-if="isBusy" class="preview-overlay">
        <el-icon class="is-loading" size="36" color="#4a90a4"><Loading /></el-icon>
        <p>正在制作作品，请稍候…</p>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue';
import ModelPreview from '@/components/ModelPreview.vue';
import { ElMessage } from 'element-plus';
import { Loading, Wallet } from '@element-plus/icons-vue';
import AdvancedMultiModalInput from '@/components/AdvancedMultiModalInput.vue';
import { generate3D, getTask, retryTask, analyzeStyle } from '@/api/ai';
import { getWorkDetail } from '@/api/workshop';
import { getUserCredits } from '@/api/user';
import { useUserStore } from '@/store/userStore';
const userStore = useUserStore();

const modelUrl = ref('');
const pollPaused = ref(false);
let disposed = false;
let pollVersion = 0;

// ---- 任务状态 ----
const taskStatus = ref('idle'); // idle | submitting | PENDING | RUNNING | SUCCESS | FAILED
const statusMessage = ref('');
const currentTaskId = ref(null);
const analyzeResult = ref(null);
const credits = ref(null);

const isBusy = computed(() => !pollPaused.value && ['analyzing', 'submitting', 'PENDING', 'RUNNING'].includes(taskStatus.value));
const taskStatusClass = computed(() => ({
  'status-running': isBusy.value,
  'status-success': taskStatus.value === 'SUCCESS',
  'status-failed': taskStatus.value === 'FAILED'
}));

// ---- 轮询 ----
const POLL_INTERVAL = 3000;
const MAX_POLLS = 200; // 约 10 分钟
let pollTimer = null;
let pollCount = 0;

const stopPolling = () => {
  pollVersion++;
  clearTimeout(pollTimer);
  pollTimer = null;
};

const startPolling = (taskId) => {
  stopPolling(); pollPaused.value = false; pollCount = 0;
  const version = pollVersion;
  const tick = async () => {
    if (disposed || version !== pollVersion) return;
    if (++pollCount > MAX_POLLS) {
      stopPolling(); pollPaused.value = true;
      statusMessage.value = '等待超时，后台任务仍可能进行中，可恢复查询或到个人中心查看';
      return;
    }
    try {
      const task = (await getTask(taskId)).data;
      if (disposed || version !== pollVersion) return;
      taskStatus.value = task.status;
      if (['SUCCESS', 'FAILED'].includes(task.status)) {
        stopPolling();
        if (task.status === 'SUCCESS') { await loadModelFromTask(task); }
        else { statusMessage.value = `制作失败：${task.error_message || '未知原因'}`; }
        await refreshCredits();
        return;
      }
      statusMessage.value = task.status === 'RUNNING' ? '模型制作中，请稍候…' : '任务排队中...';
      pollTimer = setTimeout(tick, POLL_INTERVAL);
    } catch {
      if (disposed || version !== pollVersion) return;
      stopPolling(); pollPaused.value = true;
      statusMessage.value = '任务查询中断，点击恢复查询不会重新提交生成任务';
    }
  };
  tick();
};

const resolveModelUrl = async (task) => {
  // 优先用回填的作品详情（作品为准），其次任务 result_url
  if (task.artwork_id) {
    try {
      const resp = await getWorkDetail(task.artwork_id);
      if (resp.data?.model_url) return resp.data.model_url;
    } catch {
      // 回退到 result_url
    }
  }
  return task.result_url;
};

const loadModelFromTask = async (task) => {
  const url = await resolveModelUrl(task);
  if (!url) {
    statusMessage.value = '任务完成，但未获取到模型文件';
    return;
  }
  if (!disposed) { modelUrl.value = url; statusMessage.value = task.provider === 'mock' ? '演示任务完成：展示固定阿福模型，使用预设模型展示' : '任务已完成，正在加载模型'; }
};

// ---- AI 提交 ----
const handleGenerate = async (payload) => {
  if (!userStore.user?.token) return ElMessage.warning('请先登录后创作，3D 资产库可直接浏览');
  if (isBusy.value) return;
  stopPolling(); pollPaused.value = false;
  taskStatus.value = 'submitting';
  statusMessage.value = '正在提交任务...';
  try {
    const resp = await generate3D(payload);
    if (disposed) return;
    const task = resp.data;
    currentTaskId.value = task.id;
    if (task.status === 'SUCCESS') {
      taskStatus.value = 'SUCCESS';
      statusMessage.value = '模型已完成';
      await loadModelFromTask(task);
      refreshCredits();
    } else if (task.status === 'FAILED') {
      taskStatus.value = 'FAILED'; statusMessage.value = task.error_message || '制作失败'; await refreshCredits();
    } else {
      taskStatus.value = task.status || 'PENDING';
      statusMessage.value = task.status === 'RUNNING' ? '模型制作中，请稍候…' : '任务排队中...';
      startPolling(task.id);
    }
  } catch {
    taskStatus.value = 'idle';
    statusMessage.value = '提交未完成或结果未确认，请在个人中心核对任务记录';
    refreshCredits();
  }
};

const handleAnalyze = async (payload) => {
  if (!userStore.user?.token) return ElMessage.warning('请先登录后进行风格分析');
  if (isBusy.value) return;
  stopPolling(); pollPaused.value = false; taskStatus.value = 'analyzing';
  statusMessage.value = '正在分析风格...';
  try {
    const resp = await analyzeStyle(payload);
    if(disposed)return;
    analyzeResult.value = {
      style: resp.data.style,
      features: resp.data.features || [],
      report: resp.data.report
    };
    statusMessage.value = '';
    refreshCredits();
    ElMessage.success('风格分析完成');
  } catch {
    statusMessage.value = '风格分析失败，请核对积分与任务记录';
  } finally { taskStatus.value = 'idle'; await refreshCredits(); }
};

const handleRetry = async () => {
  if (!currentTaskId.value || isBusy.value) return;
  taskStatus.value='submitting';statusMessage.value='正在提交重试任务…';
  try {
    const resp = await retryTask(currentTaskId.value);
    if (disposed) return;
    const task = resp.data;
    if (disposed) return;
    currentTaskId.value = task.id;
    taskStatus.value = task.status || 'PENDING';
    statusMessage.value = '已创建重试任务';
    startPolling(task.id);
  } catch {
    taskStatus.value='FAILED';statusMessage.value='重试未完成，请重试或查看个人中心';
  }
};

const refreshCredits = async () => {
  if(disposed)return;
  if (!userStore.user?.token) { credits.value = null; return; }
  try {
    const resp = await getUserCredits({ per_page: 1 });
    credits.value = resp.data.balance;
  } catch {
    credits.value = null;
  }
};

onMounted(() => { disposed = false; refreshCredits(); });
onUnmounted(() => { disposed = true; stopPolling(); });
</script>

<style scoped>
.multi-modal-view {
  display: flex;
  height: 640px;
}
.input-panel {
  width: 32%;
  min-width: 340px;
  background: #f9f9f9;
  padding: 20px;
  border-right: 1px solid #ddd;
  overflow-y: auto;
}
.input-panel h3 {
  margin: 0 0 10px;
  color: #2c3e50;
}
.preview-panel :deep(.model-preview) { height: 100%; }
.preview-panel {
  flex: 1;
  position: relative;
  background: #eaeaea;
}
.preview-canvas {
  width: 100%;
  height: 100%;
}
.preview-overlay {
  position: absolute;
  inset: 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 12px;
  background: rgba(255, 255, 255, 0.55);
  pointer-events: none;
}
.preview-overlay p {
  margin: 0;
  color: #2d6172;
  font-weight: 500;
}

.task-status {
  margin-top: 16px;
  padding: 12px 14px;
  border-radius: 10px;
  font-size: 0.9rem;
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}
.status-running {
  background: #e8f1f3;
  color: #2d6172;
}
.status-success {
  background: #e8f6ec;
  color: #2e7d32;
}
.status-failed {
  background: #fdecea;
  color: #c0392b;
}

.analyze-result {
  margin-top: 16px;
  padding: 12px 14px;
  background: #fdf6e9;
  border-radius: 10px;
  font-size: 0.9rem;
  color: #6d5a2e;
}
.analyze-result h4 {
  margin: 0 0 8px;
  font-size: 0.95rem;
  color: #8b6914;
}
.analyze-result ul {
  margin: 8px 0 0;
  padding-left: 18px;
}
.analyze-result li {
  line-height: 1.6;
}

.credits-line {
  margin-top: 16px;
  display: flex;
  align-items: center;
  gap: 6px;
  color: #666;
  font-size: 0.9rem;
}
.credits-line strong {
  color: #b8860b;
}
</style>
