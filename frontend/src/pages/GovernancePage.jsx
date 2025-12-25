import React, { useEffect, useState } from 'react';
import { useAuthStore } from '../stores';
import { Card, CardContent, CardDescription, CardHeader, CardTitle, CardFooter } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Badge } from '../components/ui/badge';
import { Input } from '../components/ui/input';
import { Textarea } from '../components/ui/textarea';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../components/ui/select';
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle, DialogFooter } from '../components/ui/dialog';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../components/ui/tabs';
import { Switch } from '../components/ui/switch';
import { Label } from '../components/ui/label';
import { Progress } from '../components/ui/progress';
import { ScrollArea } from '../components/ui/scroll-area';
import { Slider } from '../components/ui/slider';
import { toast } from 'sonner';
import {
  Shield, FileCheck, Users, Lock, Archive, AlertTriangle, Check, X,
  Plus, RefreshCw, Clock, ChevronRight, Activity, Database, Eye
} from 'lucide-react';
import axios from 'axios';

// Status badges for dual approval
const APPROVAL_STATUS = {
  pending: { label: 'Pendiente', color: 'bg-yellow-100 text-yellow-700' },
  first_approved: { label: 'Primera Aprobación', color: 'bg-blue-100 text-blue-700' },
  approved: { label: 'Aprobada', color: 'bg-green-100 text-green-700' },
  rejected: { label: 'Rechazada', color: 'bg-red-100 text-red-700' },
};

