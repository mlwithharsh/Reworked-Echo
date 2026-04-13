import axios from 'axios';

const apiToken = import.meta.env.VITE_API_TOKEN || 'dev-token';

const api = axios.create({
  baseURL: import.meta.env.VITE_BACKEND_URL || 'https://reworked-echo.onrender.com',
  timeout: 60000, // 60s timeout for Render cold starts
  headers: {
    'Content-Type': 'application/json',
    'x-api-token': apiToken,
  },
});

// Add response interceptor for better error handling
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.code === 'ECONNABORTED') {
      error.message = 'Request timed out — server may be cold starting';
    }
    return Promise.reject(error);
  }
);

export const coreAPI = {
  getStatus: () => api.get('/api/status', { timeout: 10000 }), // Shorter timeout for health checks

};

export const userAPI = {
  getProfile: (userId) => api.get(`/api/users/${userId}/profile`),
  updateProfile: (userId, profile) => api.put(`/api/users/${userId}/profile`, { ...profile, user_id: userId }),
  getHistory: (userId) => api.get(`/api/users/${userId}/history`),
  clearHistory: (userId) => api.post(`/api/users/${userId}/clear`),

};

export const textAPI = {
  process: (payload) => api.post('/api/chat/stream', payload),

};

export const feedbackAPI = {
  submit: (payload) => api.post('/api/feedback', payload),

};

export const modelAPI = {
  listVersions: () => api.get('/api/model/versions'),
  runTraining: (payload) => api.post('/api/training/run', payload),

};

export const marketingAPI = {
  listBrandProfiles: () => api.get('/api/marketing/brand-profiles'),
  createBrandProfile: (payload) => api.post('/api/marketing/brand-profiles', payload),
  updateBrandProfile: (brandId, payload) => api.put(`/api/marketing/brand-profiles/${brandId}`, payload),
  listCampaigns: (status) => api.get('/api/marketing/campaigns', { params: status ? { status } : {} }),
  createCampaign: (payload) => api.post('/api/marketing/campaigns', payload),
  generateStrategy: (campaignId) => api.post(`/api/marketing/campaigns/${campaignId}/strategy`),
  generateVariants: (campaignId, payload) => api.post(`/api/marketing/campaigns/${campaignId}/generate`, payload),
  listVariants: (campaignId) => api.get(`/api/marketing/campaigns/${campaignId}/variants`),
  approveVariant: (variantId, approved, notes = '') =>
    api.post(`/api/marketing/variants/${variantId}/approve`, { approved, notes }),
  scheduleCampaign: (campaignId, payload) => api.post(`/api/marketing/campaigns/${campaignId}/schedule`, payload),
  listSchedules: (status) => api.get('/api/marketing/schedules', { params: status ? { status } : {} }),
  pauseSchedule: (jobId) => api.post(`/api/marketing/schedules/${jobId}/pause`),
  resumeSchedule: (jobId) => api.post(`/api/marketing/schedules/${jobId}/resume`),
  dispatchJob: (jobId, executionMode = 'dry_run') =>
    api.post(`/api/marketing/jobs/${jobId}/dispatch-now`, { execution_mode: executionMode }),
  listDeliveryLogs: (platform) => api.get('/api/marketing/delivery-logs', { params: platform ? { platform } : {} }),
  getPlatformHealth: () => api.get('/api/marketing/platform-health'),
  listChannelCredentials: () => api.get('/api/marketing/channel-credentials'),
  saveChannelCredentials: (payload) => api.post('/api/marketing/channel-credentials', payload),
  recordPerformanceEvent: (payload) => api.post('/api/marketing/performance-events', payload),
  getAnalyticsSummary: (campaignId) =>
    api.get('/api/marketing/analytics/summary', { params: campaignId ? { campaign_id: campaignId } : {} }),
  getCampaignAnalytics: (campaignId) => api.get(`/api/marketing/analytics/campaigns/${campaignId}`),
  optimizeCampaign: (campaignId) => api.post(`/api/marketing/optimize/campaigns/${campaignId}`),
};

export const smartParksAPI = {
  getDashboard: () => api.get('/api/smart-parks/dashboard'),
  getSummary: () => api.get('/api/smart-parks/summary'),
  listParks: () => api.get('/api/smart-parks/parks'),
  listZones: (parkId) => api.get('/api/smart-parks/zones', { params: parkId ? { park_id: parkId } : {} }),
  listDevices: (parkId) => api.get('/api/smart-parks/devices', { params: parkId ? { park_id: parkId } : {} }),
  listReadings: (params = {}) => api.get('/api/smart-parks/readings', { params }),
  ingestReadings: (payload) => api.post('/api/smart-parks/readings/ingest', payload),
  simulate: (payload) => api.post('/api/smart-parks/simulate', payload),
  listAlerts: (params = {}) => api.get('/api/smart-parks/alerts', { params }),
  acknowledgeAlert: (alertId) => api.post(`/api/smart-parks/alerts/${alertId}/acknowledge`),
  resolveAlert: (alertId) => api.post(`/api/smart-parks/alerts/${alertId}/resolve`),
  listWorkOrders: (params = {}) => api.get('/api/smart-parks/work-orders', { params }),
  createWorkOrder: (payload) => api.post('/api/smart-parks/work-orders', payload),
  updateWorkOrder: (workOrderId, payload) => api.patch(`/api/smart-parks/work-orders/${workOrderId}`, payload),
  getParkRisks: () => api.get('/api/smart-parks/park-risks'),
  getReportOverview: () => api.get('/api/smart-parks/reports/overview'),
};

export default api;
