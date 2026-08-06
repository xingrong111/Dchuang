import request from './index';

export const getCulturalItems = () => {
  return request.get('/museum/items');
};

export const getCulturalItemDetail = (id) => {
  return request.get(`/museum/items/${id}`);
};

export const get3DModel = (modelPath) => {
  return request.get(`/museum/models/${modelPath}`, { responseType: 'blob' });
};