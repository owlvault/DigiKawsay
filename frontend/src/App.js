import React, { useEffect } from "react";
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { Toaster } from "./components/ui/sonner";
import { useAuthStore } from "./stores";

// Pages
import { LoginPage } from "./pages/LoginPage";
import { DashboardPage } from "./pages/DashboardPage";
import { CampaignsPage } from "./pages/CampaignsPage";
import { CreateCampaignPage } from "./pages/CreateCampaignPage";
import { CampaignDetailPage } from "./pages/CampaignDetailPage";
import { ChatPage } from "./pages/ChatPage";
import { ScriptsPage } from "./pages/ScriptsPage";
import { ScriptEditorPage } from "./pages/ScriptEditorPage";
import { InsightsPage } from "./pages/InsightsPage";
import { CreateInsightPage } from "./pages/CreateInsightPage";
import { TaxonomyPage } from "./pages/TaxonomyPage";

// Phase 3.5 - Compliance Pages
import { AuditPage } from "./pages/AuditPage";
import { PrivacyDashboard } from "./pages/PrivacyDashboard";
import { ReidentificationPage } from "./pages/ReidentificationPage";

// Phase 4 - RunaMap
import { RunaMapPage } from "./pages/RunaMapPage";

// Phase 5 - RunaFlow
import { RunaFlowPage } from "./pages/RunaFlowPage";
import { RitualsPage } from "./pages/RitualsPage";

// Phase 6 - RunaData
import { GovernancePage } from "./pages/GovernancePage";

// Phase 7 - Observability
import { ObservabilityPage } from "./pages/ObservabilityPage";

// Phase 8 - User Administration
import { UsersAdminPage } from "./pages/UsersAdminPage";

// Components
import { Layout } from "./components/Layout";

const ProtectedRoute = ({ children }) => {
  const { isAuthenticated, initAuth } = useAuthStore();
  useEffect(() => { initAuth(); }, [initAuth]);
  if (!isAuthenticated) return <Navigate to="/login" replace />;
  return <Layout>{children}</Layout>;
};

function App() {
  return (
    <div className="App">
      <BrowserRouter>
        <Routes>
          <Route path="/login" element={<LoginPage />} />
          
          <Route path="/dashboard" element={<ProtectedRoute><DashboardPage /></ProtectedRoute>} />
          <Route path="/campaigns" element={<ProtectedRoute><CampaignsPage /></ProtectedRoute>} />
          <Route path="/campaigns/new" element={<ProtectedRoute><CreateCampaignPage /></ProtectedRoute>} />
          <Route path="/campaigns/:campaignId" element={<ProtectedRoute><CampaignDetailPage /></ProtectedRoute>} />
          <Route path="/chat/:campaignId" element={<ProtectedRoute><ChatPage /></ProtectedRoute>} />
          
          <Route path="/scripts" element={<ProtectedRoute><ScriptsPage /></ProtectedRoute>} />
          <Route path="/scripts/new" element={<ProtectedRoute><ScriptEditorPage /></ProtectedRoute>} />
          <Route path="/scripts/:scriptId" element={<ProtectedRoute><ScriptEditorPage /></ProtectedRoute>} />
          
          {/* Phase 3 - Insights */}
          <Route path="/insights/:campaignId" element={<ProtectedRoute><InsightsPage /></ProtectedRoute>} />
          <Route path="/insights/:campaignId/new" element={<ProtectedRoute><CreateInsightPage /></ProtectedRoute>} />
          <Route path="/taxonomy" element={<ProtectedRoute><TaxonomyPage /></ProtectedRoute>} />
          
          {/* Phase 3.5 - Compliance & Privacy */}
          <Route path="/audit" element={<ProtectedRoute><AuditPage /></ProtectedRoute>} />
          <Route path="/privacy" element={<ProtectedRoute><PrivacyDashboard /></ProtectedRoute>} />
          <Route path="/reidentification" element={<ProtectedRoute><ReidentificationPage /></ProtectedRoute>} />
          
          {/* Phase 4 - RunaMap */}
          <Route path="/network" element={<ProtectedRoute><RunaMapPage /></ProtectedRoute>} />
          
          {/* Phase 5 - RunaFlow */}
          <Route path="/roadmap" element={<ProtectedRoute><RunaFlowPage /></ProtectedRoute>} />
          <Route path="/rituals" element={<ProtectedRoute><RitualsPage /></ProtectedRoute>} />
          
          {/* Phase 6 - RunaData */}
          <Route path="/governance" element={<ProtectedRoute><GovernancePage /></ProtectedRoute>} />
          
          {/* Phase 7 - Observability */}
          <Route path="/observability" element={<ProtectedRoute><ObservabilityPage /></ProtectedRoute>} />
          
          {/* Phase 8 - User Administration */}
          <Route path="/users" element={<ProtectedRoute><UsersAdminPage /></ProtectedRoute>} />
          
          {/* Placeholder routes */}
          <Route path="/insights" element={<ProtectedRoute>
            <div className="text-center py-12">
              <h2 className="text-2xl font-bold font-['Outfit']">RunaCultur - Hallazgos</h2>
              <p className="text-muted-foreground mt-2">Selecciona una campaña para ver sus hallazgos</p>
            </div>
          </ProtectedRoute>} />
          
          <Route path="/" element={<Navigate to="/dashboard" replace />} />
          <Route path="*" element={<Navigate to="/dashboard" replace />} />
        </Routes>
      </BrowserRouter>
      <Toaster position="top-right" richColors />
    </div>
  );
}

export default App;
