import React, { useEffect, useState } from 'react';
import { useAuthStore } from '../stores';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Badge } from '../components/ui/badge';
import { Input } from '../components/ui/input';
import { Textarea } from '../components/ui/textarea';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../components/ui/select';
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle, DialogFooter } from '../components/ui/dialog';
import { Switch } from '../components/ui/switch';
import { Label } from '../components/ui/label';
import { ScrollArea } from '../components/ui/scroll-area';
import { toast } from 'sonner';
import {
  Calendar, Clock, Plus, Edit, Trash2, Users, Play, Check,
  CalendarDays, CalendarClock, RefreshCw
} from 'lucide-react';
import axios from 'axios';

const RITUAL_TYPES = {
  daily: { label: 'Diario', icon: Clock, color: 'bg-blue-100 text-blue-700' },
  weekly: { label: 'Semanal', icon: CalendarDays, color: 'bg-green-100 text-green-700' },
  monthly: { label: 'Mensual', icon: Calendar, color: 'bg-purple-100 text-purple-700' },
  quarterly: { label: 'Trimestral', icon: CalendarClock, color: 'bg-orange-100 text-orange-700' },
};

const DAYS_OF_WEEK = ['Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado', 'Domingo'];

// Ritual Dialog Component
const RitualDialog = ({ open, onOpenChange, ritual, campaigns, users, onSave }) => {
  const [formData, setFormData] = useState({
    name: '',
    description: '',
    ritual_type: 'weekly',
    campaign_id: '',
    day_of_week: 0,
    day_of_month: 1,
    time_of_day: '09:00',
    duration_minutes: 30,
    participants: [],
    agenda_template: '',
    is_active: true,
  });

  useEffect(() => {
    if (ritual) {
      setFormData({
        name: ritual.name || '',
        description: ritual.description || '',
        ritual_type: ritual.ritual_type || 'weekly',
        campaign_id: ritual.campaign_id || '',
        day_of_week: ritual.day_of_week ?? 0,
        day_of_month: ritual.day_of_month ?? 1,
        time_of_day: ritual.time_of_day || '09:00',
        duration_minutes: ritual.duration_minutes || 30,
        participants: ritual.participants || [],
        agenda_template: ritual.agenda_template || '',
        is_active: ritual.is_active !== false,
      });
    } else {
      setFormData({
        name: '',
        description: '',
        ritual_type: 'weekly',
        campaign_id: '',
        day_of_week: 0,
        day_of_month: 1,
        time_of_day: '09:00',
        duration_minutes: 30,
        participants: [],
        agenda_template: '',
        is_active: true,
      });
    }
  }, [ritual, open]);

  const handleSubmit = async () => {
    if (!formData.name) {
      toast.error('El nombre es requerido');
      return;
    }

    try {
      const payload = {
        ...formData,
        campaign_id: formData.campaign_id || null,
      };
      
      if (ritual) {
        await axios.put(`/rituals/${ritual.id}`, payload);
        toast.success('Ritual actualizado');
      } else {
        await axios.post('/rituals/', payload);
        toast.success('Ritual creado');
      }
      onSave();
      onOpenChange(false);
    } catch (error) {
      toast.error('Error al guardar ritual');
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-xl">
        <DialogHeader>
          <DialogTitle>{ritual ? 'Editar Ritual' : 'Nuevo Ritual'}</DialogTitle>
          <DialogDescription>
            {ritual ? 'Modifica los detalles del ritual' : 'Crea un nuevo ritual organizacional'}
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4 py-4">
          <div>
            <Label>Nombre *</Label>
            <Input
              value={formData.name}
              onChange={e => setFormData({ ...formData, name: e.target.value })}
              placeholder="Ej: Daily de Seguimiento"
            />
          </div>

          <div>
            <Label>Descripción</Label>
            <Textarea
              value={formData.description}
              onChange={e => setFormData({ ...formData, description: e.target.value })}
              placeholder="Propósito del ritual..."
              rows={2}
            />
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <Label>Tipo de Ritual</Label>
              <Select
                value={formData.ritual_type}
                onValueChange={v => setFormData({ ...formData, ritual_type: v })}
              >
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {Object.entries(RITUAL_TYPES).map(([key, config]) => (
                    <SelectItem key={key} value={key}>{config.label}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            <div>
              <Label>Campaña (opcional)</Label>
              <Select
                value={formData.campaign_id}
                onValueChange={v => setFormData({ ...formData, campaign_id: v })}
              >
                <SelectTrigger>
                  <SelectValue placeholder="Global" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="">Global (todas las campañas)</SelectItem>
                  {campaigns.map(c => (
                    <SelectItem key={c.id} value={c.id}>{c.name}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          </div>

          <div className="grid grid-cols-3 gap-4">
            {(formData.ritual_type === 'weekly') && (
              <div>
                <Label>Día de la Semana</Label>
                <Select
                  value={String(formData.day_of_week)}
                  onValueChange={v => setFormData({ ...formData, day_of_week: parseInt(v) })}
                >
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {DAYS_OF_WEEK.map((day, idx) => (
                      <SelectItem key={idx} value={String(idx)}>{day}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            )}

            {(formData.ritual_type === 'monthly' || formData.ritual_type === 'quarterly') && (
              <div>
                <Label>Día del Mes</Label>
                <Select
                  value={String(formData.day_of_month)}
                  onValueChange={v => setFormData({ ...formData, day_of_month: parseInt(v) })}
                >
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {Array.from({ length: 28 }, (_, i) => i + 1).map(day => (
                      <SelectItem key={day} value={String(day)}>{day}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            )}

            <div>
              <Label>Hora</Label>
              <Input
                type="time"
                value={formData.time_of_day}
                onChange={e => setFormData({ ...formData, time_of_day: e.target.value })}
              />
            </div>

            <div>
              <Label>Duración (min)</Label>
              <Select
                value={String(formData.duration_minutes)}
                onValueChange={v => setFormData({ ...formData, duration_minutes: parseInt(v) })}
              >
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="15">15 min</SelectItem>
                  <SelectItem value="30">30 min</SelectItem>
                  <SelectItem value="45">45 min</SelectItem>
                  <SelectItem value="60">1 hora</SelectItem>
                  <SelectItem value="90">1.5 horas</SelectItem>
                  <SelectItem value="120">2 horas</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>

          <div>
            <Label>Agenda / Plantilla</Label>
            <Textarea
              value={formData.agenda_template}
              onChange={e => setFormData({ ...formData, agenda_template: e.target.value })}
              placeholder="1. Check-in&#10;2. Revisión de progreso&#10;3. Bloqueos&#10;4. Próximos pasos"
              rows={4}
            />
          </div>

          <div className="flex items-center gap-2">
            <Switch
              checked={formData.is_active}
              onCheckedChange={v => setFormData({ ...formData, is_active: v })}
            />
            <Label>Ritual activo</Label>
          </div>
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>Cancelar</Button>
          <Button onClick={handleSubmit}>{ritual ? 'Guardar' : 'Crear Ritual'}</Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
};

export const RitualsPage = () => {
  const { user } = useAuthStore();
  const [rituals, setRituals] = useState([]);
  const [campaigns, setCampaigns] = useState([]);
  const [users, setUsers] = useState([]);
  const [loading, setLoading] = useState(false);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [editingRitual, setEditingRitual] = useState(null);
  const [filterType, setFilterType] = useState('all');

  useEffect(() => {
    fetchRituals();
    fetchCampaigns();
    fetchUsers();
  }, []);

  const fetchRituals = async () => {
    setLoading(true);
    try {
      const res = await axios.get('/rituals/');
      setRituals(res.data);
    } catch (error) {
      console.error('Error fetching rituals:', error);
    }
    setLoading(false);
  };

  const fetchCampaigns = async () => {
    try {
      const res = await axios.get('/campaigns/');
      setCampaigns(res.data);
    } catch (error) {
      console.error('Error:', error);
    }
  };

  const fetchUsers = async () => {
    try {
      const res = await axios.get('/users/');
      setUsers(res.data);
    } catch (error) {
      console.error('Error:', error);
    }
  };

  const handleEdit = (ritual) => {
    setEditingRitual(ritual);
    setDialogOpen(true);
  };

  const handleDelete = async (ritualId) => {
    if (!window.confirm('¿Eliminar este ritual?')) return;
    try {
      await axios.delete(`/rituals/${ritualId}`);
      toast.success('Ritual eliminado');
      fetchRituals();
    } catch (error) {
      toast.error('Error al eliminar');
    }
  };

  const handleSave = () => {
    fetchRituals();
    setEditingRitual(null);
  };

  const filteredRituals = filterType === 'all' 
    ? rituals 
    : rituals.filter(r => r.ritual_type === filterType);

  const formatNextOccurrence = (dateStr) => {
    if (!dateStr) return 'No programado';
    try {
      const date = new Date(dateStr);
      return date.toLocaleDateString('es', { 
        weekday: 'short', 
        day: 'numeric', 
        month: 'short',
        hour: '2-digit',
        minute: '2-digit'
      });
    } catch {
      return dateStr;
    }
  };

  // Access control
  if (!['admin', 'facilitator'].includes(user?.role)) {
    return (
      <div className="flex items-center justify-center h-64">
        <Card className="max-w-md">
          <CardContent className="p-8 text-center">
            <Calendar className="w-12 h-12 mx-auto mb-4 text-muted-foreground" />
            <h3 className="font-medium text-lg">Acceso Restringido</h3>
            <p className="text-muted-foreground mt-2">
              Solo administradores y facilitadores pueden gestionar rituales
            </p>
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className="space-y-6" data-testid="rituals-page">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold font-['Outfit'] tracking-tight flex items-center gap-3">
            <Calendar className="w-8 h-8 text-primary" />
            Rituales Organizacionales
          </h1>
          <p className="text-muted-foreground mt-1">
            Gestiona las ceremonias recurrentes de tu equipo
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Select value={filterType} onValueChange={setFilterType}>
            <SelectTrigger className="w-[150px]">
              <SelectValue placeholder="Filtrar" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">Todos</SelectItem>
              {Object.entries(RITUAL_TYPES).map(([key, config]) => (
                <SelectItem key={key} value={key}>{config.label}</SelectItem>
              ))}
            </SelectContent>
          </Select>
          <Button onClick={() => { setEditingRitual(null); setDialogOpen(true); }}>
            <Plus className="w-4 h-4 mr-2" />
            Nuevo Ritual
          </Button>
        </div>
      </div>

      {/* Stats Cards */}
      <div className="grid grid-cols-4 gap-4">
        {Object.entries(RITUAL_TYPES).map(([type, config]) => {
          const count = rituals.filter(r => r.ritual_type === type).length;
          const Icon = config.icon;
          return (
            <Card key={type} className="cursor-pointer hover:shadow-md transition-shadow" onClick={() => setFilterType(type)}>
              <CardContent className="p-4 flex items-center gap-3">
                <div className={`p-2 rounded-lg ${config.color}`}>
                  <Icon className="w-5 h-5" />
                </div>
                <div>
                  <p className="text-2xl font-bold">{count}</p>
                  <p className="text-sm text-muted-foreground">{config.label}s</p>
                </div>
              </CardContent>
            </Card>
          );
        })}
      </div>

      {/* Rituals Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {filteredRituals.map(ritual => {
          const typeConfig = RITUAL_TYPES[ritual.ritual_type] || RITUAL_TYPES.weekly;
          const TypeIcon = typeConfig.icon;
          
          return (
            <Card key={ritual.id} className={`${!ritual.is_active ? 'opacity-60' : ''}`}>
              <CardHeader className="pb-2">
                <div className="flex items-start justify-between">
                  <div className="flex items-center gap-2">
                    <div className={`p-2 rounded-lg ${typeConfig.color}`}>
                      <TypeIcon className="w-4 h-4" />
                    </div>
                    <div>
                      <CardTitle className="text-base">{ritual.name}</CardTitle>
                      <Badge variant="secondary" className="text-xs mt-1">
                        {typeConfig.label}
                      </Badge>
                    </div>
                  </div>
                  <div className="flex gap-1">
                    <Button size="icon" variant="ghost" className="h-7 w-7" onClick={() => handleEdit(ritual)}>
                      <Edit className="w-3 h-3" />
                    </Button>
                    <Button size="icon" variant="ghost" className="h-7 w-7 text-destructive" onClick={() => handleDelete(ritual.id)}>
                      <Trash2 className="w-3 h-3" />
                    </Button>
                  </div>
                </div>
              </CardHeader>
              <CardContent className="space-y-3">
                {ritual.description && (
                  <p className="text-sm text-muted-foreground line-clamp-2">{ritual.description}</p>
                )}
                
                <div className="flex items-center gap-4 text-sm">
                  <div className="flex items-center gap-1 text-muted-foreground">
                    <Clock className="w-4 h-4" />
                    <span>{ritual.time_of_day || '09:00'}</span>
                  </div>
                  <div className="flex items-center gap-1 text-muted-foreground">
                    <span>{ritual.duration_minutes || 30} min</span>
                  </div>
                </div>
                
                {ritual.next_occurrence && (
                  <div className="flex items-center gap-2 text-sm">
                    <Calendar className="w-4 h-4 text-primary" />
                    <span className="font-medium">Próximo: {formatNextOccurrence(ritual.next_occurrence)}</span>
                  </div>
                )}
                
                {ritual.agenda_template && (
                  <div className="mt-2 p-2 bg-slate-50 rounded text-xs text-muted-foreground whitespace-pre-line line-clamp-3">
                    {ritual.agenda_template}
                  </div>
                )}
                
                <div className="flex items-center justify-between pt-2 border-t">
                  <div className="flex items-center gap-1 text-xs text-muted-foreground">
                    <RefreshCw className="w-3 h-3" />
                    <span>{ritual.occurrences_count || 0} ocurrencias</span>
                  </div>
                  {!ritual.is_active && (
                    <Badge variant="outline" className="text-xs">Inactivo</Badge>
                  )}
                </div>
              </CardContent>
            </Card>
          );
        })}
        
        {filteredRituals.length === 0 && (
          <Card className="col-span-full">
            <CardContent className="p-8 text-center">
              <Calendar className="w-12 h-12 mx-auto mb-4 text-muted-foreground opacity-50" />
              <h3 className="font-medium">No hay rituales</h3>
              <p className="text-sm text-muted-foreground mt-1">
                Crea tu primer ritual para empezar a gestionar las ceremonias del equipo
              </p>
              <Button className="mt-4" onClick={() => setDialogOpen(true)}>
                <Plus className="w-4 h-4 mr-2" />
                Crear Ritual
              </Button>
            </CardContent>
          </Card>
        )}
      </div>

      {/* Dialog */}
      <RitualDialog
        open={dialogOpen}
        onOpenChange={setDialogOpen}
        ritual={editingRitual}
        campaigns={campaigns}
        users={users}
        onSave={handleSave}
      />
    </div>
  );
};
