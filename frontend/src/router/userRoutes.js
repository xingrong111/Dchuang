export default [
  ...['help', 'terms', 'privacy'].map(name => ({ path: '/' + name, name,
    component: () => import('@/views/User/InformationView.vue') })),
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
    path: '/forgot-password',
    name: 'forgot-password',
    component: () => import('@/views/User/ForgotPasswordView.vue')
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
