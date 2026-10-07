import axios from 'axios';
import { ElMessage } from 'element-plus';
import { useUserStore } from '@/store/userStore';

const visibleMessage=value=>String(value).replace(/AI\s*Provider/gi,'创作服务').replace(/\bAI\s*/gi,'创作').replace('AI服务','创作服务');
// Older image tasks used this automatic title; preserve authored titles and file URLs.
const normalizeDisplay = value => {
  if (!value || typeof value !== 'object') return;
  if (typeof value.title === 'string') value.title = value.title.replace(/^AI\s*生成作品-([a-f0-9]{8})$/i, '创作作品-$1');
  if (typeof value.error_message === 'string') value.error_message = visibleMessage(value.error_message);
  for (const child of Object.values(value)) if (child && typeof child === 'object') normalizeDisplay(child);
};
const instance = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || '/api',
  timeout: 10000,
});

instance.interceptors.request.use(
  (config) => {
    const userStore = useUserStore();
    if (userStore.user?.token) {
      config.headers.Authorization = `Bearer ${userStore.user.token}`;
    }
    return config;
  },
  (error) => {
    ElMessage.error('请求失败，请稍后重试');
    return Promise.reject(error);
  }
);

instance.interceptors.response.use(
  (response) => {
    const data = response.data;
    normalizeDisplay(data.data);
    if (data.code && data.code !== 200 && data.code !== 0) {
      ElMessage.warning(visibleMessage(data.message || '操作失败'));
      return Promise.reject(new Error(visibleMessage(data.message || '操作失败')));
    }
    return data;
  },
  (error) => {
    if (error.response?.status === 401) {
      const userStore = useUserStore();
      const wasAuthenticated = !!userStore.user?.token;
      userStore.clearSession();
      ElMessage.warning(error.response?.data?.message || (wasAuthenticated ? '登录已过期，请重新登录' : '请先登录'));
      const authRequest = /\/auth\/(login|register|forgot-password|reset-password|logout)$/.test(error.config?.url || '');
      if (!authRequest && wasAuthenticated && !window.location.pathname.startsWith('/login')) {
        const redirect = window.location.pathname + window.location.search;
        window.location.href = `/login?redirect=${encodeURIComponent(redirect)}`;
      }
    } else if (error.response?.status === 402) {
      // 402 = 积分不足（后端不会创建任务），message 含所需积分
      ElMessage.warning(error.response?.data?.message || '积分不足，无法进行该操作');
    } else if (error.response?.status === 403) {
      ElMessage.error('没有权限访问该资源');
    } else if (error.response?.status === 404) {
      ElMessage.error('请求的资源不存在');
    } else if (error.response?.status === 503) {
      // 503 = AI Provider 停用或服务异常
      ElMessage.warning(visibleMessage(error.response?.data?.message || '创作服务暂不可用，请稍后再试'));
    } else if (error.response?.status === 500) {
      ElMessage.error('服务器内部错误，请稍后重试');
    } else if (error.message?.includes('timeout')) {
      ElMessage.error('请求超时，请检查网络连接');
    } else {
      ElMessage.error(visibleMessage(error.response?.data?.message || error.message || '请求失败'));
    }
    return Promise.reject(error);
  }
);

export default instance;
