import axios from 'axios';

const apiToken = import.meta.env.VITE_API_TOKEN || 'dev-token';

const api = axios.create({
  baseURL: import.meta.env.VITE_BACKEND_URL || 'http://localhost:8000',
  headers: {
    'Content-Type': 'application/json',
    'x-api-token': apiToken,
  },
});

export const coreAPI = {
  getStatus: () => api.get('/api/status'),
};

export const userAPI = {
  getProfile: (userId) => api.get(`/api/users/${userId}/profile`),
  updateProfile: (userId, profile) => api.put(`/api/users/${userId}/profile`, { ...profile, user_id: userId }),
  getHistory: (userId) => api.get(`/api/users/${userId}/history`),
};

export const textAPI = {
  process: (payload) => api.post('/api/chat', payload),
  stream: async (payload, onEvent) => {
    const response = await fetch(`${import.meta.env.VITE_BACKEND_URL || 'http://localhost:8000'}/api/chat/stream`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'x-api-token': apiToken,
      },
      body: JSON.stringify(payload),
    });

    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let buffer = '';

    while (true) {
      const { value, done } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split('\n');
      buffer = lines.pop() || '';
      for (const line of lines) {
        if (!line.trim()) continue;
        onEvent(JSON.parse(line));
      }
    }
  },
};

export const feedbackAPI = {
  submit: (payload) => api.post('/api/feedback', payload),
};

export const modelAPI = {
  listVersions: () => api.get('/api/model/versions'),
  runTraining: (payload) => api.post('/api/training/run', payload),
};

export default api;
