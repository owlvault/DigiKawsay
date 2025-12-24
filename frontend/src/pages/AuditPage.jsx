import React, { useEffect, useState } from 'react';
import { useAuthStore } from '../stores';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Badge } from '../components/ui/badge';
import { Input } from '../components/ui/input';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../components/ui/select';
import { ScrollArea } from '../components/ui/scroll-area';
import { 
  Shield, Search, Download, Eye, FileText, UserCheck, 
  LogIn, LogOut, AlertTriangle, RefreshCw
} from 'lucide-react';
import axios from 'axios';

const ACTION_CONFIG = {
  login: { label: 'Inicio sesión', icon: LogIn, color: 'bg-blue-100 text-blue-700' },
  logout: { label: 'Cierre sesión', icon: LogOut, color: 'bg-slate-100 text-slate-700' },
  view_transcript: { label: 'Ver transcripción', icon: Eye, color: 'bg-yellow-100 text-yellow-700' },
  view_insight: { label: 'Ver insight', icon: Eye, color: 'bg-green-100 text-green-700' },
  export_data: { label: 'Exportar datos', icon: Download, color: 'bg-purple-100 text-purple-700' },
  consent_given: { label: 'Consentimiento dado', icon: UserCheck, color: 'bg-emerald-100 text-emerald-700' },
  consent_revoked: { label: 'Consentimiento revocado', icon: AlertTriangle, color: 'bg-red-100 text-red-700' },
  reidentification_request: { label: 'Solicitud reidentificación', icon: Shield, color: 'bg-orange-100 text-orange-700' },
  reidentification_approve: { label: 'Aprobación reidentificación', icon: Shield, color: 'bg-amber-100 text-amber-700' },
  reidentification_resolve: { label: 'Resolución reidentificación', icon: Shield, color: 'bg-rose-100 text-rose-700' },
  data_deleted: { label: 'Datos eliminados', icon: FileText, color: 'bg-red-100 text-red-700' },
};

