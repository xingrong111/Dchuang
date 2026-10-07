import { ref, computed, watch } from 'vue'
import { defineStore } from 'pinia'
import { useUserStore } from '@/store/userStore'
import { getCart, addToCart as addCartApi, removeFromCart as removeCartApi, updateCart } from '@/api/shop'

export const useCartStore = defineStore('cart', () => {
  const userStore = useUserStore()
  const items = ref([]), busy = ref(false)
  let version = 0
  const totalCount = computed(() => items.value.reduce((sum, item) => sum + item.quantity, 0))
  const totalPrice = computed(() => items.value.reduce((sum, item) => sum + Math.round(item.price * 100) * item.quantity, 0) / 100)
  async function refresh() {
    if (!userStore.user?.token) { items.value = []; return }
    const token = version
    const response = await getCart()
    if (token === version) items.value = response.data || []
  }
  async function mutate(action) {
    if (!userStore.user?.token) throw new Error('请先登录')
    if (busy.value) return false
    const token = version
    busy.value = true
    try {
      await action()
      if (token === version) await refresh()
      return token === version
    } finally { if (token === version) busy.value = false }
  }
  const addToCart = (product, quantity = 1) => mutate(() => addCartApi({ product_id: product.id, quantity }))
  const removeFromCart = id => mutate(() => removeCartApi(id))
  const updateQuantity = (id, quantity) => mutate(() => updateCart(id, quantity))
  // 登录切换后丢弃旧用户状态，绝不共享旧浏览器 cart 缓存。
  watch(() => userStore.user?.id, () => {
    version++; items.value = []; busy.value = false
    if (userStore.user?.token) refresh().catch(() => {})
  }, { immediate: true, flush: 'sync' })
  return { items, busy, totalCount, totalPrice, refresh, addToCart, removeFromCart, updateQuantity }
})
