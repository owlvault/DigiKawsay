import React, { useEffect } from "react";
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { Toaster } from "./components/ui/sonner";
import { useAuthStore } from "./stores";

// Pages
import { LoginPage } from "./pages/LoginPage";
import { DashboardPage } from "./pages/DashboardPage";
import { CampaignsPage } from "./pages/CampaignsPage";
import { CreateCampaignPage } from "./pages/CreateCampaignPage";
import { ChatPage } from "./pages/ChatPage";

// Components
import { Layout } from "./components/Layout";

// Protected Route Component
const ProtectedRoute = ({ children }) => {
  const { isAuthenticated, initAuth } = useAuthStore();
  
  useEffect(() => {
    initAuth();
  }, [initAuth]);

  if (!isAuthenticated) {
    return <Navigate to="/login" replace />;
  }

  return <Layout>{children}</Layout>;
};

function App() {
  return (
    <div className="App">
      <BrowserRouter>
        <Routes>
          {/* Public Routes */}
          <Route path="/login" element={<LoginPage />} />
          
          {/* Protected Routes */}
          <Route
            path="/dashboard"
            element={
              <ProtectedRoute>
                <DashboardPage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/campaigns"
            element={
              <ProtectedRoute>
                <CampaignsPage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/campaigns/new"
            element={
              <ProtectedRoute>
                <CreateCampaignPage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/campaigns/:id"
            element={
              <ProtectedRoute>
                <CampaignsPage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/chat/:campaignId"
            element={
              <ProtectedRoute>
                <ChatPage />
              </ProtectedRoute>
            }
          />
          
          {/* Placeholder routes for future phases */}
          <Route
            path="/insights"
            element={
              <ProtectedRoute>
                <div className="text-center py-12">
                  <h2 className="text-2xl font-bold font-['Outfit']">RunaCultur - Hallazgos</h2>
                  <p className="text-muted-foreground mt-2">Disponible en Fase 3</p>
                </div>
              </ProtectedRoute>
            }
          />
          <Route
            path="/network"
            element={
              <ProtectedRoute>
                <div className="text-center py-12">
                  <h2 className="text-2xl font-bold font-['Outfit']">RunaMap - Análisis de Red</h2>
                  <p className="text-muted-foreground mt-2">Disponible en Fase 4</p>
                </div>
              </ProtectedRoute>
            }
          />
          <Route
            path="/roadmap"
            element={
              <ProtectedRoute>
                <div className="text-center py-12">
                  <h2 className="text-2xl font-bold font-['Outfit']">RunaFlow - Roadmap</h2>
                  <p className="text-muted-foreground mt-2">Disponible en Fase 5</p>
                </div>
              </ProtectedRoute>
            }
          />
          <Route
            path="/governance"
            element={
              <ProtectedRoute>
                <div className="text-center py-12">
                  <h2 className="text-2xl font-bold font-['Outfit']">RunaData - Gobernanza</h2>
                  <p className="text-muted-foreground mt-2">Disponible en Fase 5</p>
                </div>
              </ProtectedRoute>
            }
          />
          
          {/* Default redirect */}
          <Route path="/" element={<Navigate to="/dashboard" replace />} />
          <Route path="*" element={<Navigate to="/dashboard" replace />} />
        </Routes>
      </BrowserRouter>
      <Toaster position="top-right" richColors />
    </div>
  );
}

export default App;
