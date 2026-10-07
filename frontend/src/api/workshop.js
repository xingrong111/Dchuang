import request from './index';
export const certifyWork = (id) => request.post(`/workshop/works/${id}/certify`, {}, { timeout: 60000 });
export const getCertificate = (id) => request.get(`/workshop/works/${id}/certificate`, { timeout: 60000 });

// ============================================================
// Workshop / Community 作品模块
// 对应后端路由（前端统一加 /api 前缀，Vite 代理剥除）:
//   GET    /workshop/works                  作品列表（分页，仅公开）
//   POST   /workshop/save                   保存作品
//   GET    /workshop/works/:id              作品详情（含 current_user_status）
//   PUT    /workshop/works/:id              更新作品（仅作者）
//   DELETE /workshop/works/:id              删除作品（仅作者）
//   POST   /workshop/works/:id/like         点赞（幂等）
//   DELETE /workshop/works/:id/like         取消点赞（幂等）
//   POST   /workshop/works/:id/collect      收藏（幂等）
//   DELETE /workshop/works/:id/collect      取消收藏（幂等）
//   GET    /workshop/works/:id/comments     评论列表（分页）
//   POST   /workshop/works/:id/comments     发表评论
//   DELETE /comments/:commentId             删除评论（仅评论作者）
//   POST   /workshop/upload                 上传图片/模型文件
// ============================================================

export const getWorks = (params) => {
  return request.get('/workshop/works', { params });
};

export const getWorkDetail = (id) => {
  return request.get(`/workshop/works/${id}`);
};

export const saveWork = (data) => {
  return request.post('/workshop/save', data);
};

export const updateWork = (id, data) => {
  return request.put(`/workshop/works/${id}`, data);
};

export const deleteWork = (id) => {
  return request.delete(`/workshop/works/${id}`);
};

export const likeWork = (id) => {
  return request.post(`/workshop/works/${id}/like`);
};

export const unlikeWork = (id) => {
  return request.delete(`/workshop/works/${id}/like`);
};

export const collectWork = (id) => {
  return request.post(`/workshop/works/${id}/collect`);
};

export const uncollectWork = (id) => {
  return request.delete(`/workshop/works/${id}/collect`);
};

export const getComments = (id, params) => {
  return request.get(`/workshop/works/${id}/comments`, { params });
};

export const postComment = (id, data) => {
  return request.post(`/workshop/works/${id}/comments`, data);
};

export const deleteComment = (commentId) => {
  return request.delete(`/comments/${commentId}`);
};

export const uploadFile = (file) => {
  const formData = new FormData();
  formData.append('file', file);
  return request.post('/workshop/upload', formData, {
    headers: { 'Content-Type': 'multipart/form-data' }
  });
};
