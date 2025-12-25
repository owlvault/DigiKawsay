import React, { useEffect, useState, useCallback } from 'react';
import { useAuthStore } from '../stores';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Badge } from '../components/ui/badge';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../components/ui/select';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../components/ui/tabs';
import { Progress } from '../components/ui/progress';
import { ScrollArea } from '../components/ui/scroll-area';
import { toast } from 'sonner';
import {
  Activity, Cpu, HardDrive, MemoryStick, Network, Clock, Users,
  AlertTriangle, CheckCircle, XCircle, Bell, RefreshCw, Server,
  FileText, TrendingUp, Zap, Eye, MessageSquare, Target
} from 'lucide-react';
import axios from 'axios';

// Severity colors
const SEVERITY_CONFIG = {
  low: { color: 'bg-blue-100 text-blue-700', icon: Bell },
  medium: { color: 'bg-yellow-100 text-yellow-700', icon: AlertTriangle },
  high: { color: 'bg-orange-100 text-orange-700', icon: AlertTriangle },
  critical: { color: 'bg-red-100 text-red-700', icon: XCircle },
};

// Health status colors
const HEALTH_CONFIG = {
  healthy: { color: 'text-green-600', bg: 'bg-green-100', label: 'Saludable' },
  warning: { color: 'text-yellow-600', bg: 'bg-yellow-100', label: 'Advertencia' },
  degraded: { color: 'text-orange-600', bg: 'bg-orange-100', label: 'Degradado' },
  critical: { color: 'text-red-600', bg: 'bg-red-100', label: 'Crítico' },
};

// Log level colors
const LOG_LEVEL_CONFIG = {
  debug: 'text-gray-500',
  info: 'text-blue-600',
  warning: 'text-yellow-600',
  error: 'text-red-600',
  critical: 'text-red-700 font-bold',
};

// Metric Card Component
const MetricCard = ({ title, value, unit, icon: Icon, color, subtitle, progress }) => (
  <Card>
    <CardContent className="p-4">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className={`p-2 rounded-lg ${color || 'bg-primary/10'}`}>
            <Icon className="w-5 h-5" />
          </div>
          <div>
            <p className="text-sm text-muted-foreground">{title}</p>
            <p className="text-2xl font-bold">
              {typeof value === 'number' ? value.toFixed(1) : value}
              {unit && <span className="text-sm font-normal text-muted-foreground ml-1">{unit}</span>}
            </p>
            {subtitle && <p className="text-xs text-muted-foreground">{subtitle}</p>}
          </div>
        </div>
      </div>
      {progress !== undefined && (
        <Progress value={progress} className="mt-3 h-2" />
      )}
    </CardContent>
  </Card>
);

// Alert Item Component
const AlertItem = ({ alert, onAcknowledge }) => {
  const config = SEVERITY_CONFIG[alert.severity] || SEVERITY_CONFIG.medium;
  const Icon = config.icon;
  
  return (
    <div className={`p-3 rounded-lg border ${alert.acknowledged ? 'opacity-50' : ''}`}>
      <div className="flex items-start justify-between gap-2">
        <div className="flex items-start gap-2">
          <Badge className={config.color}>
            <Icon className="w-3 h-3 mr-1" />
            {alert.severity}
          </Badge>
          <div>
            <h4 className="font-medium text-sm">{alert.title}</h4>
            <p className="text-xs text-muted-foreground">{alert.message}</p>
            <p className="text-xs text-muted-foreground mt-1">
              {new Date(alert.timestamp).toLocaleString()}
            </p>
          </div>
        </div>
        {!alert.acknowledged && (
          <Button size="sm" variant="outline" onClick={() => onAcknowledge(alert.id)}>
            <CheckCircle className="w-3 h-3 mr-1" />
            Reconocer
          </Button>
        )}
      </div>
    </div>
  );
};

