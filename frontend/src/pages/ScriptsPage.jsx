import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useScriptStore } from '../stores';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Badge } from '../components/ui/badge';
import { toast } from 'sonner';
import { 
  Search, 
  Plus, 
  FileText, 
  Clock,
  Copy,
  Edit,
  MoreVertical,
  ListOrdered
} from 'lucide-react';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '../components/ui/dropdown-menu';

export const ScriptsPage = () => {
  const navigate = useNavigate();
  const { scripts, fetchScripts, duplicateScript, isLoading } = useScriptStore();
  const [searchTerm, setSearchTerm] = useState('');

  useEffect(() => {
    fetchScripts();
  }, [fetchScripts]);

  const filteredScripts = scripts.filter(script =>
    script.name?.toLowerCase().includes(searchTerm.toLowerCase()) ||
    script.objective?.toLowerCase().includes(searchTerm.toLowerCase())
  );

  const handleDuplicate = async (scriptId, e) => {
    e.stopPropagation();
    const result = await duplicateScript(scriptId);
    if (result.success) {
      toast.success('Guión duplicado exitosamente');
    } else {
      toast.error(result.error || 'Error al duplicar');
    }
  };

  return (
    <div className="space-y-6" data-testid="scripts-page">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
        <div>
          <h1 className="text-3xl font-bold font-['Outfit'] tracking-tight">Guiones</h1>
          <p className="text-muted-foreground mt-1">
            Gestiona los guiones conversacionales para las campañas
          </p>
        </div>
        <Button 
          onClick={() => navigate('/scripts/new')}
          className="bg-secondary hover:bg-secondary/90 text-white"
          data-testid="create-script-btn"
        >
          <Plus className="w-4 h-4 mr-2" />
          Nuevo Guión
        </Button>
      </div>

      {/* Search */}
      <div className="relative max-w-md">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
        <Input
          placeholder="Buscar guiones..."
          value={searchTerm}
          onChange={(e) => setSearchTerm(e.target.value)}
          className="pl-10"
          data-testid="search-scripts"
        />
      </div>

      {/* Scripts Grid */}
      {filteredScripts.length === 0 ? (
        <Card className="border-dashed">
          <CardContent className="flex flex-col items-center justify-center py-16">
            <div className="p-4 rounded-full bg-muted mb-4">
              <FileText className="w-8 h-8 text-muted-foreground" />
            </div>
            <h3 className="font-medium text-lg">No hay guiones</h3>
            <p className="text-muted-foreground text-center mt-1 max-w-sm">
              Crea tu primer guión para estructurar las conversaciones de VAL
            </p>
            <Button 
              className="mt-4 bg-secondary hover:bg-secondary/90 text-white"
              onClick={() => navigate('/scripts/new')}
            >
              <Plus className="w-4 h-4 mr-2" />
              Crear Guión
            </Button>
          </CardContent>
        </Card>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {filteredScripts.map((script) => (
            <Card 
              key={script.id} 
              className="card-hover cursor-pointer group"
              onClick={() => navigate(`/scripts/${script.id}`)}
              data-testid={`script-${script.id}`}
            >
              <CardHeader className="pb-2">
                <div className="flex items-start justify-between">
                  <CardTitle className="text-lg font-['Outfit'] line-clamp-1 group-hover:text-orange-500 transition-colors">
                    {script.name}
                  </CardTitle>
                  <DropdownMenu>
                    <DropdownMenuTrigger asChild onClick={(e) => e.stopPropagation()}>
                      <Button variant="ghost" size="icon" className="h-8 w-8">
                        <MoreVertical className="w-4 h-4" />
                      </Button>
                    </DropdownMenuTrigger>
                    <DropdownMenuContent align="end">
                      <DropdownMenuItem onClick={(e) => { e.stopPropagation(); navigate(`/scripts/${script.id}`); }}>
                        <Edit className="w-4 h-4 mr-2" />
                        Editar
                      </DropdownMenuItem>
                      <DropdownMenuItem onClick={(e) => handleDuplicate(script.id, e)}>
                        <Copy className="w-4 h-4 mr-2" />
                        Duplicar
                      </DropdownMenuItem>
                    </DropdownMenuContent>
                  </DropdownMenu>
                </div>
                <CardDescription className="line-clamp-2 min-h-[40px]">
                  {script.objective || 'Sin objetivo definido'}
                </CardDescription>
              </CardHeader>
              <CardContent>
                <div className="flex items-center gap-4 text-sm text-muted-foreground">
                  <div className="flex items-center gap-1.5">
                    <ListOrdered className="w-4 h-4" />
                    <span>{script.steps?.length || 0} pasos</span>
                  </div>
                  <div className="flex items-center gap-1.5">
                    <Clock className="w-4 h-4" />
                    <span>{script.estimated_duration_minutes || 15} min</span>
                  </div>
                </div>
                <div className="flex items-center gap-2 mt-3">
                  <Badge variant="outline" className="text-xs">
                    v{script.version || 1}
                  </Badge>
                  {script.is_active && (
                    <Badge className="bg-green-100 text-green-700 text-xs">Activo</Badge>
                  )}
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
};
