import axios from 'axios'

const api = axios.create({
  baseURL: '/api',
  timeout: 30000,
})

// Memory API
export const memoryApi = {
  list: (params?: { memory_type?: string; limit?: number; offset?: number }) =>
    api.get('/memory/', { params }),
  get: (id: string) => api.get(`/memory/${id}`),
  save: (data: { content: string; memory_type: string; source?: string }) =>
    api.post('/memory/save', data),
  recall: (query: string, top_k?: number) =>
    api.get('/memory/recall', { params: { query, top_k } }),
  extract: (messages: { role: string; content: string }[]) =>
    api.post('/memory/extract', { messages }),
  delete: (id: string) => api.delete(`/memory/${id}`),
}

// Knowledge API
export const knowledgeApi = {
  search: (query: string, top_k?: number) =>
    api.get('/knowledge/search', { params: { query, top_k } }),
  ingest: (path: string) => api.post('/knowledge/ingest', null, { params: { path } }),
  listDocuments: (limit?: number) =>
    api.get('/knowledge/documents', { params: { limit } }),
  getDocument: (id: string) => api.get(`/knowledge/documents/${id}`),
  deleteDocument: (id: string) => api.delete(`/knowledge/documents/${id}`),
}

// Prompt API
export const promptApi = {
  list: (tag?: string) => api.get('/prompt/', { params: { tag } }),
  get: (name: string, version?: number) =>
    api.get(`/prompt/${name}`, { params: { version } }),
  save: (data: { name: string; content: string; description?: string; variables?: string[]; tags?: string[] }) =>
    api.post('/prompt/', data),
  score: (name: string, version: number, score: number) =>
    api.post(`/prompt/${name}/versions/${version}/score`, { score }),
  compare: (name: string, v1: number, v2: number) =>
    api.get(`/prompt/${name}/compare`, { params: { v1, v2 } }),
  optimize: (name: string, feedback?: string) =>
    api.post(`/prompt/${name}/optimize`, null, { params: { feedback } }),
  delete: (name: string) => api.delete(`/prompt/${name}`),
}

// Search API
export const searchApi = {
  search: (query: string, scope?: string, top_k?: number) =>
    api.get('/search/', { params: { query, scope, top_k } }),
}

export default api
