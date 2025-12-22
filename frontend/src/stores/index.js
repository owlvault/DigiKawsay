import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import axios from 'axios';

const API_URL = process.env.REACT_APP_BACKEND_URL + '/api';

// Configure axios defaults
axios.defaults.baseURL = API_URL;

// Auth Store
export const useAuthStore = create(
  persist(
    (set, get) => ({
      user: null,
      token: null,
      isAuthenticated: false,
      isLoading: false,
      error: null,

      setAuth: (user, token) => {
        axios.defaults.headers.common['Authorization'] = `Bearer ${token}`;
        set({ user, token, isAuthenticated: true, error: null });
      },

      login: async (email, password) => {
        set({ isLoading: true, error: null });
        try {
          const response = await axios.post('/auth/login', { email, password });
          const { access_token, user } = response.data;
          axios.defaults.headers.common['Authorization'] = `Bearer ${access_token}`;
          set({ user, token: access_token, isAuthenticated: true, isLoading: false });
          return { success: true };
        } catch (error) {
          const message = error.response?.data?.detail || 'Error al iniciar sesión';
          set({ error: message, isLoading: false });
          return { success: false, error: message };
        }
      },

      register: async (email, password, fullName, role = 'participant') => {
        set({ isLoading: true, error: null });
        try {
          const response = await axios.post('/auth/register', {
            email,
            password,
            full_name: fullName,
            role
          });
          const { access_token, user } = response.data;
          axios.defaults.headers.common['Authorization'] = `Bearer ${access_token}`;
          set({ user, token: access_token, isAuthenticated: true, isLoading: false });
          return { success: true };
        } catch (error) {
          const message = error.response?.data?.detail || 'Error al registrarse';
          set({ error: message, isLoading: false });
          return { success: false, error: message };
        }
      },

      logout: () => {
        delete axios.defaults.headers.common['Authorization'];
        set({ user: null, token: null, isAuthenticated: false });
      },

      initAuth: () => {
        const token = get().token;
        if (token) {
          axios.defaults.headers.common['Authorization'] = `Bearer ${token}`;
        }
      }
    }),
    {
      name: 'digikawsay-auth',
      partialize: (state) => ({ user: state.user, token: state.token, isAuthenticated: state.isAuthenticated })
    }
  )
);

// Campaign Store
export const useCampaignStore = create((set) => ({
  campaigns: [],
  currentCampaign: null,
  isLoading: false,
  error: null,

  fetchCampaigns: async () => {
    set({ isLoading: true });
    try {
      const response = await axios.get('/campaigns/');
      set({ campaigns: response.data, isLoading: false });
    } catch (error) {
      set({ error: error.message, isLoading: false });
    }
  },

  getCampaign: async (id) => {
    set({ isLoading: true });
    try {
      const response = await axios.get(`/campaigns/${id}`);
      set({ currentCampaign: response.data, isLoading: false });
      return response.data;
    } catch (error) {
      set({ error: error.message, isLoading: false });
      return null;
    }
  },

  createCampaign: async (campaignData) => {
    set({ isLoading: true });
    try {
      const response = await axios.post('/campaigns/', campaignData);
      set((state) => ({
        campaigns: [...state.campaigns, response.data],
        isLoading: false
      }));
      return { success: true, data: response.data };
    } catch (error) {
      set({ error: error.message, isLoading: false });
      return { success: false, error: error.response?.data?.detail };
    }
  },

  updateCampaignStatus: async (id, status) => {
    try {
      await axios.patch(`/campaigns/${id}/status?status=${status}`);
      set((state) => ({
        campaigns: state.campaigns.map((c) =>
          c.id === id ? { ...c, status } : c
        )
      }));
      return { success: true };
    } catch (error) {
      return { success: false, error: error.response?.data?.detail };
    }
  }
}));

