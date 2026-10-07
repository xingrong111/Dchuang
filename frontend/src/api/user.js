import request from './index';
export const updateProfile = (data) => request.put('/user/profile', data);
export const updatePassword = (data) => request.put('/user/password', data);
export const getCollections = (params) => request.get('/user/collections', { params });
export const getOwnWorks = (params) => request.get('/user/works', { params });
export const getUserStatistics = () => request.get('/user/statistics');

// ============================================================
// 用户中心模块
// 对应后端路由（前端统一加 /api 前缀，Vite 代理剥除）:
//   GET /user/credits        积分余额与流水（分页）
//   POST /user/upload-avatar 上传头像（JWT/Session 双认证）
// ============================================================

export const getUserCredits = (params) => {
  return request.get('/user/credits', { params });
};

export const uploadAvatar = (file) => {
  const formData = new FormData();
  formData.append('file', file);
  return request.post('/user/upload-avatar', formData, {
    headers: { 'Content-Type': 'multipart/form-data' }
  });
};
