import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import axios from 'axios';

const API_URL = process.env.REACT_APP_BACKEND_URL + '/api';
axios.defaults.baseURL = API_URL;

// Auth Store
export const useAuthStore = create(
  persist(
    (set, get) => ({
      user: null, token: null, isAuthenticated: false, isLoading: false, error: null,
      setAuth: (user, token) => { axios.defaults.headers.common['Authorization'] = `Bearer ${token}`; set({ user, token, isAuthenticated: true, error: null }); },
      login: async (email, password) => {
        set({ isLoading: true, error: null });
        try {
          const response = await axios.post('/auth/login', { email, password });
          const { access_token, user } = response.data;
          axios.defaults.headers.common['Authorization'] = `Bearer ${access_token}`;
          set({ user, token: access_token, isAuthenticated: true, isLoading: false });
          return { success: true };
        } catch (error) { set({ error: error.response?.data?.detail || 'Error', isLoading: false }); return { success: false, error: error.response?.data?.detail }; }
      },
      register: async (email, password, fullName, role = 'participant') => {
        set({ isLoading: true, error: null });
        try {
          const response = await axios.post('/auth/register', { email, password, full_name: fullName, role });
          const { access_token, user } = response.data;
          axios.defaults.headers.common['Authorization'] = `Bearer ${access_token}`;
          set({ user, token: access_token, isAuthenticated: true, isLoading: false });
          return { success: true };
        } catch (error) { set({ error: error.response?.data?.detail || 'Error', isLoading: false }); return { success: false, error: error.response?.data?.detail }; }
      },
      logout: () => { delete axios.defaults.headers.common['Authorization']; set({ user: null, token: null, isAuthenticated: false }); },
      initAuth: () => { const token = get().token; if (token) axios.defaults.headers.common['Authorization'] = `Bearer ${token}`; }
    }),
    { name: 'digikawsay-auth', partialize: (state) => ({ user: state.user, token: state.token, isAuthenticated: state.isAuthenticated }) }
  )
);

// Campaign Store
export const useCampaignStore = create((set) => ({
  campaigns: [], currentCampaign: null, coverage: null, isLoading: false, error: null,
  fetchCampaigns: async (status = null) => { set({ isLoading: true }); try { const url = status ? `/campaigns/?status=${status}` : '/campaigns/'; const response = await axios.get(url); set({ campaigns: response.data, isLoading: false }); } catch (error) { set({ error: error.message, isLoading: false }); } },
  getCampaign: async (id) => { set({ isLoading: true }); try { const response = await axios.get(`/campaigns/${id}`); set({ currentCampaign: response.data, isLoading: false }); return response.data; } catch (error) { set({ error: error.message, isLoading: false }); return null; } },
  createCampaign: async (data) => { set({ isLoading: true }); try { const response = await axios.post('/campaigns/', data); set((state) => ({ campaigns: [...state.campaigns, response.data], isLoading: false })); return { success: true, data: response.data }; } catch (error) { set({ isLoading: false }); return { success: false, error: error.response?.data?.detail }; } },
  updateCampaign: async (id, data) => { set({ isLoading: true }); try { const response = await axios.put(`/campaigns/${id}`, data); set((state) => ({ campaigns: state.campaigns.map((c) => c.id === id ? response.data : c), currentCampaign: response.data, isLoading: false })); return { success: true, data: response.data }; } catch (error) { set({ isLoading: false }); return { success: false, error: error.response?.data?.detail }; } },
  updateCampaignStatus: async (id, status) => { try { await axios.patch(`/campaigns/${id}/status?status=${status}`); set((state) => ({ campaigns: state.campaigns.map((c) => c.id === id ? { ...c, status } : c), currentCampaign: state.currentCampaign?.id === id ? { ...state.currentCampaign, status } : state.currentCampaign })); return { success: true }; } catch (error) { return { success: false, error: error.response?.data?.detail }; } },
  getCoverage: async (id) => { try { const response = await axios.get(`/campaigns/${id}/coverage`); set({ coverage: response.data }); return response.data; } catch (error) { return null; } }
}));

