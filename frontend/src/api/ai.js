import request from './index';

// ============================================================
// AI 模块
// 对应后端路由（前端统一加 /api 前缀，Vite 代理剥除）:
//   POST /ai/generate-3d        3D 生成（text_to_3d / image_to_3d）
//   POST /ai/analyze-style      图片风格分析
//   GET  /ai/tasks              任务列表（分页，仅本人）
//   GET  /ai/tasks/statistics   任务统计
//   GET  /ai/tasks/:taskId      任务详情（读取时刷新异步任务状态，用于轮询）
//   POST /ai/tasks/:taskId/retry 失败任务重试
//   GET  /ai/history            AI 历史（分页，含关联作品摘要）
// ============================================================

export const generate3D = (data) => {
  return request.post('/ai/generate-3d', data, { timeout: 60000 });
};

export const analyzeStyle = (data) => {
  return request.post('/ai/analyze-style', data, { timeout: 120000 });
};

export const getTask = (taskId) => {
  return request.get(`/ai/tasks/${taskId}`, { timeout: 30000 });
};

export const getTasks = (params) => {
  return request.get('/ai/tasks', { params });
};

export const getTaskStatistics = () => {
  return request.get('/ai/tasks/statistics');
};

export const retryTask = (taskId) => {
  return request.post(`/ai/tasks/${taskId}/retry`);
};

export const getAIHistory = (params) => {
  return request.get('/ai/history', { params });
};
