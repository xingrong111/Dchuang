import { ref } from 'vue';
import { defineStore } from 'pinia';
import { login as loginApi, register as registerApi, getUserInfo } from '@/api/auth';
import { setItem, getItem, removeItem } from '@/utils/storage';

export const useUserStore = defineStore('user', () => {
  const user = ref(getItem('user') || null);

  async function login(credentials) {
    try {
      const response = await loginApi(credentials);
      user.value = response.data;
      setItem('user', response.data);
      return response;
    } catch (error) {
      throw error;
    }
  }

  async function register(userData) {
    try {
      const response = await registerApi(userData);
      return response;
    } catch (error) {
      throw error;
    }
  }

  function logout() {
    user.value = null;
    removeItem('user');
  }

  async function fetchUserInfo() {
    try {
      const response = await getUserInfo();
      user.value = response.data;
      setItem('user', response.data);
      return response;
    } catch (error) {
      logout();
      throw error;
    }
  }

  return { user, login, logout, register, fetchUserInfo };
});