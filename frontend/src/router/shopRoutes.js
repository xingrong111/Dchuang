export default [
  {
    path: '/shop',
    name: 'shop',
    component: () => import('@/views/Shop/ShopCenterView.vue')
  },
  {
    path: '/shop/designs', name: 'designs', component: () => import('@/views/Shop/ConceptView.vue')
  },
  {
    path: '/shop/account', name: 'commerce-account', component: () => import('@/views/Shop/CommerceAccountView.vue'), meta: { requiresAuth: true }
  }
];