// Policy Dialog
const PolicyDialog = ({ open, onOpenChange, policy, onSave }) => {
  const [formData, setFormData] = useState({
    name: '',
    description: '',
    retention_days: 365,
    archive_after_days: 180,
    auto_anonymize_days: 90,
    allow_transcript_export: false,
    allow_insight_export: true,
    allow_bulk_export: false,
    require_approval_for_export: true,
    anonymization_level: 'standard',
    suppress_small_groups: true,
    min_group_size: 5,
  });

  useEffect(() => {
    if (policy) {
      setFormData({
        name: policy.name || '',
        description: policy.description || '',
        retention_days: policy.retention_days || 365,
        archive_after_days: policy.archive_after_days || 180,
        auto_anonymize_days: policy.auto_anonymize_days || 90,
        allow_transcript_export: policy.allow_transcript_export || false,
        allow_insight_export: policy.allow_insight_export !== false,
        allow_bulk_export: policy.allow_bulk_export || false,
        require_approval_for_export: policy.require_approval_for_export !== false,
        anonymization_level: policy.anonymization_level || 'standard',
        suppress_small_groups: policy.suppress_small_groups !== false,
        min_group_size: policy.min_group_size || 5,
      });
    } else {
      setFormData({
        name: '',
        description: '',
        retention_days: 365,
        archive_after_days: 180,
        auto_anonymize_days: 90,
        allow_transcript_export: false,
        allow_insight_export: true,
        allow_bulk_export: false,
        require_approval_for_export: true,
        anonymization_level: 'standard',
        suppress_small_groups: true,
        min_group_size: 5,
      });
    }
  }, [policy, open]);

  const handleSubmit = async () => {
    if (!formData.name) {
      toast.error('El nombre es requerido');
      return;
    }
    try {
      if (policy) {
        await axios.put(`/governance/policies/${policy.id}`, formData);
        toast.success('Política actualizada');
      } else {
        await axios.post('/governance/policies', formData);
        toast.success('Política creada y activada');
      }
      onSave();
      onOpenChange(false);
    } catch (error) {
      toast.error('Error al guardar política');
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>{policy ? 'Editar Política' : 'Nueva Política de Datos'}</DialogTitle>
          <DialogDescription>
            {policy ? 'Modifica la política de datos' : 'Crea una nueva política de gobernanza de datos'}
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-6 py-4">
          <div className="space-y-4">
            <div>
              <Label>Nombre *</Label>
              <Input
                value={formData.name}
                onChange={e => setFormData({ ...formData, name: e.target.value })}
                placeholder="Ej: Política de Retención Estándar"
              />
            </div>
            <div>
              <Label>Descripción</Label>
              <Textarea
                value={formData.description}
                onChange={e => setFormData({ ...formData, description: e.target.value })}
                placeholder="Descripción de la política..."
                rows={2}
              />
            </div>
          </div>

          {/* Retention Settings */}
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-sm flex items-center gap-2">
                <Clock className="w-4 h-4" />
                Retención de Datos
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div>
                <div className="flex justify-between text-sm">
                  <Label>Días de retención total</Label>
                  <span className="font-medium">{formData.retention_days} días</span>
                </div>
                <Slider
                  value={[formData.retention_days]}
                  onValueChange={([v]) => setFormData({ ...formData, retention_days: v })}
                  min={30}
                  max={730}
                  step={30}
                  className="mt-2"
                />
              </div>
              <div>
                <div className="flex justify-between text-sm">
                  <Label>Archivar después de</Label>
                  <span className="font-medium">{formData.archive_after_days} días</span>
                </div>
                <Slider
                  value={[formData.archive_after_days]}
                  onValueChange={([v]) => setFormData({ ...formData, archive_after_days: v })}
                  min={30}
                  max={365}
                  step={30}
                  className="mt-2"
                />
              </div>
              <div>
                <div className="flex justify-between text-sm">
                  <Label>Auto-anonimizar después de</Label>
                  <span className="font-medium">{formData.auto_anonymize_days} días</span>
                </div>
                <Slider
                  value={[formData.auto_anonymize_days]}
                  onValueChange={([v]) => setFormData({ ...formData, auto_anonymize_days: v })}
                  min={7}
                  max={180}
                  step={7}
                  className="mt-2"
                />
              </div>
            </CardContent>
          </Card>

          {/* Export Settings */}
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-sm flex items-center gap-2">
                <Database className="w-4 h-4" />
                Permisos de Exportación
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              <div className="flex items-center justify-between">
                <Label>Exportar transcripciones</Label>
                <Switch
                  checked={formData.allow_transcript_export}
                  onCheckedChange={v => setFormData({ ...formData, allow_transcript_export: v })}
                />
              </div>
              <div className="flex items-center justify-between">
                <Label>Exportar insights</Label>
                <Switch
                  checked={formData.allow_insight_export}
                  onCheckedChange={v => setFormData({ ...formData, allow_insight_export: v })}
                />
              </div>
              <div className="flex items-center justify-between">
                <Label>Exportación masiva</Label>
                <Switch
                  checked={formData.allow_bulk_export}
                  onCheckedChange={v => setFormData({ ...formData, allow_bulk_export: v })}
                />
              </div>
              <div className="flex items-center justify-between">
                <Label>Requiere aprobación</Label>
                <Switch
                  checked={formData.require_approval_for_export}
                  onCheckedChange={v => setFormData({ ...formData, require_approval_for_export: v })}
                />
              </div>
            </CardContent>
          </Card>

          {/* Privacy Settings */}
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-sm flex items-center gap-2">
                <Eye className="w-4 h-4" />
                Privacidad y Anonimización
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div>
                <Label>Nivel de anonimización</Label>
                <Select
                  value={formData.anonymization_level}
                  onValueChange={v => setFormData({ ...formData, anonymization_level: v })}
                >
                  <SelectTrigger className="mt-1">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="minimal">Mínimo - Solo nombres</SelectItem>
                    <SelectItem value="standard">Estándar - Nombres, emails, teléfonos</SelectItem>
                    <SelectItem value="strict">Estricto - Todos los datos identificables</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              <div className="flex items-center justify-between">
                <Label>Suprimir grupos pequeños</Label>
                <Switch
                  checked={formData.suppress_small_groups}
                  onCheckedChange={v => setFormData({ ...formData, suppress_small_groups: v })}
                />
              </div>
              {formData.suppress_small_groups && (
                <div>
                  <div className="flex justify-between text-sm">
                    <Label>Tamaño mínimo de grupo</Label>
                    <span className="font-medium">{formData.min_group_size} personas</span>
                  </div>
                  <Slider
                    value={[formData.min_group_size]}
                    onValueChange={([v]) => setFormData({ ...formData, min_group_size: v })}
                    min={3}
                    max={10}
                    className="mt-2"
                  />
                </div>
              )}
            </CardContent>
          </Card>
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>Cancelar</Button>
          <Button onClick={handleSubmit}>{policy ? 'Guardar' : 'Crear Política'}</Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
};

export const GovernancePage = () => {
  const { user } = useAuthStore();
  const [metrics, setMetrics] = useState(null);
  const [policies, setPolicies] = useState([]);
  const [pendingApprovals, setPendingApprovals] = useState([]);
  const [archivedRecords, setArchivedRecords] = useState([]);
  const [permissions, setPermissions] = useState([]);
  const [loading, setLoading] = useState(false);
  const [policyDialogOpen, setPolicyDialogOpen] = useState(false);
  const [editingPolicy, setEditingPolicy] = useState(null);
  const [activeTab, setActiveTab] = useState('dashboard');

  useEffect(() => {
    fetchAll();
  }, []);

  const fetchAll = async () => {
    setLoading(true);
    try {
      await Promise.all([
        fetchMetrics(),
        fetchPolicies(),
        fetchPendingApprovals(),
        fetchArchivedRecords(),
        fetchPermissions(),
      ]);
    } catch (error) {
      console.error('Error fetching data:', error);
    }
    setLoading(false);
  };

  const fetchMetrics = async () => {
    try {
      const res = await axios.get('/governance/metrics');
      setMetrics(res.data);
    } catch (error) {
      console.error('Error:', error);
    }
  };

  const fetchPolicies = async () => {
    try {
      const res = await axios.get('/governance/policies');
      setPolicies(res.data);
    } catch (error) {
      console.error('Error:', error);
    }
  };

  const fetchPendingApprovals = async () => {
    try {
      const res = await axios.get('/governance/dual-approval/pending');
      setPendingApprovals(res.data);
    } catch (error) {
      console.error('Error:', error);
    }
  };

  const fetchArchivedRecords = async () => {
    try {
      const res = await axios.get('/governance/archive/records');
      setArchivedRecords(res.data);
    } catch (error) {
      console.error('Error:', error);
    }
  };

  const fetchPermissions = async () => {
    try {
      const res = await axios.get('/governance/permissions');
      setPermissions(res.data.permissions || []);
    } catch (error) {
      console.error('Error:', error);
    }
  };

  const handleApprove = async (requestId) => {
    try {
      const res = await axios.post(`/governance/dual-approval/${requestId}/approve`);
      toast.success(res.data.message);
      fetchPendingApprovals();
      fetchMetrics();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Error al aprobar');
    }
  };

  const handleReject = async (requestId, reason) => {
    const inputReason = prompt('Motivo del rechazo:');
    if (!inputReason) return;
    try {
      await axios.post(`/governance/dual-approval/${requestId}/reject?reason=${encodeURIComponent(inputReason)}`);
      toast.success('Solicitud rechazada');
      fetchPendingApprovals();
      fetchMetrics();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Error al rechazar');
    }
  };

  const handleRunArchival = async () => {
    if (!window.confirm('¿Ejecutar archivado de datos antiguos según la política activa?')) return;
    try {
      const res = await axios.post('/governance/archive/run');
      toast.success(`Archivado completado: ${JSON.stringify(res.data.archived)}`);
      fetchArchivedRecords();
      fetchMetrics();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Error al archivar');
    }
  };

  // Access control
  if (!['admin', 'data_steward', 'security_officer'].includes(user?.role)) {
    return (
      <div className="flex items-center justify-center h-64">
        <Card className="max-w-md">
          <CardContent className="p-8 text-center">
            <Shield className="w-12 h-12 mx-auto mb-4 text-muted-foreground" />
            <h3 className="font-medium text-lg">Acceso Restringido</h3>
            <p className="text-muted-foreground mt-2">
              Solo administradores, data stewards y security officers pueden acceder a RunaData
            </p>
          </CardContent>
        </Card>
      </div>
    );
  }

  const getComplianceColor = (score) => {
    if (score >= 80) return 'text-green-600';
    if (score >= 60) return 'text-yellow-600';
    return 'text-red-600';
  };

  return (
    <div className="space-y-6" data-testid="governance-page">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold font-['Outfit'] tracking-tight flex items-center gap-3">
            <Shield className="w-8 h-8 text-primary" />
            RunaData
          </h1>
          <p className="text-muted-foreground mt-1">
            Gobernanza de Datos - Control de acceso y políticas de privacidad
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Button variant="outline" onClick={fetchAll} disabled={loading}>
            <RefreshCw className={`w-4 h-4 mr-2 ${loading ? 'animate-spin' : ''}`} />
            Actualizar
          </Button>
          <Button onClick={() => { setEditingPolicy(null); setPolicyDialogOpen(true); }}>
            <Plus className="w-4 h-4 mr-2" />
            Nueva Política
          </Button>
        </div>
      </div>

      {/* Metrics Cards */}
      {metrics && (
        <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
          <Card>
            <CardContent className="p-4 text-center">
              <p className={`text-3xl font-bold ${getComplianceColor(metrics.compliance_score)}`}>
                {metrics.compliance_score?.toFixed(0)}%
              </p>
              <p className="text-sm text-muted-foreground">Score Compliance</p>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="p-4 text-center">
              <p className="text-3xl font-bold text-primary">{metrics.active_policies}</p>
              <p className="text-sm text-muted-foreground">Políticas Activas</p>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="p-4 text-center">
              <p className="text-3xl font-bold text-orange-600">{metrics.pending_approvals}</p>
              <p className="text-sm text-muted-foreground">Aprobaciones Pendientes</p>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="p-4 text-center">
              <p className="text-3xl font-bold text-blue-600">{metrics.archived_records}</p>
              <p className="text-sm text-muted-foreground">Registros Archivados</p>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="p-4 text-center">
              <p className="text-3xl font-bold">{permissions.length}</p>
              <p className="text-sm text-muted-foreground">Tus Permisos</p>
            </CardContent>
          </Card>
        </div>
      )}

      {/* Main Content */}
      <Tabs value={activeTab} onValueChange={setActiveTab}>
        <TabsList>
          <TabsTrigger value="dashboard">Dashboard</TabsTrigger>
          <TabsTrigger value="policies">Políticas</TabsTrigger>
          <TabsTrigger value="approvals">
            Aprobaciones
            {pendingApprovals.length > 0 && (
              <Badge variant="destructive" className="ml-2">{pendingApprovals.length}</Badge>
            )}
          </TabsTrigger>
          <TabsTrigger value="archive">Archivado</TabsTrigger>
          <TabsTrigger value="permissions">Permisos</TabsTrigger>
        </TabsList>

        {/* Dashboard Tab */}
        <TabsContent value="dashboard" className="mt-4 space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {/* Compliance Score Card */}
            <Card>
              <CardHeader>
                <CardTitle className="font-['Outfit'] flex items-center gap-2">
                  <Activity className="w-5 h-5" />
                  Score de Compliance
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="text-center">
                  <p className={`text-6xl font-bold ${getComplianceColor(metrics?.compliance_score || 0)}`}>
                    {metrics?.compliance_score?.toFixed(0) || 0}
                  </p>
                  <Progress 
                    value={metrics?.compliance_score || 0} 
                    className="mt-4 h-3"
                  />
                  <p className="text-sm text-muted-foreground mt-2">
                    {metrics?.compliance_score >= 80 ? 'Excelente cumplimiento' :
                     metrics?.compliance_score >= 60 ? 'Cumplimiento moderado' :
                     'Requiere atención'}
                  </p>
                </div>
              </CardContent>
            </Card>

            {/* Data Age Distribution */}
            <Card>
              <CardHeader>
                <CardTitle className="font-['Outfit'] flex items-center gap-2">
                  <Clock className="w-5 h-5" />
                  Antigüedad de Datos
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-3">
                  {metrics?.data_by_age && Object.entries(metrics.data_by_age).map(([period, count]) => (
                    <div key={period} className="flex items-center justify-between">
                      <span className="text-sm capitalize">{period.replace(/_/g, ' ')}</span>
                      <Badge variant="secondary">{count} sesiones</Badge>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          </div>

          {/* Recent Violations */}
          {metrics?.recent_violations?.length > 0 && (
            <Card className="border-red-200">
              <CardHeader>
                <CardTitle className="font-['Outfit'] flex items-center gap-2 text-red-600">
                  <AlertTriangle className="w-5 h-5" />
                  Alertas Recientes
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-2">
                  {metrics.recent_violations.map((v, idx) => (
                    <div key={idx} className="flex items-center gap-2 p-2 bg-red-50 rounded">
                      <AlertTriangle className="w-4 h-4 text-red-500" />
                      <span className="text-sm">{v.action}</span>
                      <span className="text-xs text-muted-foreground">{v.created_at}</span>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          )}
        </TabsContent>

        {/* Policies Tab */}
        <TabsContent value="policies" className="mt-4">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {policies.map(policy => (
              <Card key={policy.id} className={policy.is_active ? 'border-primary' : ''}>
                <CardHeader>
                  <div className="flex items-center justify-between">
                    <CardTitle className="text-base">{policy.name}</CardTitle>
                    {policy.is_active && <Badge>Activa</Badge>}
                  </div>
                  {policy.description && (
                    <CardDescription>{policy.description}</CardDescription>
                  )}
                </CardHeader>
                <CardContent className="space-y-2 text-sm">
                  <div className="flex justify-between">
                    <span>Retención:</span>
                    <span className="font-medium">{policy.retention_days} días</span>
                  </div>
                  <div className="flex justify-between">
                    <span>Archivado:</span>
                    <span className="font-medium">{policy.archive_after_days} días</span>
                  </div>
                  <div className="flex justify-between">
                    <span>Anonimización:</span>
                    <span className="font-medium capitalize">{policy.anonymization_level}</span>
                  </div>
                  <div className="flex justify-between">
                    <span>Grupos mínimos:</span>
                    <span className="font-medium">{policy.min_group_size} personas</span>
                  </div>
                </CardContent>
                <CardFooter>
                  <Button 
                    variant="outline" 
                    size="sm" 
                    onClick={() => { setEditingPolicy(policy); setPolicyDialogOpen(true); }}
                  >
                    Editar
                  </Button>
                </CardFooter>
              </Card>
            ))}
            {policies.length === 0 && (
              <Card className="col-span-full">
                <CardContent className="p-8 text-center">
                  <FileCheck className="w-12 h-12 mx-auto mb-4 text-muted-foreground opacity-50" />
                  <p>No hay políticas de datos configuradas</p>
                  <Button className="mt-4" onClick={() => setPolicyDialogOpen(true)}>
                    <Plus className="w-4 h-4 mr-2" />
                    Crear Primera Política
                  </Button>
                </CardContent>
              </Card>
            )}
          </div>
        </TabsContent>

        {/* Approvals Tab */}
        <TabsContent value="approvals" className="mt-4">
          <Card>
            <CardHeader>
              <CardTitle className="font-['Outfit']">Solicitudes de Control Dual</CardTitle>
              <CardDescription>
                Requiere aprobación de Admin + Security Officer
              </CardDescription>
            </CardHeader>
            <CardContent>
              <ScrollArea className="h-[400px]">
                {pendingApprovals.length > 0 ? (
                  <div className="space-y-3">
                    {pendingApprovals.map(request => (
                      <div 
                        key={request.id}
                        className="p-4 border rounded-lg"
                      >
                        <div className="flex items-start justify-between">
                          <div>
                            <div className="flex items-center gap-2">
                              <Badge className={APPROVAL_STATUS[request.status]?.color}>
                                {APPROVAL_STATUS[request.status]?.label}
                              </Badge>
                              <span className="font-medium">{request.request_type}</span>
                            </div>
                            <p className="text-sm text-muted-foreground mt-1">
                              Recurso: {request.resource_type} / {request.resource_id?.slice(0, 8)}...
                            </p>
                            <p className="text-sm mt-2">{request.justification}</p>
                            <p className="text-xs text-muted-foreground mt-1">
                              Solicitado por: {request.requested_by_name}
                            </p>
                          </div>
                          <div className="flex gap-2">
                            <Button 
                              size="sm" 
                              variant="outline"
                              onClick={() => handleApprove(request.id)}
                            >
                              <Check className="w-4 h-4 mr-1" />
                              Aprobar
                            </Button>
                            <Button 
                              size="sm" 
                              variant="destructive"
                              onClick={() => handleReject(request.id)}
                            >
                              <X className="w-4 h-4 mr-1" />
                              Rechazar
                            </Button>
                          </div>
                        </div>
                        {request.first_approver_name && (
                          <div className="mt-2 p-2 bg-blue-50 rounded text-sm">
                            ✓ Primera aprobación: {request.first_approver_name}
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                ) : (
                  <div className="text-center py-8 text-muted-foreground">
                    <Check className="w-12 h-12 mx-auto mb-4 opacity-50" />
                    <p>No hay solicitudes pendientes</p>
                  </div>
                )}
              </ScrollArea>
            </CardContent>
          </Card>
        </TabsContent>

        {/* Archive Tab */}
        <TabsContent value="archive" className="mt-4">
          <Card>
            <CardHeader>
              <div className="flex items-center justify-between">
                <div>
                  <CardTitle className="font-['Outfit']">Datos Archivados</CardTitle>
                  <CardDescription>Registros archivados según políticas de retención</CardDescription>
                </div>
                <Button onClick={handleRunArchival}>
                  <Archive className="w-4 h-4 mr-2" />
                  Ejecutar Archivado
                </Button>
              </div>
            </CardHeader>
            <CardContent>
              <ScrollArea className="h-[400px]">
                {archivedRecords.length > 0 ? (
                  <div className="space-y-2">
                    {archivedRecords.map(record => (
                      <div key={record.id} className="flex items-center justify-between p-3 border rounded">
                        <div>
                          <div className="flex items-center gap-2">
                            <Badge variant="secondary">{record.original_collection}</Badge>
                            <span className="text-sm">{record.original_id?.slice(0, 12)}...</span>
                          </div>
                          <p className="text-xs text-muted-foreground mt-1">{record.reason}</p>
                        </div>
                        <span className="text-xs text-muted-foreground">
                          {new Date(record.created_at).toLocaleDateString()}
                        </span>
                      </div>
                    ))}
                  </div>
                ) : (
                  <div className="text-center py-8 text-muted-foreground">
                    <Archive className="w-12 h-12 mx-auto mb-4 opacity-50" />
                    <p>No hay registros archivados</p>
                  </div>
                )}
              </ScrollArea>
            </CardContent>
          </Card>
        </TabsContent>

        {/* Permissions Tab */}
        <TabsContent value="permissions" className="mt-4">
          <Card>
            <CardHeader>
              <CardTitle className="font-['Outfit']">Tus Permisos ({user?.role})</CardTitle>
              <CardDescription>
                Permisos asignados a tu rol actual
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="flex flex-wrap gap-2">
                {permissions.map(perm => (
                  <Badge key={perm} variant="outline" className="text-xs">
                    {perm.replace(/_/g, ' ')}
                  </Badge>
                ))}
              </div>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>

      {/* Policy Dialog */}
      <PolicyDialog
        open={policyDialogOpen}
        onOpenChange={setPolicyDialogOpen}
        policy={editingPolicy}
        onSave={() => { fetchPolicies(); fetchMetrics(); setEditingPolicy(null); }}
      />
    </div>
  );
};
