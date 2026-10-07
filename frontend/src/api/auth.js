import request from './index';
export const logout = () => request.post('/auth/logout');

// 登录：返回 data.token（JWT）+ 用户信息，后端同时建立 Session Cookie
export const login = (data) => {
  return request.post('/auth/login', data);
};

// 注册：成功不返回 token，注册后需登录
export const register = (data) => {
  return request.post('/auth/register', data);
};

// 当前用户信息（需 Bearer Token）
export const getUserInfo = () => {
  return request.get('/auth/user');
};

// 忘记密码：发送验证码到邮箱
export const forgotPassword = (email) => {
  return request.post('/auth/forgot-password', { email });
};

// 重置密码：验证码 + 新密码
export const resetPassword = (data) => {
  return request.post('/auth/reset-password', data);
};
