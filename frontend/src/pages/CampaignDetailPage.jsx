import React, { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useAuthStore, useCampaignStore, useScriptStore, useInviteStore, useUsersStore } from '../stores';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Badge } from '../components/ui/badge';
import { Progress } from '../components/ui/progress';
import { Input } from '../components/ui/input';
import { Textarea } from '../components/ui/textarea';
import { Label } from '../components/ui/label';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../components/ui/tabs';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../components/ui/select';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '../components/ui/dialog';
import { toast } from 'sonner';
import { 
  ArrowLeft, 
  Settings,
  Users,
  MessageCircle,
  BarChart3,
  Mail,
  Play,
  Pause,
  CheckCircle2,
  Send,
  UserPlus,
  FileText,
  Target,
  Clock,
  TrendingUp
} from 'lucide-react';

export const CampaignDetailPage = () => {
  const { campaignId } = useParams();
  const navigate = useNavigate();
  const { user } = useAuthStore();
  const { currentCampaign, getCampaign, updateCampaign, updateCampaignStatus, getCoverage, coverage, isLoading } = useCampaignStore();
  const { scripts, fetchScripts } = useScriptStore();
  const { invites, fetchCampaignInvites, createBulkInvites } = useInviteStore();
  const { users, fetchUsers } = useUsersStore();

  const [inviteDialog, setInviteDialog] = useState(false);
  const [inviteEmails, setInviteEmails] = useState('');
  const [inviteMessage, setInviteMessage] = useState('');
  const [selectedUsers, setSelectedUsers] = useState([]);
  const [editMode, setEditMode] = useState(false);
  const [editData, setEditData] = useState({});

  const isAdmin = user?.role === 'admin' || user?.role === 'facilitator';

  useEffect(() => {
    loadData();
  }, [campaignId]);

  const loadData = async () => {
    await getCampaign(campaignId);
    await getCoverage(campaignId);
    await fetchCampaignInvites(campaignId);
    await fetchScripts();
    await fetchUsers();
  };

  useEffect(() => {
    if (currentCampaign) {
      setEditData({
        name: currentCampaign.name,
        description: currentCampaign.description,
        objective: currentCampaign.objective,
        script_id: currentCampaign.script_id,
        target_participants: currentCampaign.target_participants
      });
    }
  }, [currentCampaign]);

  const handleStatusChange = async (newStatus) => {
    const result = await updateCampaignStatus(campaignId, newStatus);
    if (result.success) {
      toast.success(`Campaña ${newStatus === 'active' ? 'activada' : newStatus === 'paused' ? 'pausada' : 'cerrada'}`);
    } else {
      toast.error(result.error || 'Error al cambiar estado');
    }
  };

  const handleSaveChanges = async () => {
    const result = await updateCampaign(campaignId, editData);
    if (result.success) {
      toast.success('Campaña actualizada');
      setEditMode(false);
    } else {
      toast.error(result.error || 'Error al guardar');
    }
  };

  const handleSendInvites = async () => {
    const emails = inviteEmails.split(/[\n,;]/).map(e => e.trim()).filter(e => e);
    
    if (emails.length === 0 && selectedUsers.length === 0) {
      toast.error('Agrega al menos un email o usuario');
      return;
    }

    const result = await createBulkInvites({
      campaign_id: campaignId,
      emails,
      user_ids: selectedUsers,
      message: inviteMessage
    });

    if (result.success) {
      toast.success(`${result.data.created} invitaciones enviadas`);
      setInviteDialog(false);
      setInviteEmails('');
      setSelectedUsers([]);
      fetchCampaignInvites(campaignId);
      getCoverage(campaignId);
    } else {
      toast.error(result.error || 'Error al enviar invitaciones');
    }
  };

  const getStatusBadge = (status) => {
    const styles = {
      active: 'bg-green-100 text-green-700',
      draft: 'bg-slate-100 text-slate-700',
      paused: 'bg-yellow-100 text-yellow-700',
      closed: 'bg-red-100 text-red-700'
    };
    const labels = {
      active: 'Activa',
      draft: 'Borrador',
      paused: 'Pausada',
      closed: 'Cerrada'
    };
    return <Badge className={styles[status]}>{labels[status]}</Badge>;
  };

  if (!currentCampaign) {
    return (
      <div className="flex items-center justify-center h-64">
        <p className="text-muted-foreground">Cargando...</p>
      </div>
    );
  }

  const participationRate = coverage?.participation_rate || 0;
  const completionRate = coverage?.completion_rate || 0;

  return (
    <div className="space-y-6" data-testid="campaign-detail-page">
      {/* Header */}
      <div className="flex items-start justify-between">
        <div className="flex items-center gap-4">
          <Button 
            variant="ghost" 
            size="icon"
            onClick={() => navigate('/campaigns')}
          >
            <ArrowLeft className="w-5 h-5" />
          </Button>
          <div>
            <div className="flex items-center gap-3">
              <h1 className="text-3xl font-bold font-['Outfit'] tracking-tight">
                {currentCampaign.name}
              </h1>
              {getStatusBadge(currentCampaign.status)}
            </div>
            <p className="text-muted-foreground mt-1">{currentCampaign.objective}</p>
          </div>
        </div>
        
        {isAdmin && (
          <div className="flex gap-2">
            {currentCampaign.status === 'draft' && (
              <Button 
                onClick={() => handleStatusChange('active')}
                className="bg-green-600 hover:bg-green-700 text-white"
              >
                <Play className="w-4 h-4 mr-2" />
                Activar
              </Button>
            )}
            {currentCampaign.status === 'active' && (
              <Button 
                variant="outline"
                onClick={() => handleStatusChange('paused')}
              >
                <Pause className="w-4 h-4 mr-2" />
                Pausar
              </Button>
            )}
            {currentCampaign.status === 'paused' && (
              <>
                <Button 
                  onClick={() => handleStatusChange('active')}
                  className="bg-green-600 hover:bg-green-700 text-white"
                >
                  <Play className="w-4 h-4 mr-2" />
                  Reanudar
                </Button>
                <Button 
                  variant="outline"
                  onClick={() => handleStatusChange('closed')}
                  className="text-red-600"
                >
                  <CheckCircle2 className="w-4 h-4 mr-2" />
                  Cerrar
                </Button>
              </>
            )}
          </div>
        )}
      </div>

      {/* Stats Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <Card>
          <CardContent className="p-4">
            <div className="flex items-center gap-3">
              <div className="p-2 rounded-lg bg-blue-50">
                <Mail className="w-5 h-5 text-blue-500" />
              </div>
              <div>
                <p className="text-2xl font-bold">{coverage?.total_invited || 0}</p>
                <p className="text-xs text-muted-foreground">Invitados</p>
              </div>
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-4">
            <div className="flex items-center gap-3">
              <div className="p-2 rounded-lg bg-green-50">
                <Users className="w-5 h-5 text-green-500" />
              </div>
              <div>
                <p className="text-2xl font-bold">{coverage?.total_consented || 0}</p>
                <p className="text-xs text-muted-foreground">Participantes</p>
              </div>
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-4">
            <div className="flex items-center gap-3">
              <div className="p-2 rounded-lg bg-orange-50">
                <MessageCircle className="w-5 h-5 text-orange-500" />
              </div>
              <div>
                <p className="text-2xl font-bold">{coverage?.total_sessions || 0}</p>
                <p className="text-xs text-muted-foreground">Sesiones</p>
              </div>
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-4">
            <div className="flex items-center gap-3">
              <div className="p-2 rounded-lg bg-violet-50">
                <CheckCircle2 className="w-5 h-5 text-violet-500" />
              </div>
              <div>
                <p className="text-2xl font-bold">{coverage?.completed_sessions || 0}</p>
                <p className="text-xs text-muted-foreground">Completadas</p>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Coverage Progress */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2 font-['Outfit']">
            <TrendingUp className="w-5 h-5 text-orange-500" />
            Cobertura de Campaña
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div className="space-y-2">
              <div className="flex justify-between text-sm">
                <span>Tasa de Participación</span>
                <span className="font-medium">{participationRate}%</span>
              </div>
              <Progress value={participationRate} className="h-2" />
              <p className="text-xs text-muted-foreground">
                {coverage?.total_consented || 0} de {coverage?.total_invited || 0} invitados han dado consentimiento
              </p>
            </div>
            <div className="space-y-2">
              <div className="flex justify-between text-sm">
                <span>Tasa de Completitud</span>
                <span className="font-medium">{completionRate}%</span>
              </div>
              <Progress value={completionRate} className="h-2" />
              <p className="text-xs text-muted-foreground">
                {coverage?.completed_sessions || 0} de {coverage?.total_sessions || 0} sesiones completadas
              </p>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Tabs */}
      <Tabs defaultValue="config" className="w-full">
        <TabsList>
          <TabsTrigger value="config" className="flex items-center gap-2">
            <Settings className="w-4 h-4" />
            Configuración
          </TabsTrigger>
          <TabsTrigger value="invites" className="flex items-center gap-2">
            <UserPlus className="w-4 h-4" />
            Invitaciones ({invites.length})
          </TabsTrigger>
        </TabsList>

        <TabsContent value="config" className="mt-4">
          <Card>
            <CardHeader>
              <div className="flex items-center justify-between">
                <CardTitle className="font-['Outfit']">Configuración de Campaña</CardTitle>
                {isAdmin && !editMode && (
                  <Button variant="outline" size="sm" onClick={() => setEditMode(true)}>
                    Editar
                  </Button>
                )}
              </div>
            </CardHeader>
            <CardContent className="space-y-4">
              {editMode ? (
                <>
                  <div className="space-y-2">
                    <Label>Nombre</Label>
                    <Input
                      value={editData.name || ''}
                      onChange={(e) => setEditData({ ...editData, name: e.target.value })}
                    />
                  </div>
                  <div className="space-y-2">
                    <Label>Descripción</Label>
                    <Textarea
                      value={editData.description || ''}
                      onChange={(e) => setEditData({ ...editData, description: e.target.value })}
                      rows={2}
                    />
                  </div>
                  <div className="space-y-2">
                    <Label>Objetivo</Label>
                    <Textarea
                      value={editData.objective || ''}
                      onChange={(e) => setEditData({ ...editData, objective: e.target.value })}
                      rows={3}
                    />
                  </div>
                  <div className="grid grid-cols-2 gap-4">
                    <div className="space-y-2">
                      <Label>Guión Asociado</Label>
                      <Select
                        value={editData.script_id || ''}
                        onValueChange={(value) => setEditData({ ...editData, script_id: value })}
                      >
                        <SelectTrigger>
                          <SelectValue placeholder="Seleccionar guión" />
                        </SelectTrigger>
                        <SelectContent>
                          <SelectItem value="">Sin guión</SelectItem>
                          {scripts.map((script) => (
                            <SelectItem key={script.id} value={script.id}>
                              {script.name}
                            </SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                    </div>
                    <div className="space-y-2">
                      <Label>Meta de Participantes</Label>
                      <Input
                        type="number"
                        min={0}
                        value={editData.target_participants || 0}
                        onChange={(e) => setEditData({ ...editData, target_participants: parseInt(e.target.value) || 0 })}
                      />
                    </div>
                  </div>
                  <div className="flex gap-2 pt-4">
                    <Button onClick={handleSaveChanges} disabled={isLoading}>
                      Guardar Cambios
                    </Button>
                    <Button variant="outline" onClick={() => setEditMode(false)}>
                      Cancelar
                    </Button>
                  </div>
                </>
              ) : (
                <div className="space-y-4">
                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <p className="text-sm text-muted-foreground">Guión</p>
                      <p className="font-medium">
                        {scripts.find(s => s.id === currentCampaign.script_id)?.name || 'Sin guión asignado'}
                      </p>
                    </div>
                    <div>
                      <p className="text-sm text-muted-foreground">Meta de Participantes</p>
                      <p className="font-medium">{currentCampaign.target_participants || 'No definida'}</p>
                    </div>
                  </div>
                  <div>
                    <p className="text-sm text-muted-foreground">Descripción</p>
                    <p>{currentCampaign.description || 'Sin descripción'}</p>
                  </div>
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="invites" className="mt-4">
          <Card>
            <CardHeader>
              <div className="flex items-center justify-between">
                <CardTitle className="font-['Outfit']">Invitaciones</CardTitle>
                {isAdmin && (
                  <Button 
                    onClick={() => setInviteDialog(true)}
                    className="bg-secondary hover:bg-secondary/90 text-white"
                  >
                    <Send className="w-4 h-4 mr-2" />
                    Enviar Invitaciones
                  </Button>
                )}
              </div>
            </CardHeader>
            <CardContent>
              {invites.length === 0 ? (
                <div className="text-center py-8 text-muted-foreground">
                  <Mail className="w-10 h-10 mx-auto mb-2 opacity-50" />
                  <p>No hay invitaciones enviadas</p>
                </div>
              ) : (
                <div className="space-y-2">
                  {invites.map((invite) => (
                    <div 
                      key={invite.id} 
                      className="flex items-center justify-between p-3 bg-slate-50 rounded-lg"
                    >
                      <div>
                        <p className="font-medium">{invite.email || invite.user_id}</p>
                        <p className="text-xs text-muted-foreground">
                          Enviada: {new Date(invite.sent_at).toLocaleDateString('es')}
                        </p>
                      </div>
                      <Badge className={
                        invite.status === 'accepted' ? 'bg-green-100 text-green-700' :
                        invite.status === 'declined' ? 'bg-red-100 text-red-700' :
                        'bg-slate-100 text-slate-700'
                      }>
                        {invite.status === 'accepted' ? 'Aceptada' :
                         invite.status === 'declined' ? 'Rechazada' :
                         invite.status === 'sent' ? 'Enviada' : 'Pendiente'}
                      </Badge>
                    </div>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>

      {/* Invite Dialog */}
      <Dialog open={inviteDialog} onOpenChange={setInviteDialog}>
        <DialogContent className="max-w-lg">
          <DialogHeader>
            <DialogTitle className="font-['Outfit']">Enviar Invitaciones</DialogTitle>
            <DialogDescription>
              Invita participantes a esta campaña por email o selecciona usuarios registrados
            </DialogDescription>
          </DialogHeader>
          
          <div className="space-y-4 py-4">
            <div className="space-y-2">
              <Label>Emails (uno por línea o separados por coma)</Label>
              <Textarea
                placeholder="usuario1@email.com&#10;usuario2@email.com"
                value={inviteEmails}
                onChange={(e) => setInviteEmails(e.target.value)}
                rows={4}
              />
            </div>
            <div className="space-y-2">
              <Label>Mensaje personalizado (opcional)</Label>
              <Textarea
                placeholder="Te invitamos a participar en..."
                value={inviteMessage}
                onChange={(e) => setInviteMessage(e.target.value)}
                rows={3}
              />
            </div>
          </div>

          <DialogFooter>
            <Button variant="outline" onClick={() => setInviteDialog(false)}>
              Cancelar
            </Button>
            <Button 
              onClick={handleSendInvites}
              className="bg-secondary hover:bg-secondary/90 text-white"
            >
              <Send className="w-4 h-4 mr-2" />
              Enviar
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
};
