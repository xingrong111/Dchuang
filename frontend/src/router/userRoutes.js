export default [
  {
    path: '/login',
    name: 'login',
    component: () => import('@/views/User/LoginView.vue')
  },
  {
    path: '/register',
    name: 'register',
    component: () => import('@/views/User/RegisterView.vue')
  },
  {
    path: '/about',
    name: 'about',
    component: () => import('@/views/User/AboutView.vue')
  },
  {
    path: '/profile',
    name: 'profile',
    component: () => import('@/views/User/ProfileView.vue'),
    meta: { requiresAuth: true }
  }
];
