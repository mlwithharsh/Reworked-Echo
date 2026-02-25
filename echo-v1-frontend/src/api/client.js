import axios from 'axios';

const api = axios.create({
  baseURL: import.meta.env.VITE_BACKEND_URL || 'http://localhost:5000',
  headers: {
    'Content-Type': 'application/json',
  },
});

export const coreAPI = {
  getStatus: () => api.get('/core/status'),
};

export const voiceAPI = {
  process: (audioBlob, personality) => {
    const formData = new FormData();
    formData.append('audio', audioBlob);
    formData.append('personality', personality);
    return api.post('/voice/process', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
  },
};

export const textAPI = {
  process: (text, personality) => api.post('/text/process', { text, personality }),
};

export const memoryAPI = {
  clear: () => api.post('/memory/clear'),
  getHistory: () => api.get('/memory/history'),
};

export default api;
