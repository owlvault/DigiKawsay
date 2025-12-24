import React, { useEffect, useState, useCallback } from 'react';
import { useAuthStore } from '../stores';
import { Card, CardContent, CardDescription, CardHeader, CardTitle, CardFooter } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Badge } from '../components/ui/badge';
import { Input } from '../components/ui/input';
import { Textarea } from '../components/ui/textarea';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../components/ui/select';
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle, DialogTrigger, DialogFooter } from '../components/ui/dialog';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../components/ui/tabs';
import { Label } from '../components/ui/label';
import { Progress } from '../components/ui/progress';
import { ScrollArea } from '../components/ui/scroll-area';
import { Slider } from '../components/ui/slider';
import { toast } from 'sonner';
import {
  Route, Plus, Target, Zap, TrendingUp, Users, Clock, Calendar,
  CheckCircle2, Circle, PlayCircle, PauseCircle, XCircle,
  ArrowRight, BarChart3, Award, RefreshCw, Trash2, Edit, MessageSquare
} from 'lucide-react';
import axios from 'axios';

// Status configuration
const STATUS_CONFIG = {
  backlog: { label: 'Backlog', color: 'bg-slate-100 text-slate-700', icon: Circle },
  en_evaluacion: { label: 'En Evaluación', color: 'bg-yellow-100 text-yellow-700', icon: PauseCircle },
  aprobada: { label: 'Aprobada', color: 'bg-blue-100 text-blue-700', icon: CheckCircle2 },
  en_progreso: { label: 'En Progreso', color: 'bg-purple-100 text-purple-700', icon: PlayCircle },
  completada: { label: 'Completada', color: 'bg-green-100 text-green-700', icon: CheckCircle2 },
  cancelada: { label: 'Cancelada', color: 'bg-red-100 text-red-700', icon: XCircle },
};

const KANBAN_COLUMNS = ['backlog', 'en_evaluacion', 'aprobada', 'en_progreso', 'completada'];