// Script Store
export const useScriptStore = create((set) => ({
  scripts: [], currentScript: null, versions: [], isLoading: false, error: null,
  fetchScripts: async () => { set({ isLoading: true }); try { const response = await axios.get('/scripts/'); set({ scripts: response.data, isLoading: false }); } catch (error) { set({ error: error.message, isLoading: false }); } },
  getScript: async (id) => { set({ isLoading: true }); try { const response = await axios.get(`/scripts/${id}`); set({ currentScript: response.data, isLoading: false }); return response.data; } catch (error) { set({ error: error.message, isLoading: false }); return null; } },
  createScript: async (data) => { set({ isLoading: true }); try { const response = await axios.post('/scripts/', data); set((state) => ({ scripts: [...state.scripts, response.data], currentScript: response.data, isLoading: false })); return { success: true, data: response.data }; } catch (error) { set({ isLoading: false }); return { success: false, error: error.response?.data?.detail }; } },
  updateScript: async (id, data) => { set({ isLoading: true }); try { const response = await axios.put(`/scripts/${id}`, data); set((state) => ({ scripts: state.scripts.map((s) => s.id === id ? response.data : s), currentScript: response.data, isLoading: false })); return { success: true, data: response.data }; } catch (error) { set({ isLoading: false }); return { success: false, error: error.response?.data?.detail }; } },
  duplicateScript: async (id) => { set({ isLoading: true }); try { const response = await axios.post(`/scripts/${id}/duplicate`); set((state) => ({ scripts: [...state.scripts, response.data], isLoading: false })); return { success: true, data: response.data }; } catch (error) { set({ isLoading: false }); return { success: false, error: error.response?.data?.detail }; } },
  getVersions: async (id) => { try { const response = await axios.get(`/scripts/${id}/versions`); set({ versions: response.data.versions || [] }); return response.data.versions; } catch (error) { return []; } }
}));

// Insight Store (NEW - Phase 3)
export const useInsightStore = create((set) => ({
  insights: [], currentInsight: null, stats: null, isLoading: false, error: null,
  fetchInsights: async (campaignId, filters = {}) => {
    set({ isLoading: true });
    try {
      let url = `/insights/campaign/${campaignId}`;
      const params = new URLSearchParams();
      if (filters.type) params.append('type', filters.type);
      if (filters.status) params.append('status', filters.status);
      if (filters.sentiment) params.append('sentiment', filters.sentiment);
      if (params.toString()) url += `?${params.toString()}`;
      const response = await axios.get(url);
      set({ insights: response.data, isLoading: false });
    } catch (error) { set({ error: error.message, isLoading: false }); }
  },
  getInsight: async (id) => { set({ isLoading: true }); try { const response = await axios.get(`/insights/${id}`); set({ currentInsight: response.data, isLoading: false }); return response.data; } catch (error) { set({ error: error.message, isLoading: false }); return null; } },
  createInsight: async (data) => { set({ isLoading: true }); try { const response = await axios.post('/insights/', data); set((state) => ({ insights: [response.data, ...state.insights], isLoading: false })); return { success: true, data: response.data }; } catch (error) { set({ isLoading: false }); return { success: false, error: error.response?.data?.detail }; } },
  updateInsight: async (id, data) => { set({ isLoading: true }); try { const response = await axios.put(`/insights/${id}`, data); set((state) => ({ insights: state.insights.map((i) => i.id === id ? response.data : i), currentInsight: response.data, isLoading: false })); return { success: true, data: response.data }; } catch (error) { set({ isLoading: false }); return { success: false, error: error.response?.data?.detail }; } },
  validateInsight: async (id, validated) => { try { await axios.patch(`/insights/${id}/validate?validated=${validated}`); set((state) => ({ insights: state.insights.map((i) => i.id === id ? { ...i, status: validated ? 'validated' : 'rejected' } : i) })); return { success: true }; } catch (error) { return { success: false, error: error.response?.data?.detail }; } },
  getStats: async (campaignId) => { try { const response = await axios.get(`/insights/campaign/${campaignId}/stats`); set({ stats: response.data }); return response.data; } catch (error) { return null; } },
  extractInsights: async (campaignId) => { set({ isLoading: true }); try { const response = await axios.post(`/insights/campaign/${campaignId}/extract`); set({ isLoading: false }); return { success: true, data: response.data }; } catch (error) { set({ isLoading: false }); return { success: false, error: error.response?.data?.detail }; } }
}));

