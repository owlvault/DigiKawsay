import React, { useEffect, useState } from 'react';
import { useAuthStore } from '../stores';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Badge } from '../components/ui/badge';
import { Progress } from '../components/ui/progress';
import { toast } from 'sonner';
import { Shield, Eye, EyeOff, RefreshCw, AlertTriangle, CheckCircle2 } from 'lucide-react';
import axios from 'axios';

export const PrivacyDashboard = () => {
  const { user } = useAuthStore();
  const [campaigns, setCampaigns] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchCampaigns();
  }, []);

  const fetchCampaigns = async () => {
    setLoading(true);
    try {
      const res = await axios.get('/campaigns/');
      const campaignsWithPrivacy = await Promise.all(
        res.data.map(async (campaign) => {
          try {
            const [suppressionRes, coverageRes] = await Promise.all([
              axios.get(`/privacy/suppression-status/${campaign.id}`),
              axios.get(`/campaigns/${campaign.id}/coverage`)
            ]);
            return {
              ...campaign,
              privacy: suppressionRes.data,
              coverage: coverageRes.data
            };
          } catch {
            return { ...campaign, privacy: null, coverage: null };
          }
        })
      );
      setCampaigns(campaignsWithPrivacy);
    } catch (error) {
      console.error('Error fetching campaigns:', error);
    }
    setLoading(false);
  };

  const handleTriggerSuppression = async (campaignId) => {
    try {
      const res = await axios.post(`/privacy/suppress/${campaignId}`);
      toast.success(`Supresión completada: ${res.data.suppressed_count} insights suprimidos`);
      fetchCampaigns();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Error al ejecutar supresión');
    }
  };

  if (user?.role !== 'admin' && user?.role !== 'facilitator') {
    return (
      <div className="flex items-center justify-center h-64">
        <Card className="max-w-md">
          <CardContent className="p-8 text-center">
            <Shield className="w-12 h-12 mx-auto mb-4 text-muted-foreground" />
            <h3 className="font-medium text-lg">Acceso Restringido</h3>
            <p className="text-muted-foreground mt-2">
              Solo administradores y facilitadores pueden ver el dashboard de privacidad
            </p>
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className="space-y-6" data-testid="privacy-dashboard">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold font-['Outfit'] tracking-tight">Privacidad</h1>
          <p className="text-muted-foreground mt-1">
            Dashboard de cumplimiento y protección de datos
          </p>
        </div>
        <Button variant="outline" onClick={fetchCampaigns}>
          <RefreshCw className="w-4 h-4 mr-2" />
          Actualizar
        </Button>
      </div>

      {/* Suppression Info */}
      <Card className="border-blue-200 bg-blue-50">
        <CardContent className="p-4 flex items-start gap-3">
          <Shield className="w-5 h-5 text-blue-600 mt-0.5" />
          <div>
            <p className="font-medium text-blue-900">Supresión de Grupos Pequeños</p>
            <p className="text-sm text-blue-700">
              Los insights con menos de 5 fuentes únicas son automáticamente suprimidos para 
              prevenir la identificación indirecta de participantes. Solo admin/security_officer 
              pueden ver insights suprimidos.
            </p>
          </div>
        </CardContent>
      </Card>

      {/* Campaigns Privacy Status */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {loading ? (
          <p className="text-muted-foreground">Cargando...</p>
        ) : campaigns.length === 0 ? (
          <Card className="col-span-2">
            <CardContent className="p-8 text-center">
              <p className="text-muted-foreground">No hay campañas</p>
            </CardContent>
          </Card>
        ) : (
          campaigns.map((campaign) => (
            <Card key={campaign.id}>
              <CardHeader className="pb-2">
                <div className="flex items-start justify-between">
                  <CardTitle className="font-['Outfit'] text-lg">{campaign.name}</CardTitle>
                  <Badge className={
                    campaign.status === 'active' ? 'bg-green-100 text-green-700' : 'bg-slate-100 text-slate-700'
                  }>
                    {campaign.status}
                  </Badge>
                </div>
              </CardHeader>
              <CardContent className="space-y-4">
                {campaign.privacy ? (
                  <>
                    <div className="grid grid-cols-3 gap-2 text-center">
                      <div className="p-2 bg-slate-50 rounded">
                        <p className="text-xl font-bold">{campaign.privacy.total_insights}</p>
                        <p className="text-xs text-muted-foreground">Total Insights</p>
                      </div>
                      <div className="p-2 bg-green-50 rounded">
                        <p className="text-xl font-bold text-green-700">{campaign.privacy.visible_insights}</p>
                        <p className="text-xs text-muted-foreground">Visibles</p>
                      </div>
                      <div className="p-2 bg-orange-50 rounded">
                        <p className="text-xl font-bold text-orange-700">{campaign.privacy.suppressed_insights}</p>
                        <p className="text-xs text-muted-foreground">Suprimidos</p>
                      </div>
                    </div>

                    <div className="space-y-1">
                      <div className="flex justify-between text-sm">
                        <span>Cobertura de supresión</span>
                        <span>
                          {campaign.privacy.total_insights > 0 
                            ? Math.round((campaign.privacy.suppressed_insights / campaign.privacy.total_insights) * 100)
                            : 0}%
                        </span>
                      </div>
                      <Progress 
                        value={campaign.privacy.total_insights > 0 
                          ? (campaign.privacy.suppressed_insights / campaign.privacy.total_insights) * 100 
                          : 0} 
                        className="h-2"
                      />
                    </div>

                    <div className="flex items-center gap-2 text-sm">
                      {campaign.privacy.suppressed_insights > 0 ? (
                        <>
                          <EyeOff className="w-4 h-4 text-orange-500" />
                          <span className="text-orange-700">
                            {campaign.privacy.suppressed_insights} insights ocultos por privacidad
                          </span>
                        </>
                      ) : (
                        <>
                          <CheckCircle2 className="w-4 h-4 text-green-500" />
                          <span className="text-green-700">Todos los insights son visibles</span>
                        </>
                      )}
                    </div>

                    <Button 
                      variant="outline" 
                      size="sm" 
                      className="w-full"
                      onClick={() => handleTriggerSuppression(campaign.id)}
                    >
                      <RefreshCw className="w-4 h-4 mr-2" />
                      Re-evaluar Supresión
                    </Button>
                  </>
                ) : (
                  <p className="text-sm text-muted-foreground">No hay datos de privacidad disponibles</p>
                )}
              </CardContent>
            </Card>
          ))
        )}
      </div>

      {/* Privacy Guidelines */}
      <Card>
        <CardHeader>
          <CardTitle className="font-['Outfit']">Controles de Privacidad Implementados</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="flex items-start gap-3 p-3 bg-slate-50 rounded-lg">
              <CheckCircle2 className="w-5 h-5 text-green-600 mt-0.5" />
              <div>
                <p className="font-medium">Pseudonimización</p>
                <p className="text-sm text-muted-foreground">
                  Emails, teléfonos y nombres son reemplazados antes del análisis
                </p>
              </div>
            </div>
            <div className="flex items-start gap-3 p-3 bg-slate-50 rounded-lg">
              <CheckCircle2 className="w-5 h-5 text-green-600 mt-0.5" />
              <div>
                <p className="font-medium">PII Vault Separado</p>
                <p className="text-sm text-muted-foreground">
                  Mapeo identity-pseudonym almacenado de forma segura
                </p>
              </div>
            </div>
            <div className="flex items-start gap-3 p-3 bg-slate-50 rounded-lg">
              <CheckCircle2 className="w-5 h-5 text-green-600 mt-0.5" />
              <div>
                <p className="font-medium">Supresión Grupos Pequeños</p>
                <p className="text-sm text-muted-foreground">
                  Threshold de {5} fuentes mínimas para visibilidad
                </p>
              </div>
            </div>
            <div className="flex items-start gap-3 p-3 bg-slate-50 rounded-lg">
              <CheckCircle2 className="w-5 h-5 text-green-600 mt-0.5" />
              <div>
                <p className="font-medium">Control Dual de Reidentificación</p>
                <p className="text-sm text-muted-foreground">
                  Requiere solicitud + aprobación de Data Steward
                </p>
              </div>
            </div>
            <div className="flex items-start gap-3 p-3 bg-slate-50 rounded-lg">
              <CheckCircle2 className="w-5 h-5 text-green-600 mt-0.5" />
              <div>
                <p className="font-medium">Auditoría Completa</p>
                <p className="text-sm text-muted-foreground">
                  Todo acceso a datos sensibles es registrado
                </p>
              </div>
            </div>
            <div className="flex items-start gap-3 p-3 bg-slate-50 rounded-lg">
              <CheckCircle2 className="w-5 h-5 text-green-600 mt-0.5" />
              <div>
                <p className="font-medium">Transcripciones Restringidas</p>
                <p className="text-sm text-muted-foreground">
                  Solo admin/security_officer pueden ver transcripciones
                </p>
              </div>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
};