// Initiative Card Component
const InitiativeCard = ({ initiative, onEdit, onStatusChange, users }) => {
  const StatusIcon = STATUS_CONFIG[initiative.status]?.icon || Circle;
  
  return (
    <Card className="mb-3 hover:shadow-md transition-shadow cursor-pointer group">
      <CardContent className="p-4">
        <div className="flex items-start justify-between gap-2">
          <div className="flex-1 min-w-0">
            <h4 className="font-medium text-sm truncate">{initiative.title}</h4>
            {initiative.description && (
              <p className="text-xs text-muted-foreground mt-1 line-clamp-2">{initiative.description}</p>
            )}
          </div>
          <Badge variant="outline" className="text-xs shrink-0">
            {initiative.final_score?.toFixed(1)}
          </Badge>
        </div>
        
        <div className="mt-3 flex items-center justify-between gap-2">
          <div className="flex items-center gap-2">
            {initiative.assigned_to_name && (
              <div className="flex items-center gap-1 text-xs text-muted-foreground">
                <Users className="w-3 h-3" />
                <span className="truncate max-w-[80px]">{initiative.assigned_to_name}</span>
              </div>
            )}
            <Badge variant="secondary" className="text-xs">
              {initiative.scoring_method?.toUpperCase()}
            </Badge>
          </div>
          
          <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
            <Button size="icon" variant="ghost" className="h-6 w-6" onClick={() => onEdit(initiative)}>
              <Edit className="w-3 h-3" />
            </Button>
          </div>
        </div>
        
        {initiative.progress_percentage > 0 && initiative.status === 'en_progreso' && (
          <div className="mt-2">
            <Progress value={initiative.progress_percentage} className="h-1" />
            <span className="text-xs text-muted-foreground">{initiative.progress_percentage}%</span>
          </div>
        )}
        
        {initiative.tags?.length > 0 && (
          <div className="flex flex-wrap gap-1 mt-2">
            {initiative.tags.slice(0, 3).map(tag => (
              <Badge key={tag} variant="outline" className="text-xs px-1">
                {tag}
              </Badge>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  );
};

// Create/Edit Initiative Dialog
const InitiativeDialog = ({ open, onOpenChange, initiative, campaigns, users, onSave }) => {
  const [formData, setFormData] = useState({
    title: '',
    description: '',
    campaign_id: '',
    scoring_method: 'ice',
    impact_score: 5,
    confidence_score: 5,
    ease_score: 5,
    reach_score: 100,
    effort_score: 5,
    assigned_to: '',
    tags: '',
  });
  
  useEffect(() => {
    if (initiative) {
      setFormData({
        title: initiative.title || '',
        description: initiative.description || '',
        campaign_id: initiative.campaign_id || '',
        scoring_method: initiative.scoring_method || 'ice',
        impact_score: initiative.impact_score || 5,
        confidence_score: initiative.confidence_score || 5,
        ease_score: initiative.ease_score || 5,
        reach_score: initiative.reach_score || 100,
        effort_score: initiative.effort_score || 5,
        assigned_to: initiative.assigned_to || '',
        tags: initiative.tags?.join(', ') || '',
      });
    } else {
      setFormData({
        title: '',
        description: '',
        campaign_id: campaigns[0]?.id || '',
        scoring_method: 'ice',
        impact_score: 5,
        confidence_score: 5,
        ease_score: 5,
        reach_score: 100,
        effort_score: 5,
        assigned_to: '',
        tags: '',
      });
    }
  }, [initiative, campaigns, open]);
  
  const calculateScore = () => {
    if (formData.scoring_method === 'rice') {
      const effort = formData.effort_score || 1;
      return ((formData.reach_score * formData.impact_score * (formData.confidence_score / 10)) / effort).toFixed(2);
    }
    return ((formData.impact_score * formData.confidence_score * formData.ease_score) / 10).toFixed(2);
  };
  
  const handleSubmit = async () => {
    if (!formData.title || !formData.campaign_id) {
      toast.error('Título y campaña son requeridos');
      return;
    }
    
    const payload = {
      ...formData,
      tags: formData.tags.split(',').map(t => t.trim()).filter(Boolean),
      assigned_to: formData.assigned_to || null,
    };
    
    try {
      if (initiative) {
        await axios.put(`/initiatives/${initiative.id}`, payload);
        toast.success('Iniciativa actualizada');
      } else {
        await axios.post('/initiatives/', payload);
        toast.success('Iniciativa creada');
      }
      onSave();
      onOpenChange(false);
    } catch (error) {
      toast.error('Error al guardar iniciativa');
    }
  };
  
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>{initiative ? 'Editar Iniciativa' : 'Nueva Iniciativa'}</DialogTitle>
          <DialogDescription>
            {initiative ? 'Modifica los detalles de la iniciativa' : 'Crea una nueva iniciativa desde insights detectados'}
          </DialogDescription>
        </DialogHeader>
        
        <div className="space-y-4 py-4">
          <div className="grid grid-cols-2 gap-4">
            <div className="col-span-2">
              <Label>Título *</Label>
              <Input
                value={formData.title}
                onChange={e => setFormData({ ...formData, title: e.target.value })}
                placeholder="Ej: Mejorar comunicación entre equipos"
              />
            </div>
            
            <div className="col-span-2">
              <Label>Descripción</Label>
              <Textarea
                value={formData.description}
                onChange={e => setFormData({ ...formData, description: e.target.value })}
                placeholder="Describe la iniciativa en detalle..."
                rows={3}
              />
            </div>
            
            <div>
              <Label>Campaña *</Label>
              <Select
                value={formData.campaign_id}
                onValueChange={v => setFormData({ ...formData, campaign_id: v })}
              >
                <SelectTrigger>
                  <SelectValue placeholder="Seleccionar" />
                </SelectTrigger>
                <SelectContent>
                  {campaigns.map(c => (
                    <SelectItem key={c.id} value={c.id}>{c.name}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            
            <div>
              <Label>Responsable</Label>
              <Select
                value={formData.assigned_to || 'none'}
                onValueChange={v => setFormData({ ...formData, assigned_to: v === 'none' ? '' : v })}
              >
                <SelectTrigger>
                  <SelectValue placeholder="Sin asignar" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="none">Sin asignar</SelectItem>
                  {users.map(u => (
                    <SelectItem key={u.id} value={u.id}>{u.full_name || u.email}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            
            <div className="col-span-2">
              <Label>Tags (separados por coma)</Label>
              <Input
                value={formData.tags}
                onChange={e => setFormData({ ...formData, tags: e.target.value })}
                placeholder="comunicación, liderazgo, cultura"
              />
            </div>
          </div>
          
          {/* Scoring Section */}
          <Card className="border-primary/20">
            <CardHeader className="pb-2">
              <CardTitle className="text-sm flex items-center justify-between">
                <span>Puntuación</span>
                <Badge variant="default" className="text-lg px-3">
                  {calculateScore()}
                </Badge>
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div>
                <Label>Método de Scoring</Label>
                <Select
                  value={formData.scoring_method}
                  onValueChange={v => setFormData({ ...formData, scoring_method: v })}
                >
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="ice">ICE (Impact × Confidence × Ease)</SelectItem>
                    <SelectItem value="rice">RICE (Reach × Impact × Confidence / Effort)</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              
              {formData.scoring_method === 'rice' && (
                <div>
                  <div className="flex justify-between text-sm">
                    <Label>Alcance (Reach)</Label>
                    <span className="font-medium">{formData.reach_score}</span>
                  </div>
                  <Slider
                    value={[formData.reach_score]}
                    onValueChange={([v]) => setFormData({ ...formData, reach_score: v })}
                    min={10}
                    max={1000}
                    step={10}
                    className="mt-2"
                  />
                  <p className="text-xs text-muted-foreground mt-1">Personas afectadas por esta iniciativa</p>
                </div>
              )}
              
              <div>
                <div className="flex justify-between text-sm">
                  <Label>Impacto</Label>
                  <span className="font-medium">{formData.impact_score}/10</span>
                </div>
                <Slider
                  value={[formData.impact_score]}
                  onValueChange={([v]) => setFormData({ ...formData, impact_score: v })}
                  min={1}
                  max={10}
                  className="mt-2"
                />
              </div>
              
              <div>
                <div className="flex justify-between text-sm">
                  <Label>Confianza</Label>
                  <span className="font-medium">{formData.confidence_score}/10</span>
                </div>
                <Slider
                  value={[formData.confidence_score]}
                  onValueChange={([v]) => setFormData({ ...formData, confidence_score: v })}
                  min={1}
                  max={10}
                  className="mt-2"
                />
              </div>
              
              {formData.scoring_method === 'ice' ? (
                <div>
                  <div className="flex justify-between text-sm">
                    <Label>Facilidad (Ease)</Label>
                    <span className="font-medium">{formData.ease_score}/10</span>
                  </div>
                  <Slider
                    value={[formData.ease_score]}
                    onValueChange={([v]) => setFormData({ ...formData, ease_score: v })}
                    min={1}
                    max={10}
                    className="mt-2"
                  />
                </div>
              ) : (
                <div>
                  <div className="flex justify-between text-sm">
                    <Label>Esfuerzo (Effort)</Label>
                    <span className="font-medium">{formData.effort_score}/10</span>
                  </div>
                  <Slider
                    value={[formData.effort_score]}
                    onValueChange={([v]) => setFormData({ ...formData, effort_score: v })}
                    min={1}
                    max={10}
                    className="mt-2"
                  />
                  <p className="text-xs text-muted-foreground mt-1">Mayor esfuerzo = menor puntuación</p>
                </div>
              )}
            </CardContent>
          </Card>
        </div>
        
        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>Cancelar</Button>
          <Button onClick={handleSubmit}>{initiative ? 'Guardar Cambios' : 'Crear Iniciativa'}</Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
};

export const RunaFlowPage = () => {
  const { user } = useAuthStore();
  const [campaigns, setCampaigns] = useState([]);
  const [selectedCampaign, setSelectedCampaign] = useState('');
  const [initiatives, setInitiatives] = useState([]);
  const [stats, setStats] = useState(null);
  const [users, setUsers] = useState([]);
  const [loading, setLoading] = useState(false);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [editingInitiative, setEditingInitiative] = useState(null);
  const [activeTab, setActiveTab] = useState('kanban');

  useEffect(() => {
    fetchCampaigns();
    fetchUsers();
  }, []);

  useEffect(() => {
    if (selectedCampaign) {
      fetchInitiatives();
      fetchStats();
    }
  }, [selectedCampaign]);

  const fetchCampaigns = async () => {
    try {
      const res = await axios.get('/campaigns/');
      setCampaigns(res.data);
      if (res.data.length > 0) {
        setSelectedCampaign(res.data[0].id);
      }
    } catch (error) {
      console.error('Error fetching campaigns:', error);
    }
  };

  const fetchUsers = async () => {
    try {
      const res = await axios.get('/users/');
      setUsers(res.data);
    } catch (error) {
      console.error('Error fetching users:', error);
    }
  };

  const fetchInitiatives = async () => {
    setLoading(true);
    try {
      const res = await axios.get(`/initiatives/campaign/${selectedCampaign}`);
      setInitiatives(res.data);
    } catch (error) {
      console.error('Error fetching initiatives:', error);
    }
    setLoading(false);
  };

  const fetchStats = async () => {
    try {
      const res = await axios.get(`/initiatives/stats/${selectedCampaign}`);
      setStats(res.data);
    } catch (error) {
      console.error('Error fetching stats:', error);
    }
  };

  const handleEdit = (initiative) => {
    setEditingInitiative(initiative);
    setDialogOpen(true);
  };

  const handleStatusChange = async (initiativeId, newStatus) => {
    try {
      await axios.put(`/initiatives/${initiativeId}`, { status: newStatus });
      toast.success('Estado actualizado');
      fetchInitiatives();
      fetchStats();
    } catch (error) {
      toast.error('Error al actualizar estado');
    }
  };

  const handleSave = () => {
    fetchInitiatives();
    fetchStats();
    setEditingInitiative(null);
  };

  const getInitiativesByStatus = (status) => {
    return initiatives.filter(i => i.status === status);
  };

  // Access control
  if (!['admin', 'facilitator', 'analyst', 'sponsor'].includes(user?.role)) {
    return (
      <div className="flex items-center justify-center h-64">
        <Card className="max-w-md">
          <CardContent className="p-8 text-center">
            <Route className="w-12 h-12 mx-auto mb-4 text-muted-foreground" />
            <h3 className="font-medium text-lg">Acceso Restringido</h3>
            <p className="text-muted-foreground mt-2">
              No tienes permisos para acceder a RunaFlow
            </p>
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className="space-y-6" data-testid="runaflow-page">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold font-['Outfit'] tracking-tight flex items-center gap-3">
            <Route className="w-8 h-8 text-primary" />
            RunaFlow
          </h1>
          <p className="text-muted-foreground mt-1">
            Gestión de Iniciativas y Roadmap - Transforma insights en acciones
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Select value={selectedCampaign} onValueChange={setSelectedCampaign}>
            <SelectTrigger className="w-[200px]">
              <SelectValue placeholder="Campaña" />
            </SelectTrigger>
            <SelectContent>
              {campaigns.map(c => (
                <SelectItem key={c.id} value={c.id}>{c.name}</SelectItem>
              ))}
            </SelectContent>
          </Select>
          <Button onClick={() => { setEditingInitiative(null); setDialogOpen(true); }}>
            <Plus className="w-4 h-4 mr-2" />
            Nueva Iniciativa
          </Button>
        </div>
      </div>

      {/* Stats Row */}
      {stats && (
        <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
          <Card>
            <CardContent className="p-4 text-center">
              <p className="text-3xl font-bold text-primary">{stats.total}</p>
              <p className="text-sm text-muted-foreground">Total Iniciativas</p>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="p-4 text-center">
              <p className="text-3xl font-bold text-green-600">{stats.by_status?.completada || 0}</p>
              <p className="text-sm text-muted-foreground">Completadas</p>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="p-4 text-center">
              <p className="text-3xl font-bold text-purple-600">{stats.by_status?.en_progreso || 0}</p>
              <p className="text-sm text-muted-foreground">En Progreso</p>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="p-4 text-center">
              <p className="text-3xl font-bold text-blue-600">{stats.avg_score?.toFixed(1) || 0}</p>
              <p className="text-sm text-muted-foreground">Score Promedio</p>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="p-4 text-center">
              <p className="text-3xl font-bold text-orange-600">{stats.completion_rate?.toFixed(0) || 0}%</p>
              <p className="text-sm text-muted-foreground">Tasa Completado</p>
            </CardContent>
          </Card>
        </div>
      )}

      {/* Main Content */}
      <Tabs value={activeTab} onValueChange={setActiveTab}>
        <TabsList>
          <TabsTrigger value="kanban">Kanban</TabsTrigger>
          <TabsTrigger value="list">Lista Priorizada</TabsTrigger>
          <TabsTrigger value="contributors">Contribuidores</TabsTrigger>
        </TabsList>
        
        <TabsContent value="kanban" className="mt-4">
          <div className="grid grid-cols-5 gap-4 min-h-[500px]">
            {KANBAN_COLUMNS.map(status => {
              const config = STATUS_CONFIG[status];
              const items = getInitiativesByStatus(status);
              const StatusIcon = config.icon;
              
              return (
                <div key={status} className="bg-slate-50 rounded-lg p-3">
                  <div className="flex items-center justify-between mb-3">
                    <div className="flex items-center gap-2">
                      <StatusIcon className="w-4 h-4" />
                      <span className="font-medium text-sm">{config.label}</span>
                    </div>
                    <Badge variant="secondary">{items.length}</Badge>
                  </div>
                  
                  <ScrollArea className="h-[450px] pr-2">
                    {items.map(initiative => (
                      <InitiativeCard
                        key={initiative.id}
                        initiative={initiative}
                        onEdit={handleEdit}
                        onStatusChange={handleStatusChange}
                        users={users}
                      />
                    ))}
                    {items.length === 0 && (
                      <div className="text-center py-8 text-sm text-muted-foreground">
                        Sin iniciativas
                      </div>
                    )}
                  </ScrollArea>
                </div>
              );
            })}
          </div>
        </TabsContent>
        
        <TabsContent value="list" className="mt-4">
          <Card>
            <CardHeader>
              <CardTitle className="font-['Outfit']">Iniciativas por Prioridad (Score)</CardTitle>
              <CardDescription>Ordenadas de mayor a menor puntuación</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-3">
                {[...initiatives].sort((a, b) => (b.final_score || 0) - (a.final_score || 0)).map((init, idx) => {
                  const StatusIcon = STATUS_CONFIG[init.status]?.icon || Circle;
                  return (
                    <div 
                      key={init.id}
                      className="flex items-center gap-4 p-3 border rounded-lg hover:bg-slate-50"
                    >
                      <span className="text-lg font-bold text-muted-foreground w-8">#{idx + 1}</span>
                      <div className="flex-1 min-w-0">
                        <h4 className="font-medium">{init.title}</h4>
                        <p className="text-sm text-muted-foreground truncate">{init.description}</p>
                      </div>
                      <Badge className={STATUS_CONFIG[init.status]?.color}>
                        <StatusIcon className="w-3 h-3 mr-1" />
                        {STATUS_CONFIG[init.status]?.label}
                      </Badge>
                      <Badge variant="outline" className="text-lg">
                        {init.final_score?.toFixed(1)}
                      </Badge>
                      <div className="flex gap-1">
                        <Button size="sm" variant="outline" onClick={() => handleEdit(init)}>
                          <Edit className="w-3 h-3" />
                        </Button>
                      </div>
                    </div>
                  );
                })}
              </div>
            </CardContent>
          </Card>
        </TabsContent>
        
        <TabsContent value="contributors" className="mt-4">
          <Card>
            <CardHeader>
              <CardTitle className="font-['Outfit'] flex items-center gap-2">
                <Award className="w-5 h-5 text-yellow-500" />
                Top Contribuidores
              </CardTitle>
              <CardDescription>Líderes de iniciativas más activos</CardDescription>
            </CardHeader>
            <CardContent>
              {stats?.top_contributors?.length > 0 ? (
                <div className="space-y-3">
                  {stats.top_contributors.map((contributor, idx) => (
                    <div 
                      key={contributor.user_id}
                      className="flex items-center gap-4 p-3 border rounded-lg"
                    >
                      <div className={`w-8 h-8 rounded-full flex items-center justify-center text-white font-bold ${
                        idx === 0 ? 'bg-yellow-500' : idx === 1 ? 'bg-slate-400' : idx === 2 ? 'bg-orange-400' : 'bg-slate-300'
                      }`}>
                        {idx + 1}
                      </div>
                      <div className="flex-1">
                        <h4 className="font-medium">{contributor.name}</h4>
                      </div>
                      <Badge variant="secondary" className="text-lg">
                        {contributor.initiatives_count} iniciativas
                      </Badge>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="text-center py-8 text-muted-foreground">
                  No hay contribuidores con iniciativas asignadas
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>

      {/* Dialog */}
      <InitiativeDialog
        open={dialogOpen}
        onOpenChange={setDialogOpen}
        initiative={editingInitiative}
        campaigns={campaigns}
        users={users}
        onSave={handleSave}
      />
    </div>
  );
};