// Taxonomy Store (NEW - Phase 3)
export const useTaxonomyStore = create((set) => ({
  categories: [], isLoading: false, error: null,
  fetchCategories: async (type = null) => { set({ isLoading: true }); try { const url = type ? `/taxonomy/?type=${type}` : '/taxonomy/'; const response = await axios.get(url); set({ categories: response.data, isLoading: false }); } catch (error) { set({ error: error.message, isLoading: false }); } },
  createCategory: async (data) => { set({ isLoading: true }); try { const response = await axios.post('/taxonomy/', data); set((state) => ({ categories: [...state.categories, response.data], isLoading: false })); return { success: true, data: response.data }; } catch (error) { set({ isLoading: false }); return { success: false, error: error.response?.data?.detail }; } },
  updateCategory: async (id, data) => { set({ isLoading: true }); try { const response = await axios.put(`/taxonomy/${id}`, data); set((state) => ({ categories: state.categories.map((c) => c.id === id ? response.data : c), isLoading: false })); return { success: true, data: response.data }; } catch (error) { set({ isLoading: false }); return { success: false, error: error.response?.data?.detail }; } },
  deleteCategory: async (id) => { try { await axios.delete(`/taxonomy/${id}`); set((state) => ({ categories: state.categories.filter((c) => c.id !== id) })); return { success: true }; } catch (error) { return { success: false, error: error.response?.data?.detail }; } }
}));

// Transcript Store (NEW - Phase 3)
export const useTranscriptStore = create((set) => ({
  transcripts: [], currentTranscript: null, isLoading: false, error: null,
  fetchTranscripts: async (campaignId) => { set({ isLoading: true }); try { const response = await axios.get(`/transcripts/campaign/${campaignId}`); set({ transcripts: response.data, isLoading: false }); } catch (error) { set({ error: error.message, isLoading: false }); } },
  getTranscript: async (id) => { set({ isLoading: true }); try { const response = await axios.get(`/transcripts/${id}`); set({ currentTranscript: response.data, isLoading: false }); return response.data; } catch (error) { set({ error: error.message, isLoading: false }); return null; } },
  pseudonymize: async (id) => { try { const response = await axios.post(`/transcripts/${id}/pseudonymize`); return { success: true, data: response.data }; } catch (error) { return { success: false, error: error.response?.data?.detail }; } }
}));

// Validation Store (NEW - Phase 3)
export const useValidationStore = create((set) => ({
  pendingValidations: [], isLoading: false, error: null,
  fetchPending: async () => { set({ isLoading: true }); try { const response = await axios.get('/validations/pending'); set({ pendingValidations: response.data, isLoading: false }); } catch (error) { set({ error: error.message, isLoading: false }); } },
  respond: async (id, validated, comment = null) => { try { await axios.post(`/validations/${id}/respond`, { validated, comment }); set((state) => ({ pendingValidations: state.pendingValidations.filter((v) => v.id !== id) })); return { success: true }; } catch (error) { return { success: false, error: error.response?.data?.detail }; } }
}));

// Invite Store
export const useInviteStore = create((set) => ({
  invites: [], myInvites: [], isLoading: false, error: null,
  fetchCampaignInvites: async (campaignId) => { set({ isLoading: true }); try { const response = await axios.get(`/invites/campaign/${campaignId}`); set({ invites: response.data, isLoading: false }); } catch (error) { set({ error: error.message, isLoading: false }); } },
  fetchMyInvites: async () => { set({ isLoading: true }); try { const response = await axios.get('/invites/my-invites'); set({ myInvites: response.data, isLoading: false }); } catch (error) { set({ error: error.message, isLoading: false }); } },
  createBulkInvites: async (data) => { set({ isLoading: true }); try { const response = await axios.post('/invites/bulk', data); set({ isLoading: false }); return { success: true, data: response.data }; } catch (error) { set({ isLoading: false }); return { success: false, error: error.response?.data?.detail }; } }
}));

