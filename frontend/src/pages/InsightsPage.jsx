import React, { useEffect, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { useInsightStore, useCampaignStore, useTaxonomyStore } from '../stores';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Badge } from '../components/ui/badge';
import { Progress } from '../components/ui/progress';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../components/ui/select';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../components/ui/tabs';
import { toast } from 'sonner';
import { 
  Search, Plus, Lightbulb, ArrowLeft, Filter, CheckCircle2, XCircle, 
  TrendingUp, AlertTriangle, Target, Zap, Eye, ThumbsUp, ThumbsDown,
  RefreshCw, BarChart3
} from 'lucide-react';

const TYPE_CONFIG = {
  theme: { label: 'Tema', color: 'bg-blue-100 text-blue-700', icon: Lightbulb },
  tension: { label: 'Tensión', color: 'bg-red-100 text-red-700', icon: AlertTriangle },
  symbol: { label: 'Símbolo', color: 'bg-purple-100 text-purple-700', icon: Target },
  opportunity: { label: 'Oportunidad', color: 'bg-green-100 text-green-700', icon: TrendingUp },
  risk: { label: 'Riesgo', color: 'bg-orange-100 text-orange-700', icon: Zap }
};

const STATUS_CONFIG = {
  draft: { label: 'Borrador', color: 'bg-slate-100 text-slate-700' },
  validated: { label: 'Validado', color: 'bg-green-100 text-green-700' },
  rejected: { label: 'Rechazado', color: 'bg-red-100 text-red-700' },
  needs_review: { label: 'En revisión', color: 'bg-yellow-100 text-yellow-700' }
};

const SENTIMENT_CONFIG = {
  positive: { label: 'Positivo', color: 'text-green-600' },
  negative: { label: 'Negativo', color: 'text-red-600' },
  neutral: { label: 'Neutral', color: 'text-slate-600' },
  mixed: { label: 'Mixto', color: 'text-purple-600' }
};