export const AuditPage = () => {
  const { user } = useAuthStore();
  const [logs, setLogs] = useState([]);
  const [summary, setSummary] = useState(null);
  const [loading, setLoading] = useState(true);
  const [filters, setFilters] = useState({ action: 'all', resource_type: 'all', user_id: '' });

  useEffect(() => {
    fetchData();
  }, []);

  useEffect(() => {
    fetchLogs();
  }, [filters]);

  const fetchData = async () => {
    setLoading(true);
    try {
      const [logsRes, summaryRes] = await Promise.all([
        axios.get('/audit/'),
        axios.get('/audit/summary?days=30')
      ]);
      setLogs(logsRes.data);
      setSummary(summaryRes.data);
    } catch (error) {
      console.error('Error fetching audit data:', error);
    }
    setLoading(false);
  };

  const fetchLogs = async () => {
    try {
      const params = new URLSearchParams();
      if (filters.action && filters.action !== 'all') params.append('action', filters.action);
      if (filters.resource_type && filters.resource_type !== 'all') params.append('resource_type', filters.resource_type);
      if (filters.user_id) params.append('user_id', filters.user_id);
      const url = `/audit/${params.toString() ? '?' + params.toString() : ''}`;
      const res = await axios.get(url);
      setLogs(res.data);
    } catch (error) {
      console.error('Error fetching logs:', error);
    }
  };

  if (user?.role !== 'admin' && user?.role !== 'security_officer') {
    return (
      <div className="flex items-center justify-center h-64">
        <Card className="max-w-md">
          <CardContent className="p-8 text-center">
            <Shield className="w-12 h-12 mx-auto mb-4 text-muted-foreground" />
            <h3 className="font-medium text-lg">Acceso Restringido</h3>
            <p className="text-muted-foreground mt-2">
              Solo administradores y security officers pueden ver la auditoría
            </p>
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className="space-y-6" data-testid="audit-page">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold font-['Outfit'] tracking-tight">Auditoría</h1>
          <p className="text-muted-foreground mt-1">Registro de actividad y acceso a datos</p>
        </div>
        <Button variant="outline" onClick={fetchData}>
          <RefreshCw className="w-4 h-4 mr-2" />
          Actualizar
        </Button>
      </div>

      {/* Summary Cards */}
      {summary && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <Card>
            <CardContent className="p-4 text-center">
              <p className="text-3xl font-bold text-primary">{summary.total_events}</p>
              <p className="text-xs text-muted-foreground">Eventos (30 días)</p>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="p-4 text-center">
              <p className="text-2xl font-bold">{summary.by_action?.login || 0}</p>
              <p className="text-xs text-muted-foreground">Inicios de sesión</p>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="p-4 text-center">
              <p className="text-2xl font-bold">{summary.by_action?.view_transcript || 0}</p>
              <p className="text-xs text-muted-foreground">Transcripciones vistas</p>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="p-4 text-center">
              <p className="text-2xl font-bold text-orange-600">
                {(summary.by_action?.reidentification_request || 0) + 
                 (summary.by_action?.reidentification_resolve || 0)}
              </p>
              <p className="text-xs text-muted-foreground">Reidentificaciones</p>
            </CardContent>
          </Card>
        </div>
      )}

      {/* Filters */}
      <Card>
        <CardContent className="p-4">
          <div className="flex flex-wrap gap-4">
            <Select value={filters.action} onValueChange={(v) => setFilters({ ...filters, action: v })}>
              <SelectTrigger className="w-[200px]">
                <SelectValue placeholder="Filtrar por acción" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">Todas las acciones</SelectItem>
                {Object.entries(ACTION_CONFIG).map(([key, config]) => (
                  <SelectItem key={key} value={key}>{config.label}</SelectItem>
                ))}
              </SelectContent>
            </Select>
            <Select value={filters.resource_type} onValueChange={(v) => setFilters({ ...filters, resource_type: v })}>
              <SelectTrigger className="w-[200px]">
                <SelectValue placeholder="Tipo de recurso" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">Todos los recursos</SelectItem>
                <SelectItem value="transcript">Transcripción</SelectItem>
                <SelectItem value="insight">Insight</SelectItem>
                <SelectItem value="consent">Consentimiento</SelectItem>
                <SelectItem value="session">Sesión</SelectItem>
                <SelectItem value="reidentification">Reidentificación</SelectItem>
              </SelectContent>
            </Select>
            <Input
              placeholder="Filtrar por User ID..."
              value={filters.user_id}
              onChange={(e) => setFilters({ ...filters, user_id: e.target.value })}
              className="w-[200px]"
            />
          </div>
        </CardContent>
      </Card>

      {/* Logs List */}
      <Card>
        <CardHeader>
          <CardTitle className="font-['Outfit']">Eventos Recientes</CardTitle>
          <CardDescription>Últimos {logs.length} eventos registrados</CardDescription>
        </CardHeader>
        <CardContent>
          <ScrollArea className="h-[500px]">
            <div className="space-y-2">
              {logs.length === 0 ? (
                <p className="text-center text-muted-foreground py-8">No hay eventos registrados</p>
              ) : (
                logs.map((log) => {
                  const config = ACTION_CONFIG[log.action] || { 
                    label: log.action, 
                    icon: FileText, 
                    color: 'bg-slate-100 text-slate-700' 
                  };
                  const Icon = config.icon;
                  
                  return (
                    <div 
                      key={log.id} 
                      className="flex items-start gap-4 p-3 bg-slate-50 rounded-lg hover:bg-slate-100 transition-colors"
                    >
                      <div className={`p-2 rounded-lg ${config.color.split(' ')[0]}`}>
                        <Icon className={`w-4 h-4 ${config.color.split(' ')[1]}`} />
                      </div>
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2 flex-wrap">
                          <Badge className={config.color}>{config.label}</Badge>
                          <span className="text-xs text-muted-foreground">
                            {new Date(log.created_at).toLocaleString('es')}
                          </span>
                        </div>
                        <p className="text-sm mt-1">
                          <span className="font-medium">{log.user_role}</span>
                          {log.resource_id && (
                            <span className="text-muted-foreground"> → {log.resource_type}: {log.resource_id.slice(0, 8)}...</span>
                          )}
                        </p>
                        {log.details && Object.keys(log.details).length > 0 && (
                          <p className="text-xs text-muted-foreground mt-1">
                            {JSON.stringify(log.details).slice(0, 100)}
                          </p>
                        )}
                      </div>
                      {!log.success && (
                        <Badge className="bg-red-100 text-red-700">Error</Badge>
                      )}
                    </div>
                  );
                })
              )}
            </div>
          </ScrollArea>
        </CardContent>
      </Card>
    </div>
  );
};
