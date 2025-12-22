import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuthStore, useCampaignStore, useConsentStore } from '../stores';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Badge } from '../components/ui/badge';
import { 
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '../components/ui/dialog';
import { Checkbox } from '../components/ui/checkbox';
import { Label } from '../components/ui/label';
import { toast } from 'sonner';
import { 
  Search, 
  Plus, 
  Users, 
  MessageCircle, 
  Calendar,
  Filter,
  Play,
  Settings,
  Shield
} from 'lucide-react';

export const CampaignsPage = () => {
  const navigate = useNavigate();
  const { user } = useAuthStore();
  const { campaigns, fetchCampaigns, isLoading } = useCampaignStore();
  const { consents, fetchConsents, createConsent } = useConsentStore();
  
  const [searchTerm, setSearchTerm] = useState('');
  const [statusFilter, setStatusFilter] = useState('all');
  const [consentDialog, setConsentDialog] = useState({ open: false, campaign: null });
  const [consentAccepted, setConsentAccepted] = useState(false);

  const isAdmin = user?.role === 'admin' || user?.role === 'facilitator';

  useEffect(() => {
    fetchCampaigns();
    fetchConsents();
  }, [fetchCampaigns, fetchConsents]);

  const hasConsent = (campaignId) => {
    return consents.some(c => c.campaign_id === campaignId && c.accepted && !c.revoked_at);
  };

  const filteredCampaigns = campaigns.filter(campaign => {
    const matchesSearch = campaign.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
                          campaign.objective?.toLowerCase().includes(searchTerm.toLowerCase());
    const matchesStatus = statusFilter === 'all' || campaign.status === statusFilter;
    
    // Non-admin users only see active campaigns
    if (!isAdmin && campaign.status !== 'active') return false;
    
    return matchesSearch && matchesStatus;
  });

  const getStatusBadge = (status) => {
    const styles = {
      active: 'bg-green-100 text-green-700 border-green-200',
      draft: 'bg-slate-100 text-slate-700 border-slate-200',
      paused: 'bg-yellow-100 text-yellow-700 border-yellow-200',
      closed: 'bg-red-100 text-red-700 border-red-200'
    };
    const labels = {
      active: 'Activa',
      draft: 'Borrador',
      paused: 'Pausada',
      closed: 'Cerrada'
    };
    return <Badge className={styles[status]}>{labels[status]}</Badge>;
  };

  const handleCampaignClick = (campaign) => {
    if (isAdmin) {
      navigate(`/campaigns/${campaign.id}`);
    } else {
      // Check if user has consent
      if (hasConsent(campaign.id)) {
        navigate(`/chat/${campaign.id}`);
      } else {
        setConsentDialog({ open: true, campaign });
      }
    }
  };

  const handleAcceptConsent = async () => {
    if (!consentAccepted) {
      toast.error('Debes aceptar los términos para continuar');
      return;
    }

    const result = await createConsent(consentDialog.campaign.id, true);
    if (result.success) {
      toast.success('¡Consentimiento registrado!');
      setConsentDialog({ open: false, campaign: null });
      setConsentAccepted(false);
      navigate(`/chat/${consentDialog.campaign.id}`);
    } else {
      toast.error(result.error || 'Error al registrar consentimiento');
    }
  };

  return (
    <div className="space-y-6" data-testid="campaigns-page">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
        <div>
          <h1 className="text-3xl font-bold font-['Outfit'] tracking-tight">Campañas</h1>
          <p className="text-muted-foreground mt-1">
            {isAdmin ? 'Gestiona y monitorea tus campañas de diálogo' : 'Explora las campañas disponibles para participar'}
          </p>
        </div>
        {isAdmin && (
          <Button 
            onClick={() => navigate('/campaigns/new')}
            className="bg-secondary hover:bg-secondary/90 text-white"
            data-testid="create-campaign-btn"
          >
            <Plus className="w-4 h-4 mr-2" />
            Nueva Campaña
          </Button>
        )}
      </div>

      {/* Search and Filters */}
      <div className="flex flex-col md:flex-row gap-4">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
          <Input
            placeholder="Buscar campañas..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="pl-10"
            data-testid="search-campaigns"
          />
        </div>
        {isAdmin && (
          <div className="flex gap-2">
            {['all', 'active', 'draft', 'paused', 'closed'].map((status) => (
              <Button
                key={status}
                variant={statusFilter === status ? 'default' : 'outline'}
                size="sm"
                onClick={() => setStatusFilter(status)}
                data-testid={`filter-${status}`}
              >
                {status === 'all' ? 'Todas' : 
                 status === 'active' ? 'Activas' :
                 status === 'draft' ? 'Borrador' :
                 status === 'paused' ? 'Pausadas' : 'Cerradas'}
              </Button>
            ))}
          </div>
        )}
      </div>

      {/* Campaigns Grid */}
      {filteredCampaigns.length === 0 ? (
        <Card className="border-dashed">
          <CardContent className="flex flex-col items-center justify-center py-16">
            <div className="p-4 rounded-full bg-muted mb-4">
              <MessageCircle className="w-8 h-8 text-muted-foreground" />
            </div>
            <h3 className="font-medium text-lg">No se encontraron campañas</h3>
            <p className="text-muted-foreground text-center mt-1 max-w-sm">
              {searchTerm 
                ? 'Intenta con otros términos de búsqueda' 
                : isAdmin 
                  ? 'Crea tu primera campaña para comenzar' 
                  : 'Pronto habrá campañas disponibles'}
            </p>
          </CardContent>
        </Card>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {filteredCampaigns.map((campaign) => (
            <Card 
              key={campaign.id} 
              className="card-hover cursor-pointer group"
              onClick={() => handleCampaignClick(campaign)}
              data-testid={`campaign-${campaign.id}`}
            >
              <CardHeader className="pb-2">
                <div className="flex items-start justify-between">
                  <CardTitle className="text-lg font-['Outfit'] line-clamp-1 group-hover:text-orange-500 transition-colors">
                    {campaign.name}
                  </CardTitle>
                  {getStatusBadge(campaign.status)}
                </div>
                <CardDescription className="line-clamp-2 min-h-[40px]">
                  {campaign.objective || 'Sin descripción'}
                </CardDescription>
              </CardHeader>
              <CardContent>
                <div className="flex items-center gap-4 text-sm text-muted-foreground mb-4">
                  <div className="flex items-center gap-1.5">
                    <Users className="w-4 h-4" />
                    <span>{campaign.participant_count || 0} participantes</span>
                  </div>
                  <div className="flex items-center gap-1.5">
                    <MessageCircle className="w-4 h-4" />
                    <span>{campaign.session_count || 0} sesiones</span>
                  </div>
                </div>
                
                <div className="flex gap-2">
                  {isAdmin ? (
                    <>
                      <Button variant="outline" className="flex-1" size="sm">
                        <Settings className="w-4 h-4 mr-1" />
                        Gestionar
                      </Button>
                    </>
                  ) : (
                    <Button 
                      className="flex-1 bg-primary hover:bg-primary/90" 
                      size="sm"
                      disabled={campaign.status !== 'active'}
                    >
                      {hasConsent(campaign.id) ? (
                        <>
                          <Play className="w-4 h-4 mr-1" />
                          Continuar
                        </>
                      ) : (
                        <>
                          <Shield className="w-4 h-4 mr-1" />
                          Participar
                        </>
                      )}
                    </Button>
                  )}
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}

      {/* Consent Dialog */}
      <Dialog open={consentDialog.open} onOpenChange={(open) => {
        setConsentDialog({ open, campaign: open ? consentDialog.campaign : null });
        if (!open) setConsentAccepted(false);
      }}>
        <DialogContent className="max-w-lg" data-testid="consent-dialog">
          <DialogHeader>
            <DialogTitle className="font-['Outfit'] text-xl">
              Consentimiento de Participación
            </DialogTitle>
            <DialogDescription>
              Antes de participar en "{consentDialog.campaign?.name}", por favor lee y acepta los términos.
            </DialogDescription>
          </DialogHeader>
          
          <div className="space-y-4 py-4">
            <div className="p-4 bg-slate-50 rounded-lg text-sm space-y-3">
              <p><strong>Propósito:</strong> Esta campaña recopila diálogos para análisis organizacional.</p>
              <p><strong>Confidencialidad:</strong> Tus respuestas serán anonimizadas y nunca se usarán para evaluación individual.</p>
              <p><strong>Uso de datos:</strong> Los insights agregados se utilizarán únicamente para mejorar la cultura organizacional.</p>
              <p><strong>Voluntariedad:</strong> Tu participación es completamente voluntaria y puedes revocar tu consentimiento en cualquier momento.</p>
            </div>

            <div className="flex items-start gap-3">
              <Checkbox 
                id="consent-accept"
                checked={consentAccepted}
                onCheckedChange={setConsentAccepted}
                data-testid="consent-checkbox"
              />
              <Label htmlFor="consent-accept" className="text-sm leading-relaxed cursor-pointer">
                Acepto participar en esta campaña de diálogo y autorizo el uso de mis respuestas 
                de forma anonimizada para fines de análisis organizacional.
              </Label>
            </div>
          </div>

          <DialogFooter>
            <Button 
              variant="outline" 
              onClick={() => setConsentDialog({ open: false, campaign: null })}
            >
              Cancelar
            </Button>
            <Button 
              onClick={handleAcceptConsent}
              className="bg-secondary hover:bg-secondary/90 text-white"
              data-testid="accept-consent-btn"
            >
              <Shield className="w-4 h-4 mr-2" />
              Aceptar y Continuar
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
};