export const InsightsPage = () => {
  const { campaignId } = useParams();
  const navigate = useNavigate();
  const { insights, fetchInsights, stats, getStats, validateInsight, extractInsights, isLoading } = useInsightStore();
  const { currentCampaign, getCampaign } = useCampaignStore();
  const { categories, fetchCategories } = useTaxonomyStore();

  const [filters, setFilters] = useState({ type: '', status: '', sentiment: '' });
  const [searchTerm, setSearchTerm] = useState('');
  const [extracting, setExtracting] = useState(false);

  useEffect(() => {
    loadData();
  }, [campaignId]);

  useEffect(() => {
    fetchInsights(campaignId, filters);
  }, [filters, campaignId]);

  const loadData = async () => {
    await getCampaign(campaignId);
    await fetchInsights(campaignId, {});
    await getStats(campaignId);
    await fetchCategories();
  };

  const handleExtract = async () => {
    setExtracting(true);
    const result = await extractInsights(campaignId);
    setExtracting(false);
    if (result.success) {
      toast.success(`Extracción iniciada: ${result.data.queued || 0} transcripciones en cola`);
      setTimeout(() => {
        fetchInsights(campaignId, filters);
        getStats(campaignId);
      }, 5000);
    } else {
      toast.error(result.error || 'Error al extraer');
    }
  };

  const handleValidate = async (insightId, validated) => {
    const result = await validateInsight(insightId, validated);
    if (result.success) {
      toast.success(validated ? 'Insight validado' : 'Insight rechazado');
    } else {
      toast.error(result.error);
    }
  };

  const filteredInsights = insights.filter(i =>
    i.content?.toLowerCase().includes(searchTerm.toLowerCase()) ||
    i.source_quote?.toLowerCase().includes(searchTerm.toLowerCase())
  );

  return (
    <div className="space-y-6" data-testid="insights-page">
      {/* Header */}
      <div className="flex items-start justify-between">
        <div className="flex items-center gap-4">
          <Button variant="ghost" size="icon" onClick={() => navigate(`/campaigns/${campaignId}`)}>
            <ArrowLeft className="w-5 h-5" />
          </Button>
          <div>
            <h1 className="text-3xl font-bold font-['Outfit'] tracking-tight">Hallazgos</h1>
            <p className="text-muted-foreground mt-1">{currentCampaign?.name || 'Campaña'}</p>
          </div>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" onClick={handleExtract} disabled={extracting}>
            <RefreshCw className={`w-4 h-4 mr-2 ${extracting ? 'animate-spin' : ''}`} />
            {extracting ? 'Extrayendo...' : 'Extraer Insights'}
          </Button>
          <Button className="bg-secondary hover:bg-secondary/90 text-white" onClick={() => navigate(`/insights/${campaignId}/new`)}>
            <Plus className="w-4 h-4 mr-2" />
            Agregar Manual
          </Button>
        </div>
      </div>

      {/* Stats Cards */}
      {stats && (
        <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
          <Card>
            <CardContent className="p-4 text-center">
              <p className="text-3xl font-bold text-primary">{stats.total_insights}</p>
              <p className="text-xs text-muted-foreground">Total</p>
            </CardContent>
          </Card>
          {Object.entries(TYPE_CONFIG).map(([type, config]) => (
            <Card key={type}>
              <CardContent className="p-4 text-center">
                <p className="text-2xl font-bold">{stats.by_type?.[type] || 0}</p>
                <p className="text-xs text-muted-foreground">{config.label}s</p>
              </CardContent>
            </Card>
          ))}
        </div>
      )}

      {/* Filters */}
      <Card>
        <CardContent className="p-4">
          <div className="flex flex-wrap gap-4">
            <div className="relative flex-1 min-w-[200px]">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
              <Input
                placeholder="Buscar insights..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className="pl-10"
              />
            </div>
            <Select value={filters.type} onValueChange={(v) => setFilters({ ...filters, type: v })}>
              <SelectTrigger className="w-[150px]"><SelectValue placeholder="Tipo" /></SelectTrigger>
              <SelectContent>
                <SelectItem value="">Todos</SelectItem>
                {Object.entries(TYPE_CONFIG).map(([k, v]) => (<SelectItem key={k} value={k}>{v.label}</SelectItem>))}
              </SelectContent>
            </Select>
            <Select value={filters.status} onValueChange={(v) => setFilters({ ...filters, status: v })}>
              <SelectTrigger className="w-[150px]"><SelectValue placeholder="Estado" /></SelectTrigger>
              <SelectContent>
                <SelectItem value="">Todos</SelectItem>
                {Object.entries(STATUS_CONFIG).map(([k, v]) => (<SelectItem key={k} value={k}>{v.label}</SelectItem>))}
              </SelectContent>
            </Select>
            <Select value={filters.sentiment} onValueChange={(v) => setFilters({ ...filters, sentiment: v })}>
              <SelectTrigger className="w-[150px]"><SelectValue placeholder="Sentimiento" /></SelectTrigger>
              <SelectContent>
                <SelectItem value="">Todos</SelectItem>
                {Object.entries(SENTIMENT_CONFIG).map(([k, v]) => (<SelectItem key={k} value={k}>{v.label}</SelectItem>))}
              </SelectContent>
            </Select>
          </div>
        </CardContent>
      </Card>

      {/* Insights List */}
      {filteredInsights.length === 0 ? (
        <Card className="border-dashed">
          <CardContent className="flex flex-col items-center justify-center py-16">
            <Lightbulb className="w-12 h-12 text-muted-foreground mb-4" />
            <h3 className="font-medium text-lg">No hay hallazgos</h3>
            <p className="text-muted-foreground text-center mt-1">
              Extrae insights de las transcripciones o agrégalos manualmente
            </p>
          </CardContent>
        </Card>
      ) : (
        <div className="space-y-3">
          {filteredInsights.map((insight) => {
            const typeConfig = TYPE_CONFIG[insight.type] || TYPE_CONFIG.theme;
            const statusConfig = STATUS_CONFIG[insight.status] || STATUS_CONFIG.draft;
            const sentimentConfig = SENTIMENT_CONFIG[insight.sentiment];
            const TypeIcon = typeConfig.icon;

            return (
              <Card key={insight.id} className="card-hover" data-testid={`insight-${insight.id}`}>
                <CardContent className="p-4">
                  <div className="flex items-start gap-4">
                    <div className={`p-2 rounded-lg ${typeConfig.color.split(' ')[0]}`}>
                      <TypeIcon className={`w-5 h-5 ${typeConfig.color.split(' ')[1]}`} />
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 flex-wrap mb-2">
                        <Badge className={typeConfig.color}>{typeConfig.label}</Badge>
                        <Badge className={statusConfig.color}>{statusConfig.label}</Badge>
                        {sentimentConfig && (
                          <span className={`text-xs ${sentimentConfig.color}`}>{sentimentConfig.label}</span>
                        )}
                        <span className="text-xs text-muted-foreground ml-auto">
                          Importancia: {insight.importance}/10
                        </span>
                      </div>
                      <p className="text-sm font-medium mb-2">{insight.content}</p>
                      {insight.source_quote && (
                        <blockquote className="text-xs text-muted-foreground italic border-l-2 border-slate-200 pl-3">
                          "{insight.source_quote}"
                        </blockquote>
                      )}
                    </div>
                    {insight.status === 'draft' && (
                      <div className="flex gap-1">
                        <Button size="icon" variant="ghost" className="text-green-600 hover:bg-green-50" onClick={() => handleValidate(insight.id, true)}>
                          <ThumbsUp className="w-4 h-4" />
                        </Button>
                        <Button size="icon" variant="ghost" className="text-red-600 hover:bg-red-50" onClick={() => handleValidate(insight.id, false)}>
                          <ThumbsDown className="w-4 h-4" />
                        </Button>
                      </div>
                    )}
                  </div>
                </CardContent>
              </Card>
            );
          })}
        </div>
      )}
    </div>
  );
};
