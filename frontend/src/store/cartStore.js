import { ref, computed } from 'vue';
import { defineStore } from 'pinia';
import { setItem, getItem } from '@/utils/storage';

export const useCartStore = defineStore('cart', () => {
  const items = ref(getItem('cart') || []);

  const totalCount = computed(() => {
    return items.value.reduce((sum, item) => sum + item.quantity, 0);
  });

  const totalPrice = computed(() => {
    return items.value.reduce((sum, item) => sum + item.price * item.quantity, 0);
  });

  function addToCart(product) {
    const existingItem = items.value.find(item => item.id === product.id);
    if (existingItem) {
      existingItem.quantity++;
    } else {
      items.value.push({
        ...product,
        quantity: 1
      });
    }
    setItem('cart', items.value);
  }

  function removeFromCart(productId) {
    items.value = items.value.filter(item => item.id !== productId);
    setItem('cart', items.value);
  }

  function updateQuantity(productId, quantity) {
    const item = items.value.find(item => item.id === productId);
    if (item) {
      if (quantity <= 0) {
        removeFromCart(productId);
      } else {
        item.quantity = quantity;
        setItem('cart', items.value);
      }
    }
  }

  function clearCart() {
    items.value = [];
    setItem('cart', items.value);
  }

  return { items, totalCount, totalPrice, addToCart, removeFromCart, updateQuantity, clearCart };
});