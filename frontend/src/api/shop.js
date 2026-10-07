import request from './index';
export const cancelOrder = (id) => request.post(`/shop/orders/${id}/cancel`);
export const updateCart = (id, quantity) => request.put(`/shop/cart/${id}`, { quantity });

export const getProducts = (params) => {
  return request.get('/shop/products', { params });
};

export const getProductDetail = (id) => {
  return request.get(`/shop/products/${id}`);
};

export const createOrder = (data) => {
  return request.post('/shop/orders', data);
};

export const getOrders = (params) => {
  return request.get('/shop/orders', { params });
};

export const getCart = () => {
  return request.get('/shop/cart');
};

export const addToCart = (data) => {
  return request.post('/shop/cart', data);
};

export const removeFromCart = (id) => {
  return request.delete(`/shop/cart/${id}`);
};
