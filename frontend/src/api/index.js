import axios from 'axios';
import { ElMessage } from 'element-plus';
import { useUserStore } from '@/store/userStore';

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
    if (data.code && data.code !== 200 && data.code !== 0) {
      ElMessage.warning(data.message || '操作失败');
    }
    return data;
  },
  (error) => {
    if (error.response?.status === 401) {
      ElMessage.warning('登录已过期，请重新登录');
      const userStore = useUserStore();
      userStore.logout();
      setTimeout(() => {
        window.location.href = '/login';
      }, 1000);
    } else if (error.response?.status === 403) {
      ElMessage.error('没有权限访问该资源');
    } else if (error.response?.status === 404) {
      ElMessage.error('请求的资源不存在');
    } else if (error.response?.status === 500) {
      ElMessage.error('服务器内部错误，请稍后重试');
    } else if (error.message?.includes('timeout')) {
      ElMessage.error('请求超时，请检查网络连接');
    } else {
      ElMessage.error(error.response?.data?.message || error.message || '请求失败');
    }
    return Promise.reject(error);
  }
);

export default instance;
