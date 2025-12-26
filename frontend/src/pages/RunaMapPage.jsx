import React, { useEffect, useState, useCallback, useMemo } from 'react';
import ReactFlow, {
  Background,
  Controls,
  MiniMap,
  useNodesState,
  useEdgesState,
  MarkerType,
  Panel,
} from 'reactflow';
import { forceSimulation, forceLink, forceManyBody, forceCenter, forceCollide } from 'd3-force';
import 'reactflow/dist/style.css';
import { useAuthStore } from '../stores';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Badge } from '../components/ui/badge';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../components/ui/select';
import { Switch } from '../components/ui/switch';
import { Label } from '../components/ui/label';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../components/ui/tabs';
import { Progress } from '../components/ui/progress';
import { ScrollArea } from '../components/ui/scroll-area';
import { toast } from 'sonner';
import {
  Network, RefreshCw, Users, Tag, Zap, Eye, Target,
  TrendingUp, GitBranch, Layers, Download, Save
} from 'lucide-react';
import axios from 'axios';

// Node type colors
const NODE_COLORS = {
  participant: { bg: '#3b82f6', border: '#1d4ed8', text: '#ffffff' },
  theme: { bg: '#10b981', border: '#059669', text: '#ffffff' },
  tension: { bg: '#f59e0b', border: '#d97706', text: '#ffffff' },
  symbol: { bg: '#8b5cf6', border: '#7c3aed', text: '#ffffff' },
  category: { bg: '#6366f1', border: '#4f46e5', text: '#ffffff' },
};

// Edge type colors
const EDGE_COLORS = {
  habla_de: '#94a3b8',
  co_ocurre: '#22c55e',
  comparte_tema: '#3b82f6',
  consulta: '#f59e0b',
  colabora: '#ec4899',
};

// Custom Node Component
const CustomNode = ({ data }) => {
  const colors = NODE_COLORS[data.nodeType] || NODE_COLORS.category;
  const size = Math.max(40, Math.min(80, 40 + (data.degree || 0) * 5));
  
  return (
    <div
      className="flex items-center justify-center rounded-full shadow-lg transition-all hover:scale-110 cursor-pointer"
      style={{
        width: size,
        height: size,
        backgroundColor: colors.bg,
        border: `3px solid ${colors.border}`,
        color: colors.text,
      }}
      title={`${data.label}\nTipo: ${data.nodeType}\nBetweenness: ${data.betweenness?.toFixed(3) || 0}`}
    >
      <span className="text-xs font-medium text-center px-1 truncate max-w-full">
        {data.label?.slice(0, 8)}
      </span>
    </div>
  );
};

const nodeTypes = { custom: CustomNode };

