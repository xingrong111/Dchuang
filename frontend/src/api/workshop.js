import request from './index';

export const generate3DModel = (data) => {
  return request.post('/workshop/generate', data);
};

export const getParts = () => {
  return request.get('/workshop/parts');
};

export const saveWork = (data) => {
  return request.post('/workshop/save', data);
};

export const uploadFile = (file) => {
  const formData = new FormData();
  formData.append('file', file);
  return request.post('/workshop/upload', formData, {
    headers: { 'Content-Type': 'multipart/form-data' }
  });
};