// Session Store
export const useSessionStore = create((set) => ({
  sessions: [],
  currentSession: null,
  isLoading: false,
  error: null,

  fetchSessions: async () => {
    set({ isLoading: true });
    try {
      const response = await axios.get('/sessions/');
      set({ sessions: response.data, isLoading: false });
    } catch (error) {
      set({ error: error.message, isLoading: false });
    }
  },

  createSession: async (campaignId) => {
    set({ isLoading: true });
    try {
      const response = await axios.post('/sessions/', { campaign_id: campaignId });
      set((state) => ({
        sessions: [...state.sessions, response.data],
        currentSession: response.data,
        isLoading: false
      }));
      return { success: true, data: response.data };
    } catch (error) {
      set({ error: error.message, isLoading: false });
      return { success: false, error: error.response?.data?.detail };
    }
  },

  completeSession: async (sessionId) => {
    try {
      await axios.post(`/sessions/${sessionId}/complete`);
      set((state) => ({
        sessions: state.sessions.map((s) =>
          s.id === sessionId ? { ...s, status: 'completed' } : s
        ),
        currentSession: null
      }));
      return { success: true };
    } catch (error) {
      return { success: false, error: error.response?.data?.detail };
    }
  },

  setCurrentSession: (session) => set({ currentSession: session })
}));

// Consent Store
export const useConsentStore = create((set) => ({
  consents: [],
  isLoading: false,
  error: null,

  fetchConsents: async () => {
    set({ isLoading: true });
    try {
      const response = await axios.get('/consents/my-consents');
      set({ consents: response.data, isLoading: false });
    } catch (error) {
      set({ error: error.message, isLoading: false });
    }
  },

  createConsent: async (campaignId, accepted) => {
    set({ isLoading: true });
    try {
      const response = await axios.post('/consents/', {
        campaign_id: campaignId,
        accepted
      });
      set((state) => ({
        consents: [...state.consents, response.data],
        isLoading: false
      }));
      return { success: true, data: response.data };
    } catch (error) {
      set({ error: error.message, isLoading: false });
      return { success: false, error: error.response?.data?.detail };
    }
  },

  hasConsent: (campaignId) => {
    const consents = useConsentStore.getState().consents;
    return consents.some(c => c.campaign_id === campaignId && c.accepted && !c.revoked_at);
  }
}));

// Chat Store
export const useChatStore = create((set) => ({
  messages: [],
  isLoading: false,
  error: null,

  fetchHistory: async (sessionId) => {
    set({ isLoading: true });
    try {
      const response = await axios.get(`/chat/history/${sessionId}`);
      set({ messages: response.data.messages || [], isLoading: false });
    } catch (error) {
      set({ error: error.message, isLoading: false });
    }
  },

  sendMessage: async (sessionId, message) => {
    set({ isLoading: true });
    try {
      // Add user message immediately
      const userMsg = { role: 'user', content: message, timestamp: new Date().toISOString() };
      set((state) => ({ messages: [...state.messages, userMsg] }));

      const response = await axios.post('/chat/message', {
        session_id: sessionId,
        message
      });

      // Add assistant response
      const assistantMsg = {
        role: 'assistant',
        content: response.data.message,
        timestamp: response.data.timestamp
      };
      set((state) => ({
        messages: [...state.messages, assistantMsg],
        isLoading: false
      }));

      return { success: true, data: response.data };
    } catch (error) {
      set({ isLoading: false, error: error.message });
      return { success: false, error: error.response?.data?.detail };
    }
  },

  clearMessages: () => set({ messages: [] })
}));

// Dashboard Store
export const useDashboardStore = create((set) => ({
  stats: null,
  isLoading: false,
  error: null,

  fetchStats: async () => {
    set({ isLoading: true });
    try {
      const response = await axios.get('/dashboard/stats');
      set({ stats: response.data, isLoading: false });
    } catch (error) {
      set({ error: error.message, isLoading: false });
    }
  }
}));