export const RunaMapPage = () => {
  const { user } = useAuthStore();
  const [campaigns, setCampaigns] = useState([]);
  const [selectedCampaign, setSelectedCampaign] = useState('');
  const [loading, setLoading] = useState(false);
  const [graphData, setGraphData] = useState({ nodes: [], edges: [], metrics: null });
  
  // Filters
  const [includeParticipantTheme, setIncludeParticipantTheme] = useState(true);
  const [includeThemeCooccurrence, setIncludeThemeCooccurrence] = useState(true);
  const [includeParticipantSimilarity, setIncludeParticipantSimilarity] = useState(true);
  const [minEdgeWeight, setMinEdgeWeight] = useState(1);
  
  // React Flow state
  const [nodes, setNodes, onNodesChange] = useNodesState([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState([]);
  
  // Selected node for details
  const [selectedNode, setSelectedNode] = useState(null);

  useEffect(() => {
    fetchCampaigns();
  }, []);

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

  const applyD3ForceLayout = useCallback((rawNodes, rawEdges) => {
    if (rawNodes.length === 0) return { nodes: [], edges: [] };

    console.log('=== D3 Force Layout Debug ===');
    console.log('Raw nodes:', rawNodes.length);
    console.log('Raw edges:', rawEdges.length);
    if (rawEdges.length > 0) {
      console.log('First edge:', JSON.stringify(rawEdges[0]));
    }

    // Store original source/target IDs before D3 mutates them
    const edgeSourceTargetMap = new Map();
    rawEdges.forEach(edge => {
      const sourceId = edge.source || edge.source_node_id;
      const targetId = edge.target || edge.target_node_id;
      edgeSourceTargetMap.set(edge.id, { source: sourceId, target: targetId });
      console.log(`Edge ${edge.id.slice(0,8)}: source=${sourceId?.slice(0,8)}, target=${targetId?.slice(0,8)}`);
    });

    // Create copies for D3 to avoid mutating original data
    const nodesCopy = rawNodes.map(n => ({ ...n }));
    const edgesCopy = rawEdges.map(e => ({ 
      ...e,
      source: e.source || e.source_node_id,
      target: e.target || e.target_node_id
    }));

    const simulation = forceSimulation(nodesCopy)
      .force('link', forceLink(edgesCopy)
        .id(d => d.id)
        .distance(150)
        .strength(d => Math.min(1, (d.weight || 1) / 5))
      )
      .force('charge', forceManyBody().strength(-300))
      .force('center', forceCenter(400, 300))
      .force('collision', forceCollide().radius(60))
      .stop();

    // Run simulation
    for (let i = 0; i < 300; i++) simulation.tick();

    // Convert to React Flow format
    const flowNodes = nodesCopy.map(node => ({
      id: node.id,
      type: 'custom',
      position: { x: node.x || 0, y: node.y || 0 },
      data: {
        label: node.label,
        nodeType: node.node_type,
        betweenness: node.betweenness,
        degree: node.degree_in,
        clustering: node.clustering_coef,
        communityId: node.community_id,
        metadata: node.metadata,
      },
    }));

    // Use the stored original IDs for edges
    const flowEdges = rawEdges.map(edge => {
      const originalIds = edgeSourceTargetMap.get(edge.id);
      return {
        id: edge.id,
        source: originalIds.source,
        target: originalIds.target,
        type: 'default',
        animated: edge.edge_type === 'comparte_tema',
        style: {
          stroke: EDGE_COLORS[edge.edge_type] || '#94a3b8',
          strokeWidth: Math.min(5, Math.max(1, edge.weight || 1)),
        },
        markerEnd: edge.edge_type === 'habla_de' ? {
          type: MarkerType.ArrowClosed,
          color: EDGE_COLORS[edge.edge_type],
        } : undefined,
        label: (edge.weight || 1) > 1 ? String(edge.weight) : undefined,
        labelStyle: { fontSize: 10 },
      };
    });

    return { nodes: flowNodes, edges: flowEdges };
  }, []);

  const fetchNetworkData = async () => {
    if (!selectedCampaign) return;
    
    setLoading(true);
    try {
      const params = new URLSearchParams({
        include_participant_theme: includeParticipantTheme,
        include_theme_cooccurrence: includeThemeCooccurrence,
        include_participant_similarity: includeParticipantSimilarity,
        min_edge_weight: minEdgeWeight,
      });
      
      const res = await axios.get(`/network/campaign/${selectedCampaign}?${params}`);
      setGraphData(res.data);
      
      // Apply D3 force layout
      const { nodes: flowNodes, edges: flowEdges } = applyD3ForceLayout(
        res.data.nodes,
        res.data.edges
      );
      
      setNodes(flowNodes);
      setEdges(flowEdges);
      
      if (res.data.nodes.length === 0) {
        toast.info('No hay datos suficientes para generar la red');
      } else {
        toast.success(`Red generada: ${res.data.nodes.length} nodos, ${res.data.edges.length} conexiones`);
      }
    } catch (error) {
      console.error('Error fetching network:', error);
      toast.error('Error al generar la red');
    }
    setLoading(false);
  };

  const onNodeClick = useCallback((event, node) => {
    setSelectedNode(node);
  }, []);

  const handleSaveSnapshot = async () => {
    if (!selectedCampaign) return;
    
    try {
      const res = await axios.post('/network/generate', {
        campaign_id: selectedCampaign,
        include_participant_theme: includeParticipantTheme,
        include_theme_cooccurrence: includeThemeCooccurrence,
        include_participant_similarity: includeParticipantSimilarity,
        min_edge_weight: minEdgeWeight,
        snapshot_name: `Snapshot ${new Date().toLocaleDateString('es')}`,
      });
      toast.success(`Snapshot guardado: ${res.data.snapshot_id?.slice(0, 8)}`);
    } catch (error) {
      toast.error('Error al guardar snapshot');
    }
  };

  const metrics = graphData.metrics;

  // Access control
  if (!['admin', 'facilitator', 'analyst'].includes(user?.role)) {
    return (
      <div className="flex items-center justify-center h-64">
        <Card className="max-w-md">
          <CardContent className="p-8 text-center">
            <Network className="w-12 h-12 mx-auto mb-4 text-muted-foreground" />
            <h3 className="font-medium text-lg">Acceso Restringido</h3>
            <p className="text-muted-foreground mt-2">
              Solo administradores, facilitadores y analistas pueden acceder a RunaMap
            </p>
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className="space-y-6" data-testid="runamap-page">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold font-['Outfit'] tracking-tight flex items-center gap-3">
            <Network className="w-8 h-8 text-primary" />
            RunaMap
          </h1>
          <p className="text-muted-foreground mt-1">
            Análisis de Redes Sociales - Visualiza conexiones y detecta patrones
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Button variant="outline" onClick={handleSaveSnapshot} disabled={nodes.length === 0}>
            <Save className="w-4 h-4 mr-2" />
            Guardar Snapshot
          </Button>
          <Button onClick={fetchNetworkData} disabled={loading || !selectedCampaign}>
            <RefreshCw className={`w-4 h-4 mr-2 ${loading ? 'animate-spin' : ''}`} />
            Generar Red
          </Button>
        </div>
      </div>

      {/* Controls Row */}
      <Card>
        <CardContent className="p-4">
          <div className="flex flex-wrap items-center gap-6">
            <div className="flex items-center gap-2">
              <Label>Campaña:</Label>
              <Select value={selectedCampaign} onValueChange={setSelectedCampaign}>
                <SelectTrigger className="w-[250px]">
                  <SelectValue placeholder="Seleccionar campaña" />
                </SelectTrigger>
                <SelectContent>
                  {campaigns.map(c => (
                    <SelectItem key={c.id} value={c.id}>{c.name}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            
            <div className="flex items-center gap-2">
              <Switch
                id="participant-theme"
                checked={includeParticipantTheme}
                onCheckedChange={setIncludeParticipantTheme}
              />
              <Label htmlFor="participant-theme" className="text-sm">Participante↔Tema</Label>
            </div>
            
            <div className="flex items-center gap-2">
              <Switch
                id="theme-cooccurrence"
                checked={includeThemeCooccurrence}
                onCheckedChange={setIncludeThemeCooccurrence}
              />
              <Label htmlFor="theme-cooccurrence" className="text-sm">Tema↔Tema</Label>
            </div>
            
            <div className="flex items-center gap-2">
              <Switch
                id="participant-similarity"
                checked={includeParticipantSimilarity}
                onCheckedChange={setIncludeParticipantSimilarity}
              />
              <Label htmlFor="participant-similarity" className="text-sm">Participante↔Participante</Label>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Main Content */}
      <div className="grid grid-cols-1 lg:grid-cols-4 gap-4">
        {/* Graph View */}
        <Card className="lg:col-span-3">
          <CardContent className="p-0">
            <div className="h-[600px] bg-slate-50 rounded-lg">
              {nodes.length > 0 ? (
                <ReactFlow
                  nodes={nodes}
                  edges={edges}
                  onNodesChange={onNodesChange}
                  onEdgesChange={onEdgesChange}
                  onNodeClick={onNodeClick}
                  nodeTypes={nodeTypes}
                  fitView
                  attributionPosition="bottom-left"
                >
                  <Background color="#e2e8f0" gap={16} />
                  <Controls />
                  <MiniMap
                    nodeColor={node => NODE_COLORS[node.data?.nodeType]?.bg || '#6b7280'}
                    maskColor="rgba(0,0,0,0.1)"
                  />
                  <Panel position="top-left" className="bg-white/90 p-3 rounded-lg shadow-sm">
                    <div className="flex flex-wrap gap-3 text-xs">
                      <div className="flex items-center gap-1">
                        <div className="w-3 h-3 rounded-full" style={{ backgroundColor: NODE_COLORS.participant.bg }} />
                        <span>Participante</span>
                      </div>
                      <div className="flex items-center gap-1">
                        <div className="w-3 h-3 rounded-full" style={{ backgroundColor: NODE_COLORS.theme.bg }} />
                        <span>Tema</span>
                      </div>
                      <div className="flex items-center gap-1">
                        <div className="w-3 h-3 rounded-full" style={{ backgroundColor: NODE_COLORS.tension.bg }} />
                        <span>Tensión</span>
                      </div>
                      <div className="flex items-center gap-1">
                        <div className="w-3 h-3 rounded-full" style={{ backgroundColor: NODE_COLORS.symbol.bg }} />
                        <span>Símbolo</span>
                      </div>
                    </div>
                  </Panel>
                </ReactFlow>
              ) : (
                <div className="h-full flex items-center justify-center text-muted-foreground">
                  <div className="text-center">
                    <Network className="w-16 h-16 mx-auto mb-4 opacity-30" />
                    <p className="text-lg font-medium">Sin datos de red</p>
                    <p className="text-sm">Selecciona una campaña y genera la red</p>
                  </div>
                </div>
              )}
            </div>
          </CardContent>
        </Card>

        {/* Metrics Panel */}
        <div className="space-y-4">
          {/* Network Stats */}
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-sm font-['Outfit']">Métricas de Red</CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              <div className="grid grid-cols-2 gap-2">
                <div className="p-2 bg-slate-50 rounded text-center">
                  <p className="text-2xl font-bold text-primary">{metrics?.total_nodes || 0}</p>
                  <p className="text-xs text-muted-foreground">Nodos</p>
                </div>
                <div className="p-2 bg-slate-50 rounded text-center">
                  <p className="text-2xl font-bold text-green-600">{metrics?.total_edges || 0}</p>
                  <p className="text-xs text-muted-foreground">Conexiones</p>
                </div>
              </div>
              
              <div className="space-y-1">
                <div className="flex justify-between text-sm">
                  <span>Densidad</span>
                  <span className="font-medium">{((metrics?.density || 0) * 100).toFixed(1)}%</span>
                </div>
                <Progress value={(metrics?.density || 0) * 100} className="h-2" />
              </div>
              
              <div className="space-y-1">
                <div className="flex justify-between text-sm">
                  <span>Clustering Promedio</span>
                  <span className="font-medium">{((metrics?.avg_clustering || 0) * 100).toFixed(1)}%</span>
                </div>
                <Progress value={(metrics?.avg_clustering || 0) * 100} className="h-2" />
              </div>
              
              <div className="flex items-center justify-between pt-2 border-t">
                <span className="text-sm flex items-center gap-1">
                  <Layers className="w-4 h-4" />
                  Comunidades
                </span>
                <Badge variant="secondary">{metrics?.num_communities || 0}</Badge>
              </div>
            </CardContent>
          </Card>

          {/* Top Brokers */}
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-sm font-['Outfit'] flex items-center gap-2">
                <Target className="w-4 h-4 text-orange-500" />
                Top Brokers
              </CardTitle>
              <CardDescription className="text-xs">
                Nodos con alta centralidad de intermediación
              </CardDescription>
            </CardHeader>
            <CardContent>
              <ScrollArea className="h-[200px]">
                {metrics?.top_brokers?.length > 0 ? (
                  <div className="space-y-2">
                    {metrics.top_brokers.map((broker, idx) => (
                      <div 
                        key={broker.node_id}
                        className="flex items-center gap-2 p-2 bg-slate-50 rounded hover:bg-slate-100 transition-colors"
                      >
                        <span className="text-xs font-bold text-muted-foreground w-5">
                          #{idx + 1}
                        </span>
                        <div
                          className="w-3 h-3 rounded-full"
                          style={{ backgroundColor: NODE_COLORS[broker.node_type]?.bg || '#6b7280' }}
                        />
                        <div className="flex-1 min-w-0">
                          <p className="text-sm font-medium truncate">{broker.label}</p>
                          <p className="text-xs text-muted-foreground">{broker.node_type}</p>
                        </div>
                        <Badge variant="outline" className="text-xs">
                          {(broker.betweenness * 100).toFixed(1)}%
                        </Badge>
                      </div>
                    ))}
                  </div>
                ) : (
                  <p className="text-sm text-muted-foreground text-center py-4">
                    Sin datos de brokers
                  </p>
                )}
              </ScrollArea>
            </CardContent>
          </Card>

          {/* Communities */}
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-sm font-['Outfit'] flex items-center gap-2">
                <GitBranch className="w-4 h-4 text-purple-500" />
                Comunidades Detectadas
              </CardTitle>
            </CardHeader>
            <CardContent>
              <ScrollArea className="h-[150px]">
                {metrics?.communities?.length > 0 ? (
                  <div className="space-y-2">
                    {metrics.communities.map((comm, idx) => (
                      <div 
                        key={comm.id}
                        className="p-2 bg-slate-50 rounded"
                      >
                        <div className="flex items-center justify-between">
                          <span className="text-sm font-medium">Comunidad {comm.id + 1}</span>
                          <Badge variant="secondary">{comm.size} miembros</Badge>
                        </div>
                        <div className="flex flex-wrap gap-1 mt-1">
                          {comm.members?.slice(0, 3).map(m => (
                            <Badge key={m.node_id} variant="outline" className="text-xs">
                              {m.label?.slice(0, 10)}
                            </Badge>
                          ))}
                          {comm.size > 3 && (
                            <Badge variant="outline" className="text-xs">
                              +{comm.size - 3} más
                            </Badge>
                          )}
                        </div>
                      </div>
                    ))}
                  </div>
                ) : (
                  <p className="text-sm text-muted-foreground text-center py-4">
                    Sin comunidades detectadas
                  </p>
                )}
              </ScrollArea>
            </CardContent>
          </Card>

          {/* Selected Node Details */}
          {selectedNode && (
            <Card className="border-primary">
              <CardHeader className="pb-2">
                <CardTitle className="text-sm font-['Outfit'] flex items-center gap-2">
                  <Eye className="w-4 h-4" />
                  Nodo Seleccionado
                </CardTitle>
              </CardHeader>
              <CardContent className="text-sm space-y-2">
                <div className="flex items-center gap-2">
                  <div
                    className="w-4 h-4 rounded-full"
                    style={{ backgroundColor: NODE_COLORS[selectedNode.data?.nodeType]?.bg }}
                  />
                  <span className="font-medium">{selectedNode.data?.label}</span>
                </div>
                <div className="grid grid-cols-2 gap-2 text-xs">
                  <div className="p-1 bg-slate-50 rounded">
                    <p className="text-muted-foreground">Tipo</p>
                    <p className="font-medium">{selectedNode.data?.nodeType}</p>
                  </div>
                  <div className="p-1 bg-slate-50 rounded">
                    <p className="text-muted-foreground">Grado</p>
                    <p className="font-medium">{selectedNode.data?.degree || 0}</p>
                  </div>
                  <div className="p-1 bg-slate-50 rounded">
                    <p className="text-muted-foreground">Betweenness</p>
                    <p className="font-medium">{((selectedNode.data?.betweenness || 0) * 100).toFixed(2)}%</p>
                  </div>
                  <div className="p-1 bg-slate-50 rounded">
                    <p className="text-muted-foreground">Comunidad</p>
                    <p className="font-medium">{selectedNode.data?.communityId ?? '-'}</p>
                  </div>
                </div>
              </CardContent>
            </Card>
          )}
        </div>
      </div>

      {/* Nodes by Type */}
      {metrics && Object.keys(metrics.nodes_by_type || {}).length > 0 && (
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="font-['Outfit']">Distribución de Nodos</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="flex flex-wrap gap-4">
              {Object.entries(metrics.nodes_by_type).map(([type, count]) => (
                <div key={type} className="flex items-center gap-2">
                  <div
                    className="w-4 h-4 rounded-full"
                    style={{ backgroundColor: NODE_COLORS[type]?.bg || '#6b7280' }}
                  />
                  <span className="capitalize">{type}</span>
                  <Badge>{count}</Badge>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
};
