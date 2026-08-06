import request from './index';

export const getWorks = (params) => {
  return request.get('/community/works', { params });
};

export const getWorkDetail = (id) => {
  return request.get(`/community/works/${id}`);
};

export const uploadWork = (data) => {
  return request.post('/community/works', data, {
    headers: { 'Content-Type': 'multipart/form-data' }
  });
};

export const likeWork = (id) => {
  return request.post(`/community/works/${id}/like`);
};

export const commentWork = (id, data) => {
  return request.post(`/community/works/${id}/comments`, data);
};