import React, { useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuthStore, useDashboardStore, useCampaignStore } from '../stores';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Badge } from '../components/ui/badge';
import { Progress } from '../components/ui/progress';
import { 
  BarChart3, 
  Users, 
  MessageCircle, 
  FileCheck, 
  TrendingUp,
  ArrowRight,
  Play,
  Clock,
  CheckCircle2
} from 'lucide-react';

export const DashboardPage = () => {
  const navigate = useNavigate();
  const { user } = useAuthStore();
  const { stats, fetchStats, isLoading } = useDashboardStore();
  const { campaigns, fetchCampaigns } = useCampaignStore();

  useEffect(() => {
    fetchStats();
    fetchCampaigns();
  }, [fetchStats, fetchCampaigns]);

  const isAdmin = user?.role === 'admin' || user?.role === 'facilitator' || user?.role === 'analyst';

  const statCards = isAdmin && stats ? [
    {
      title: 'Campañas Activas',
      value: stats.campaigns?.active || 0,
      total: stats.campaigns?.total || 0,
      icon: BarChart3,
      color: 'text-orange-500',
      bgColor: 'bg-orange-50'
    },
    {
      title: 'Sesiones Completadas',
      value: stats.sessions?.completed || 0,
      total: stats.sessions?.total || 0,
      icon: MessageCircle,
      color: 'text-sky-500',
      bgColor: 'bg-sky-50'
    },
    {
      title: 'Usuarios Registrados',
      value: stats.users || 0,
      icon: Users,
      color: 'text-emerald-500',
      bgColor: 'bg-emerald-50'
    },
    {
      title: 'Consentimientos Activos',
      value: stats.active_consents || 0,
      icon: FileCheck,
      color: 'text-violet-500',
      bgColor: 'bg-violet-50'
    }
  ] : [];

  const activeCampaigns = campaigns.filter(c => c.status === 'active');

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

  return (
    <div className="space-y-8" data-testid="dashboard-page">
      {/* Welcome Section */}
      <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
        <div>
          <h1 className="text-3xl font-bold font-['Outfit'] tracking-tight">
            ¡Hola, {user?.full_name?.split(' ')[0]}!
          </h1>
          <p className="text-muted-foreground mt-1">
            {isAdmin 
              ? 'Aquí tienes un resumen de la actividad de DigiKawsay'
              : 'Bienvenido a tu espacio de diálogos facilitados'}
          </p>
        </div>
        {isAdmin && (
          <Button 
            onClick={() => navigate('/campaigns/new')}
            className="bg-secondary hover:bg-secondary/90 text-white"
            data-testid="new-campaign-btn"
          >
            Nueva Campaña
            <ArrowRight className="w-4 h-4 ml-2" />
          </Button>
        )}
      </div>

      {/* Stats Grid - Admin Only */}
      {isAdmin && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          {statCards.map((stat, index) => (
            <Card key={index} className="card-hover" data-testid={`stat-card-${index}`}>
              <CardContent className="p-6">
                <div className="flex items-start justify-between">
                  <div className={`p-3 rounded-xl ${stat.bgColor}`}>
                    <stat.icon className={`w-6 h-6 ${stat.color}`} />
                  </div>
                  {stat.total && (
                    <span className="text-sm text-muted-foreground">
                      de {stat.total}
                    </span>
                  )}
                </div>
                <div className="mt-4">
                  <p className="text-3xl font-bold font-['Outfit']">{stat.value}</p>
                  <p className="text-sm text-muted-foreground mt-1">{stat.title}</p>
                </div>
                {stat.total && (
                  <Progress 
                    value={(stat.value / stat.total) * 100} 
                    className="mt-3 h-1.5" 
                  />
                )}
              </CardContent>
            </Card>
          ))}
        </div>
      )}

      {/* Active Campaigns */}
      <div>
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-xl font-semibold font-['Outfit']">
            {isAdmin ? 'Campañas Recientes' : 'Campañas Disponibles'}
          </h2>
          <Button 
            variant="ghost" 
            onClick={() => navigate('/campaigns')}
            data-testid="view-all-campaigns"
          >
            Ver todas
            <ArrowRight className="w-4 h-4 ml-1" />
          </Button>
        </div>

        {activeCampaigns.length === 0 ? (
          <Card className="border-dashed">
            <CardContent className="flex flex-col items-center justify-center py-12">
              <div className="p-4 rounded-full bg-muted mb-4">
                <MessageCircle className="w-8 h-8 text-muted-foreground" />
              </div>
              <h3 className="font-medium text-lg">No hay campañas activas</h3>
              <p className="text-muted-foreground text-center mt-1 max-w-sm">
                {isAdmin 
                  ? 'Crea una nueva campaña para comenzar a recopilar insights'
                  : 'Pronto habrá nuevas campañas disponibles para participar'}
              </p>
              {isAdmin && (
                <Button 
                  className="mt-4 bg-secondary hover:bg-secondary/90 text-white"
                  onClick={() => navigate('/campaigns/new')}
                >
                  Crear Campaña
                </Button>
              )}
            </CardContent>
          </Card>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {activeCampaigns.slice(0, 6).map((campaign) => (
              <Card 
                key={campaign.id} 
                className="card-hover cursor-pointer"
                onClick={() => navigate(`/campaigns/${campaign.id}`)}
                data-testid={`campaign-card-${campaign.id}`}
              >
                <CardHeader className="pb-2">
                  <div className="flex items-start justify-between">
                    <CardTitle className="text-lg font-['Outfit'] line-clamp-1">
                      {campaign.name}
                    </CardTitle>
                    {getStatusBadge(campaign.status)}
                  </div>
                  <CardDescription className="line-clamp-2">
                    {campaign.objective}
                  </CardDescription>
                </CardHeader>
                <CardContent>
                  <div className="flex items-center gap-4 text-sm text-muted-foreground">
                    <div className="flex items-center gap-1">
                      <Users className="w-4 h-4" />
                      <span>{campaign.participant_count || 0}</span>
                    </div>
                    <div className="flex items-center gap-1">
                      <MessageCircle className="w-4 h-4" />
                      <span>{campaign.session_count || 0}</span>
                    </div>
                  </div>
                  <Button 
                    className="w-full mt-4"
                    variant="outline"
                    data-testid={`join-campaign-${campaign.id}`}
                  >
                    <Play className="w-4 h-4 mr-2" />
                    {isAdmin ? 'Ver Detalles' : 'Participar'}
                  </Button>
                </CardContent>
              </Card>
            ))}
          </div>
        )}
      </div>

      {/* Quick Actions for Participants */}
      {!isAdmin && (
        <Card className="bg-gradient-to-br from-slate-900 to-slate-800 text-white border-0">
          <CardContent className="p-8">
            <div className="flex flex-col md:flex-row items-center gap-6">
              <div className="p-4 rounded-2xl bg-orange-500/20">
                <MessageCircle className="w-10 h-10 text-orange-400" />
              </div>
              <div className="flex-1 text-center md:text-left">
                <h3 className="text-xl font-semibold font-['Outfit']">
                  ¿Listo para una conversación?
                </h3>
                <p className="text-slate-300 mt-1">
                  VAL está aquí para facilitar un diálogo reflexivo y confidencial
                </p>
              </div>
              <Button 
                className="bg-orange-500 hover:bg-orange-600 text-white"
                onClick={() => navigate('/campaigns')}
                data-testid="start-conversation-btn"
              >
                Ver Campañas
                <ArrowRight className="w-4 h-4 ml-2" />
              </Button>
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
};
