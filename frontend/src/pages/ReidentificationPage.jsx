import React, { useEffect, useState } from 'react';
import { useAuthStore } from '../stores';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Badge } from '../components/ui/badge';
import { Input } from '../components/ui/input';
import { Textarea } from '../components/ui/textarea';
import { Label } from '../components/ui/label';
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
import { Shield, Search, AlertTriangle, CheckCircle2, XCircle, Clock, Eye } from 'lucide-react';
import axios from 'axios';

const REASON_LABELS = {
  safety_concern: 'Preocupación de seguridad',
  legal_compliance: 'Cumplimiento legal',
  explicit_consent: 'Consentimiento explícito',
  data_correction: 'Corrección de datos'
};

export const ReidentificationPage = () => {
  const { user } = useAuthStore();
  const [pendingRequests, setPendingRequests] = useState([]);
  const [myRequests, setMyRequests] = useState([]);
  const [loading, setLoading] = useState(true);
  const [createDialog, setCreateDialog] = useState(false);
  const [resolveDialog, setResolveDialog] = useState({ open: false, request: null, result: null });
  const [formData, setFormData] = useState({
    pseudonym_id: '',
    reason_code: 'safety_concern',
    justification: ''
  });

  const isDataSteward = user?.role === 'admin' || user?.role === 'data_steward';
  const canResolve = user?.role === 'admin' || user?.role === 'security_officer';

  useEffect(() => {
    fetchData();
  }, []);

  const fetchData = async () => {
    setLoading(true);
    try {
      if (isDataSteward) {
        const res = await axios.get('/reidentification/pending');
        setPendingRequests(res.data);
      }
    } catch (error) {
      console.error('Error fetching requests:', error);
    }
    setLoading(false);
  };

  const handleCreateRequest = async () => {
    if (!formData.pseudonym_id || !formData.justification) {
      toast.error('Complete todos los campos');
      return;
    }
    try {
      await axios.post('/reidentification/request', formData);
      toast.success('Solicitud creada. Requiere aprobación de Data Steward.');
      setCreateDialog(false);
      setFormData({ pseudonym_id: '', reason_code: 'safety_concern', justification: '' });
      fetchData();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Error al crear solicitud');
    }
  };

  const handleReview = async (requestId, approved, notes = '') => {
    try {
      await axios.post(`/reidentification/${requestId}/review?approved=${approved}`, null, {
        params: { notes }
      });
      toast.success(approved ? 'Solicitud aprobada' : 'Solicitud denegada');
      fetchData();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Error al procesar');
    }
  };

  const handleResolve = async (requestId) => {
    try {
      const res = await axios.post(`/reidentification/${requestId}/resolve`);
      setResolveDialog({ open: true, request: requestId, result: res.data });
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Error al resolver');
    }
  };

  const getStatusBadge = (status) => {
    const config = {
      pending: { label: 'Pendiente', color: 'bg-yellow-100 text-yellow-700', icon: Clock },
      approved: { label: 'Aprobada', color: 'bg-green-100 text-green-700', icon: CheckCircle2 },
      denied: { label: 'Denegada', color: 'bg-red-100 text-red-700', icon: XCircle },
      resolved: { label: 'Resuelta', color: 'bg-blue-100 text-blue-700', icon: Eye },
      expired: { label: 'Expirada', color: 'bg-slate-100 text-slate-700', icon: Clock }
    };
    const c = config[status] || config.pending;
    return <Badge className={c.color}>{c.label}</Badge>;
  };

  if (user?.role !== 'admin' && user?.role !== 'data_steward' && user?.role !== 'security_officer') {
    return (
      <div className="flex items-center justify-center h-64">
        <Card className="max-w-md">
          <CardContent className="p-8 text-center">
            <Shield className="w-12 h-12 mx-auto mb-4 text-muted-foreground" />
            <h3 className="font-medium text-lg">Acceso Restringido</h3>
            <p className="text-muted-foreground mt-2">
              Solo roles autorizados pueden gestionar reidentificación
            </p>
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className="space-y-6" data-testid="reidentification-page">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold font-['Outfit'] tracking-tight">Reidentificación</h1>
          <p className="text-muted-foreground mt-1">
            Gestión de solicitudes de resolución de identidad (control dual)
          </p>
        </div>
        <Button 
          className="bg-secondary hover:bg-secondary/90 text-white"
          onClick={() => setCreateDialog(true)}
        >
          <Shield className="w-4 h-4 mr-2" />
          Nueva Solicitud
        </Button>
      </div>

      {/* Warning Banner */}
      <Card className="border-orange-200 bg-orange-50">
        <CardContent className="p-4 flex items-start gap-3">
          <AlertTriangle className="w-5 h-5 text-orange-600 mt-0.5" />
          <div>
            <p className="font-medium text-orange-900">Proceso Excepcional</p>
            <p className="text-sm text-orange-700">
              La reidentificación solo está permitida para razones legítimas (seguridad, cumplimiento legal, 
              consentimiento explícito). Requiere aprobación de Data Steward y todas las acciones son auditadas.
            </p>
          </div>
        </CardContent>
      </Card>

      {/* Pending Requests */}
      {isDataSteward && (
        <Card>
          <CardHeader>
            <CardTitle className="font-['Outfit']">Solicitudes Pendientes de Aprobación</CardTitle>
            <CardDescription>Como Data Steward, debe revisar y aprobar/denegar solicitudes</CardDescription>
          </CardHeader>
          <CardContent>
            {pendingRequests.length === 0 ? (
              <p className="text-center text-muted-foreground py-8">No hay solicitudes pendientes</p>
            ) : (
              <div className="space-y-3">
                {pendingRequests.map((req) => (
                  <Card key={req.id} className="bg-slate-50">
                    <CardContent className="p-4">
                      <div className="flex items-start justify-between">
                        <div className="space-y-2">
                          <div className="flex items-center gap-2">
                            {getStatusBadge(req.status)}
                            <Badge variant="outline">{REASON_LABELS[req.reason_code]}</Badge>
                          </div>
                          <p className="text-sm">
                            <strong>Pseudónimo:</strong> {req.pseudonym_id}
                          </p>
                          <p className="text-sm text-muted-foreground">{req.justification}</p>
                          <p className="text-xs text-muted-foreground">
                            Solicitado: {new Date(req.created_at).toLocaleString('es')}
                          </p>
                        </div>
                        {req.status === 'pending' && req.requested_by !== user.id && (
                          <div className="flex gap-2">
                            <Button 
                              size="sm" 
                              className="bg-green-600 hover:bg-green-700"
                              onClick={() => handleReview(req.id, true)}
                            >
                              Aprobar
                            </Button>
                            <Button 
                              size="sm" 
                              variant="outline"
                              className="text-red-600"
                              onClick={() => handleReview(req.id, false)}
                            >
                              Denegar
                            </Button>
                          </div>
                        )}
                        {req.status === 'approved' && canResolve && (
                          <Button 
                            size="sm"
                            onClick={() => handleResolve(req.id)}
                          >
                            <Eye className="w-4 h-4 mr-1" />
                            Resolver
                          </Button>
                        )}
                        {req.requested_by === user.id && req.status === 'pending' && (
                          <Badge variant="outline">Su solicitud</Badge>
                        )}
                      </div>
                    </CardContent>
                  </Card>
                ))}
              </div>
            )}
          </CardContent>
        </Card>
      )}

      {/* Create Request Dialog */}
      <Dialog open={createDialog} onOpenChange={setCreateDialog}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle className="font-['Outfit']">Nueva Solicitud de Reidentificación</DialogTitle>
            <DialogDescription>
              Complete la información para solicitar la resolución de un pseudónimo
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4 py-4">
            <div className="space-y-2">
              <Label>Pseudónimo a resolver *</Label>
              <Input
                placeholder="P-XXXXXXXX"
                value={formData.pseudonym_id}
                onChange={(e) => setFormData({ ...formData, pseudonym_id: e.target.value })}
              />
            </div>
            <div className="space-y-2">
              <Label>Razón *</Label>
              <Select 
                value={formData.reason_code} 
                onValueChange={(v) => setFormData({ ...formData, reason_code: v })}
              >
                <SelectTrigger><SelectValue /></SelectTrigger>
                <SelectContent>
                  {Object.entries(REASON_LABELS).map(([key, label]) => (
                    <SelectItem key={key} value={key}>{label}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-2">
              <Label>Justificación detallada *</Label>
              <Textarea
                placeholder="Explique por qué es necesaria esta reidentificación..."
                value={formData.justification}
                onChange={(e) => setFormData({ ...formData, justification: e.target.value })}
                rows={4}
              />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setCreateDialog(false)}>Cancelar</Button>
            <Button onClick={handleCreateRequest}>Crear Solicitud</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Resolve Result Dialog */}
      <Dialog open={resolveDialog.open} onOpenChange={(open) => setResolveDialog({ ...resolveDialog, open })}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle className="font-['Outfit']">Identidad Resuelta</DialogTitle>
            <DialogDescription>
              Esta información NO se persiste y debe ser tratada con confidencialidad
            </DialogDescription>
          </DialogHeader>
          {resolveDialog.result && (
            <div className="space-y-4 py-4">
              <Card className="bg-slate-50">
                <CardContent className="p-4 space-y-2">
                  <p><strong>Pseudónimo:</strong> {resolveDialog.result.pseudonym_id}</p>
                  {resolveDialog.result.resolved_user ? (
                    <>
                      <p><strong>Nombre:</strong> {resolveDialog.result.resolved_user.full_name}</p>
                      <p><strong>Email:</strong> {resolveDialog.result.resolved_user.email}</p>
                      {resolveDialog.result.resolved_user.department && (
                        <p><strong>Departamento:</strong> {resolveDialog.result.resolved_user.department}</p>
                      )}
                    </>
                  ) : (
                    <p className="text-muted-foreground">No se pudo resolver la identidad</p>
                  )}
                </CardContent>
              </Card>
              <Card className="border-red-200 bg-red-50">
                <CardContent className="p-3">
                  <p className="text-sm text-red-700">
                    ⚠️ {resolveDialog.result.warning}
                  </p>
                </CardContent>
              </Card>
            </div>
          )}
          <DialogFooter>
            <Button onClick={() => setResolveDialog({ open: false, request: null, result: null })}>
              Cerrar
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
};
