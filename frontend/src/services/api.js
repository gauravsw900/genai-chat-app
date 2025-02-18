import axios from 'axios';

const API = axios.create({
  baseURL: process.env.REACT_APP_API_URL || 'http://localhost:8000/api',
});

export const chatApi = {
  newSession: () => API.get('/chat/session/new').then(r => r.data),
  sendMessage: (payload) => API.post('/chat', payload).then(r => r.data),
  getHistory: (sessionId, limit = 50) =>
    API.get(`/chat/session/${sessionId}/history?limit=${limit}`).then(r => r.data),
  clearSession: (sessionId) => API.delete(`/chat/session/${sessionId}`).then(r => r.data),
  listSessions: () => API.get('/chat/sessions').then(r => r.data),
};

export const documentApi = {
  upload: (sessionId, file) => {
    const form = new FormData();
    form.append('file', file);
    form.append('session_id', sessionId);
    return API.post('/documents/upload', form, {
      headers: { 'Content-Type': 'multipart/form-data' }
    }).then(r => r.data);
  },
  clearDocs: (sessionId) => API.delete(`/documents/${sessionId}`).then(r => r.data),
  status: (sessionId) => API.get(`/documents/${sessionId}/status`).then(r => r.data),
};

export const healthApi = {
  check: () => axios.get(`${process.env.REACT_APP_API_URL?.replace('/api', '') || 'http://localhost:8000'}/health`).then(r => r.data),
};
