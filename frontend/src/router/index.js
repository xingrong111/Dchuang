import { createRouter, createWebHistory } from 'vue-router'
import userRoutes from './userRoutes';
import shopRoutes from './shopRoutes';
import museumRoutes from './museumRoutes';
import workshopRoutes from './workshopRoutes';
import communityRoutes from './communityRoutes';
import { getItem } from '@/utils/storage';

const routes = [
  { path: '/model-library', name: 'model-library', component: () => import('@/views/Museum/ModelLibraryView.vue') },
  { path: '/admin', name: 'admin', component: () => import('@/views/User/AdminView.vue'), meta: { requiresAuth: true } },
  {
    path: '/',
    name: 'home',
    component: () => import('@/views/Home/HomeView.vue')
  },
  ...userRoutes,
  ...shopRoutes,
  ...museumRoutes,
  ...workshopRoutes,
  ...communityRoutes,
  {
    path: '/workshop/multi-modal-input',
    name: 'MultiModalInputView',
    component: () => import('@/views/Workshop/MultiModalInputView.vue'),
    meta: { requiresAuth: true }
  },
  {
    path: '/workshop/3d-editor',
    name: 'AIWorkshopView',
    component: () => import('@/views/Workshop/AIWorkshopView.vue'),
    meta: { requiresAuth: false }
  },
  {
    path: '/:pathMatch(.*)*',
    name: 'not-found',
    component: () => import('@/views/NotFound.vue')
  }
]

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes
})

router.beforeEach((to, from, next) => {
  const isLoggedIn = !!getItem('user')?.token;

  if (to.meta.requiresAuth && !isLoggedIn) {
    next({
      path: '/login',
      query: { redirect: to.fullPath }
    });
  } else if (to.path === '/login' && isLoggedIn) {
    next('/');
  } else {
    next();
  }
});

export default router

