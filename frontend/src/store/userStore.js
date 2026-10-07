import { ref } from 'vue';
import { defineStore } from 'pinia';
import { login as loginApi, logout as logoutApi, register as registerApi, getUserInfo } from '@/api/auth';
import { setItem, getItem, removeItem } from '@/utils/storage';

export const useUserStore = defineStore('user', () => {
  const user = ref(getItem('user') || null);

  async function login(credentials) {
    const response = await loginApi(credentials);
    // 后端 data 含 token，整体保存供 axios 拦截器注入 Bearer
    user.value = response.data;
    setItem('user', response.data);
    return response;
  }

  async function register(userData) {
    return await registerApi(userData);
  }

  function clearSession() {
    user.value = null;
    removeItem('user');
  }

  async function logout() {
    try { await logoutApi(); } finally { clearSession(); }
  }

  async function fetchUserInfo() {
    const response = await getUserInfo();
    // /auth/user 响应不含 token，必须保留原 token，否则后续 Bearer 会丢失
    const token = user.value?.token;
    user.value = { ...response.data, token };
    setItem('user', user.value);
    return response;
  }

  return { user, login, logout, clearSession, register, fetchUserInfo };
});