// Log Entry Component
const LogEntry = ({ log }) => {
  const levelColor = LOG_LEVEL_CONFIG[log.level] || 'text-gray-600';
  
  return (
    <div className="py-2 border-b last:border-0 font-mono text-xs">
      <div className="flex items-center gap-2">
        <span className="text-muted-foreground w-[180px]">
          {new Date(log.timestamp).toLocaleString()}
        </span>
        <Badge variant="outline" className={`${levelColor} uppercase w-16 justify-center`}>
          {log.level}
        </Badge>
        <span className="flex-1 truncate">{log.message}</span>
        {log.correlation_id && (
          <span className="text-muted-foreground text-[10px]">
            {log.correlation_id.slice(0, 8)}
          </span>
        )}
      </div>
      {log.endpoint && (
        <div className="ml-[196px] text-muted-foreground">
          {log.method} {log.endpoint} → {log.status_code} ({log.duration_ms?.toFixed(0)}ms)
        </div>
      )}
    </div>
  );
};

export const ObservabilityPage = () => {
  const { user } = useAuthStore();
  const [dashboard, setDashboard] = useState(null);
  const [logs, setLogs] = useState([]);
  const [loading, setLoading] = useState(false);
  const [autoRefresh, setAutoRefresh] = useState(false);
  const [logLevel, setLogLevel] = useState('all');
  const [activeTab, setActiveTab] = useState('dashboard');

  const fetchDashboard = useCallback(async () => {
    try {
      const res = await axios.get('/observability/dashboard');
      setDashboard(res.data);
    } catch (error) {
      console.error('Error fetching dashboard:', error);
    }
  }, []);

  const fetchLogs = useCallback(async () => {
    try {
      const params = logLevel !== 'all' ? `?level=${logLevel}` : '';
      const res = await axios.get(`/observability/logs${params}&limit=200`);
      setLogs(res.data);
    } catch (error) {
      console.error('Error fetching logs:', error);
    }
  }, [logLevel]);

  const refresh = useCallback(async () => {
    setLoading(true);
    await Promise.all([fetchDashboard(), fetchLogs()]);
    setLoading(false);
  }, [fetchDashboard, fetchLogs]);

  useEffect(() => {
    refresh();
  }, [refresh]);

  useEffect(() => {
    let interval;
    if (autoRefresh) {
      interval = setInterval(refresh, 5000);
    }
    return () => clearInterval(interval);
  }, [autoRefresh, refresh]);

  const handleAcknowledge = async (alertId) => {
    try {
      await axios.post(`/observability/alerts/${alertId}/acknowledge`);
      toast.success('Alerta reconocida');
      fetchDashboard();
    } catch (error) {
      toast.error('Error al reconocer alerta');
    }
  };

  // Access control
  if (!['admin', 'security_officer'].includes(user?.role)) {
    return (
      <div className="flex items-center justify-center h-64">
        <Card className="max-w-md">
          <CardContent className="p-8 text-center">
            <Activity className="w-12 h-12 mx-auto mb-4 text-muted-foreground" />
            <h3 className="font-medium text-lg">Acceso Restringido</h3>
            <p className="text-muted-foreground mt-2">
              Solo administradores y security officers pueden acceder a Observabilidad
            </p>
          </CardContent>
        </Card>
      </div>
    );
  }

  const healthConfig = HEALTH_CONFIG[dashboard?.health_status] || HEALTH_CONFIG.healthy;
  const system = dashboard?.system || {};
  const business = dashboard?.business || {};
  const endpoints = dashboard?.endpoints || [];
  const alerts = dashboard?.active_alerts || [];

  return (
    <div className="space-y-6" data-testid="observability-page">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold font-['Outfit'] tracking-tight flex items-center gap-3">
            <Activity className="w-8 h-8 text-primary" />
            Observabilidad
          </h1>
          <p className="text-muted-foreground mt-1">
            Monitoreo del sistema - Métricas, logs y alertas en tiempo real
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Button
            variant={autoRefresh ? 'default' : 'outline'}
            size="sm"
            onClick={() => setAutoRefresh(!autoRefresh)}
          >
            {autoRefresh ? 'Auto-refresh ON' : 'Auto-refresh OFF'}
          </Button>
          <Button variant="outline" onClick={refresh} disabled={loading}>
            <RefreshCw className={`w-4 h-4 mr-2 ${loading ? 'animate-spin' : ''}`} />
            Actualizar
          </Button>
        </div>
      </div>

      {/* Health Status Banner */}
      <Card className={healthConfig.bg}>
        <CardContent className="p-4 flex items-center justify-between">
          <div className="flex items-center gap-3">
            {dashboard?.health_status === 'healthy' ? (
              <CheckCircle className={`w-8 h-8 ${healthConfig.color}`} />
            ) : (
              <AlertTriangle className={`w-8 h-8 ${healthConfig.color}`} />
            )}
            <div>
              <h2 className={`text-xl font-bold ${healthConfig.color}`}>
                Estado: {healthConfig.label}
              </h2>
              <p className="text-sm text-muted-foreground">
                Uptime: {Math.floor((system.uptime_seconds || 0) / 60)} minutos
              </p>
            </div>
          </div>
          {alerts.length > 0 && (
            <Badge variant="destructive" className="text-lg px-4 py-1">
              {alerts.length} alertas activas
            </Badge>
          )}
        </CardContent>
      </Card>

      {/* Main Content */}
      <Tabs value={activeTab} onValueChange={setActiveTab}>
        <TabsList>
          <TabsTrigger value="dashboard">Dashboard</TabsTrigger>
          <TabsTrigger value="endpoints">Endpoints</TabsTrigger>
          <TabsTrigger value="logs">Logs</TabsTrigger>
          <TabsTrigger value="alerts">
            Alertas
            {alerts.length > 0 && <Badge variant="destructive" className="ml-2">{alerts.length}</Badge>}
          </TabsTrigger>
        </TabsList>

        {/* Dashboard Tab */}
        <TabsContent value="dashboard" className="mt-4 space-y-4">
          {/* System Metrics */}
          <div>
            <h3 className="font-medium mb-3 flex items-center gap-2">
              <Server className="w-4 h-4" />
              Métricas del Sistema
            </h3>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <MetricCard
                title="CPU"
                value={system.cpu_percent}
                unit="%"
                icon={Cpu}
                color="bg-blue-100"
                progress={system.cpu_percent}
              />
              <MetricCard
                title="Memoria"
                value={system.memory_percent}
                unit="%"
                icon={MemoryStick}
                color="bg-purple-100"
                progress={system.memory_percent}
                subtitle={`${(system.memory_used_mb / 1024).toFixed(1)} GB usado`}
              />
              <MetricCard
                title="Disco"
                value={system.disk_percent}
                unit="%"
                icon={HardDrive}
                color="bg-orange-100"
                progress={system.disk_percent}
              />
              <MetricCard
                title="Conexiones"
                value={system.active_connections}
                icon={Network}
                color="bg-green-100"
              />
            </div>
          </div>

          {/* Business Metrics */}
          <div>
            <h3 className="font-medium mb-3 flex items-center gap-2">
              <TrendingUp className="w-4 h-4" />
              Métricas de Negocio
            </h3>
            <div className="grid grid-cols-2 md:grid-cols-6 gap-4">
              <MetricCard
                title="Usuarios"
                value={business.total_users}
                icon={Users}
                color="bg-blue-100"
              />
              <MetricCard
                title="Sesiones Activas"
                value={business.active_sessions}
                icon={Zap}
                color="bg-green-100"
              />
              <MetricCard
                title="Campañas"
                value={business.total_campaigns}
                icon={Target}
                color="bg-purple-100"
              />
              <MetricCard
                title="Insights"
                value={business.total_insights}
                icon={Eye}
                color="bg-orange-100"
              />
              <MetricCard
                title="Mensajes Hoy"
                value={business.messages_today}
                icon={MessageSquare}
                color="bg-cyan-100"
              />
              <MetricCard
                title="Insights Hoy"
                value={business.insights_generated_today}
                icon={Zap}
                color="bg-yellow-100"
              />
            </div>
          </div>

          {/* Top Endpoints */}
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-sm font-['Outfit']">Top Endpoints por Tráfico</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-2">
                {endpoints.slice(0, 5).map((ep, idx) => (
                  <div key={idx} className="flex items-center justify-between p-2 bg-slate-50 rounded">
                    <div className="flex items-center gap-2">
                      <Badge variant="outline">{ep.method}</Badge>
                      <span className="text-sm font-mono">{ep.endpoint}</span>
                    </div>
                    <div className="flex items-center gap-4 text-sm">
                      <span>{ep.request_count} requests</span>
                      <span className={ep.error_count > 0 ? 'text-red-600' : 'text-green-600'}>
                        {ep.error_count} errors
                      </span>
                      <span>{ep.avg_latency_ms.toFixed(0)}ms avg</span>
                    </div>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        {/* Endpoints Tab */}
        <TabsContent value="endpoints" className="mt-4">
          <Card>
            <CardHeader>
              <CardTitle className="font-['Outfit']">Métricas por Endpoint</CardTitle>
              <CardDescription>Latencia y tasa de errores por endpoint</CardDescription>
            </CardHeader>
            <CardContent>
              <ScrollArea className="h-[500px]">
                <div className="space-y-2">
                  {endpoints.map((ep, idx) => {
                    const errorRate = ep.request_count > 0 ? (ep.error_count / ep.request_count * 100) : 0;
                    return (
                      <div key={idx} className="p-3 border rounded-lg">
                        <div className="flex items-center justify-between">
                          <div className="flex items-center gap-2">
                            <Badge variant="outline">{ep.method}</Badge>
                            <span className="font-mono text-sm">{ep.endpoint}</span>
                          </div>
                          <Badge variant={errorRate > 5 ? 'destructive' : 'secondary'}>
                            {errorRate.toFixed(1)}% error
                          </Badge>
                        </div>
                        <div className="grid grid-cols-4 gap-4 mt-2 text-sm">
                          <div>
                            <p className="text-muted-foreground">Requests</p>
                            <p className="font-bold">{ep.request_count}</p>
                          </div>
                          <div>
                            <p className="text-muted-foreground">Avg Latency</p>
                            <p className="font-bold">{ep.avg_latency_ms.toFixed(0)}ms</p>
                          </div>
                          <div>
                            <p className="text-muted-foreground">P95 Latency</p>
                            <p className="font-bold">{ep.p95_latency_ms.toFixed(0)}ms</p>
                          </div>
                          <div>
                            <p className="text-muted-foreground">P99 Latency</p>
                            <p className="font-bold">{ep.p99_latency_ms.toFixed(0)}ms</p>
                          </div>
                        </div>
                      </div>
                    );
                  })}
                </div>
              </ScrollArea>
            </CardContent>
          </Card>
        </TabsContent>

        {/* Logs Tab */}
        <TabsContent value="logs" className="mt-4">
          <Card>
            <CardHeader>
              <div className="flex items-center justify-between">
                <div>
                  <CardTitle className="font-['Outfit']">Logs del Sistema</CardTitle>
                  <CardDescription>Logs estructurados en tiempo real</CardDescription>
                </div>
                <Select value={logLevel} onValueChange={setLogLevel}>
                  <SelectTrigger className="w-[150px]">
                    <SelectValue placeholder="Nivel" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="all">Todos</SelectItem>
                    <SelectItem value="debug">Debug</SelectItem>
                    <SelectItem value="info">Info</SelectItem>
                    <SelectItem value="warning">Warning</SelectItem>
                    <SelectItem value="error">Error</SelectItem>
                    <SelectItem value="critical">Critical</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </CardHeader>
            <CardContent>
              <ScrollArea className="h-[500px] bg-slate-950 rounded-lg p-4">
                <div className="text-green-400">
                  {logs.map((log, idx) => (
                    <LogEntry key={idx} log={log} />
                  ))}
                  {logs.length === 0 && (
                    <p className="text-center text-muted-foreground py-8">No hay logs disponibles</p>
                  )}
                </div>
              </ScrollArea>
            </CardContent>
          </Card>
        </TabsContent>

        {/* Alerts Tab */}
        <TabsContent value="alerts" className="mt-4">
          <Card>
            <CardHeader>
              <CardTitle className="font-['Outfit']">Alertas Activas</CardTitle>
              <CardDescription>Alertas que requieren atención</CardDescription>
            </CardHeader>
            <CardContent>
              <ScrollArea className="h-[400px]">
                {alerts.length > 0 ? (
                  <div className="space-y-3">
                    {alerts.map((alert, idx) => (
                      <AlertItem key={idx} alert={alert} onAcknowledge={handleAcknowledge} />
                    ))}
                  </div>
                ) : (
                  <div className="text-center py-12 text-muted-foreground">
                    <CheckCircle className="w-16 h-16 mx-auto mb-4 text-green-500 opacity-50" />
                    <p className="text-lg font-medium">Sin alertas activas</p>
                    <p className="text-sm">El sistema está funcionando correctamente</p>
                  </div>
                )}
              </ScrollArea>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
};