// Users Store
export const useUsersStore = create((set) => ({
  users: [], isLoading: false, error: null,
  fetchUsers: async (role = null) => { set({ isLoading: true }); try { const url = role ? `/users/?role=${role}` : '/users/'; const response = await axios.get(url); set({ users: response.data, isLoading: false }); } catch (error) { set({ error: error.message, isLoading: false }); } }
}));

// Session Store
export const useSessionStore = create((set) => ({
  sessions: [], currentSession: null, isLoading: false, error: null,
  fetchSessions: async () => { set({ isLoading: true }); try { const response = await axios.get('/sessions/'); set({ sessions: response.data, isLoading: false }); } catch (error) { set({ error: error.message, isLoading: false }); } },
  createSession: async (campaignId) => { set({ isLoading: true }); try { const response = await axios.post('/sessions/', { campaign_id: campaignId }); set((state) => ({ sessions: [...state.sessions, response.data], currentSession: response.data, isLoading: false })); return { success: true, data: response.data }; } catch (error) { set({ isLoading: false }); return { success: false, error: error.response?.data?.detail }; } },
  completeSession: async (sessionId) => { try { await axios.post(`/sessions/${sessionId}/complete`); set((state) => ({ sessions: state.sessions.map((s) => s.id === sessionId ? { ...s, status: 'completed' } : s), currentSession: null })); return { success: true }; } catch (error) { return { success: false, error: error.response?.data?.detail }; } },
  setCurrentSession: (session) => set({ currentSession: session })
}));

// Consent Store
export const useConsentStore = create((set) => ({
  consents: [], isLoading: false, error: null,
  fetchConsents: async () => { set({ isLoading: true }); try { const response = await axios.get('/consents/my-consents'); set({ consents: response.data, isLoading: false }); } catch (error) { set({ error: error.message, isLoading: false }); } },
  createConsent: async (campaignId, accepted) => { set({ isLoading: true }); try { const response = await axios.post('/consents/', { campaign_id: campaignId, accepted }); set((state) => ({ consents: [...state.consents, response.data], isLoading: false })); return { success: true, data: response.data }; } catch (error) { set({ isLoading: false }); return { success: false, error: error.response?.data?.detail }; } },
  hasConsent: (campaignId) => { const consents = useConsentStore.getState().consents; return consents.some(c => c.campaign_id === campaignId && c.accepted && !c.revoked_at); }
}));

// Chat Store
export const useChatStore = create((set) => ({
  messages: [], isLoading: false, error: null,
  fetchHistory: async (sessionId) => { set({ isLoading: true }); try { const response = await axios.get(`/chat/history/${sessionId}`); set({ messages: response.data.messages || [], isLoading: false }); } catch (error) { set({ error: error.message, isLoading: false }); } },
  sendMessage: async (sessionId, message) => {
    set({ isLoading: true });
    const userMsg = { role: 'user', content: message, timestamp: new Date().toISOString() };
    set((state) => ({ messages: [...state.messages, userMsg] }));
    try {
      const response = await axios.post('/chat/message', { session_id: sessionId, message });
      const assistantMsg = { role: 'assistant', content: response.data.message, timestamp: response.data.timestamp };
      set((state) => ({ messages: [...state.messages, assistantMsg], isLoading: false }));
      return { success: true, data: response.data };
    } catch (error) { set({ isLoading: false }); return { success: false, error: error.response?.data?.detail }; }
  },
  clearMessages: () => set({ messages: [] })
}));

// Dashboard Store
export const useDashboardStore = create((set) => ({
  stats: null, isLoading: false, error: null,
  fetchStats: async () => { set({ isLoading: true }); try { const response = await axios.get('/dashboard/stats'); set({ stats: response.data, isLoading: false }); } catch (error) { set({ error: error.message, isLoading: false }); } }
}));
