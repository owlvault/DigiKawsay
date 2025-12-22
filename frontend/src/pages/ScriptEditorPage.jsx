import React, { useState, useEffect } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { useScriptStore } from '../stores';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Textarea } from '../components/ui/textarea';
import { Label } from '../components/ui/label';
import { Switch } from '../components/ui/switch';
import { Badge } from '../components/ui/badge';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../components/ui/select';
import { toast } from 'sonner';
import { 
  ArrowLeft, 
  Save,
  Plus,
  Trash2,
  GripVertical,
  MessageSquare,
  Target,
  Clock,
  History
} from 'lucide-react';

export const ScriptEditorPage = () => {
  const navigate = useNavigate();
  const { scriptId } = useParams();
  const { currentScript, getScript, createScript, updateScript, getVersions, versions, isLoading } = useScriptStore();
  
  const isEditing = scriptId && scriptId !== 'new';
  
  const [formData, setFormData] = useState({
    name: '',
    description: '',
    objective: '',
    welcome_message: '',
    closing_message: '',
    estimated_duration_minutes: 15,
    steps: []
  });

  const [showVersions, setShowVersions] = useState(false);

  useEffect(() => {
    if (isEditing) {
      loadScript();
    }
  }, [scriptId]);

  const loadScript = async () => {
    const script = await getScript(scriptId);
    if (script) {
      setFormData({
        name: script.name || '',
        description: script.description || '',
        objective: script.objective || '',
        welcome_message: script.welcome_message || '',
        closing_message: script.closing_message || '',
        estimated_duration_minutes: script.estimated_duration_minutes || 15,
        steps: script.steps || []
      });
      getVersions(scriptId);
    }
  };

  const handleAddStep = () => {
    const newStep = {
      id: `step-${Date.now()}`,
      order: formData.steps.length + 1,
      question: '',
      description: '',
      type: 'open',
      options: [],
      is_required: true,
      follow_up_prompt: ''
    };
    setFormData({ ...formData, steps: [...formData.steps, newStep] });
  };

  const handleUpdateStep = (index, field, value) => {
    const updatedSteps = [...formData.steps];
    updatedSteps[index] = { ...updatedSteps[index], [field]: value };
    setFormData({ ...formData, steps: updatedSteps });
  };

  const handleRemoveStep = (index) => {
    const updatedSteps = formData.steps.filter((_, i) => i !== index);
    // Reorder steps
    updatedSteps.forEach((step, i) => step.order = i + 1);
    setFormData({ ...formData, steps: updatedSteps });
  };

  const handleMoveStep = (index, direction) => {
    const newIndex = direction === 'up' ? index - 1 : index + 1;
    if (newIndex < 0 || newIndex >= formData.steps.length) return;
    
    const updatedSteps = [...formData.steps];
    [updatedSteps[index], updatedSteps[newIndex]] = [updatedSteps[newIndex], updatedSteps[index]];
    updatedSteps.forEach((step, i) => step.order = i + 1);
    setFormData({ ...formData, steps: updatedSteps });
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    
    if (!formData.name.trim()) {
      toast.error('El nombre del guión es requerido');
      return;
    }
    if (!formData.objective.trim()) {
      toast.error('El objetivo del guión es requerido');
      return;
    }

    const result = isEditing 
      ? await updateScript(scriptId, formData)
      : await createScript(formData);

    if (result.success) {
      toast.success(isEditing ? '¡Guión actualizado!' : '¡Guión creado!');
      if (!isEditing) {
        navigate(`/scripts/${result.data.id}`);
      }
    } else {
      toast.error(result.error || 'Error al guardar');
    }
  };

  return (
    <div className="max-w-4xl mx-auto space-y-6" data-testid="script-editor-page">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <Button 
            variant="ghost" 
            size="icon"
            onClick={() => navigate('/scripts')}
            data-testid="back-btn"
          >
            <ArrowLeft className="w-5 h-5" />
          </Button>
          <div>
            <h1 className="text-3xl font-bold font-['Outfit'] tracking-tight">
              {isEditing ? 'Editar Guión' : 'Nuevo Guión'}
            </h1>
            {isEditing && currentScript && (
              <div className="flex items-center gap-2 mt-1">
                <Badge variant="outline">v{currentScript.version || 1}</Badge>
                <Button 
                  variant="ghost" 
                  size="sm" 
                  onClick={() => setShowVersions(!showVersions)}
                  className="h-6 text-xs"
                >
                  <History className="w-3 h-3 mr-1" />
                  Historial
                </Button>
              </div>
            )}
          </div>
        </div>
        <Button 
          onClick={handleSubmit}
          className="bg-secondary hover:bg-secondary/90 text-white"
          disabled={isLoading}
          data-testid="save-script-btn"
        >
          <Save className="w-4 h-4 mr-2" />
          {isLoading ? 'Guardando...' : 'Guardar'}
        </Button>
      </div>

      {/* Version History */}
      {showVersions && versions.length > 0 && (
        <Card className="bg-slate-50">
          <CardHeader className="py-3">
            <CardTitle className="text-sm">Historial de Versiones</CardTitle>
          </CardHeader>
          <CardContent className="py-2">
            <div className="space-y-2">
              {versions.map((v) => (
                <div key={v.id} className="flex items-center justify-between text-sm p-2 bg-white rounded">
                  <span>Versión {v.version}</span>
                  <span className="text-muted-foreground text-xs">
                    {new Date(v.created_at).toLocaleDateString('es')}
                  </span>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      <form onSubmit={handleSubmit} className="space-y-6">
        {/* Basic Info */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2 font-['Outfit']">
              <Target className="w-5 h-5 text-orange-500" />
              Información del Guión
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label htmlFor="name">Nombre *</Label>
                <Input
                  id="name"
                  placeholder="Ej: Entrevista de Clima Organizacional"
                  value={formData.name}
                  onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                  data-testid="script-name"
                  required
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="duration">Duración estimada (minutos)</Label>
                <Input
                  id="duration"
                  type="number"
                  min={5}
                  max={120}
                  value={formData.estimated_duration_minutes}
                  onChange={(e) => setFormData({ ...formData, estimated_duration_minutes: parseInt(e.target.value) || 15 })}
                  data-testid="script-duration"
                />
              </div>
            </div>
            <div className="space-y-2">
              <Label htmlFor="objective">Objetivo *</Label>
              <Textarea
                id="objective"
                placeholder="¿Qué se busca explorar con este guión?"
                value={formData.objective}
                onChange={(e) => setFormData({ ...formData, objective: e.target.value })}
                data-testid="script-objective"
                rows={2}
                required
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="description">Descripción</Label>
              <Textarea
                id="description"
                placeholder="Descripción opcional del guión..."
                value={formData.description}
                onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                rows={2}
              />
            </div>
          </CardContent>
        </Card>

        {/* Messages */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2 font-['Outfit']">
              <MessageSquare className="w-5 h-5 text-orange-500" />
              Mensajes de VAL
            </CardTitle>
            <CardDescription>
              Mensajes de bienvenida y cierre que VAL usará en las sesiones
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="welcome">Mensaje de Bienvenida</Label>
              <Textarea
                id="welcome"
                placeholder="¡Hola! Gracias por participar en esta conversación..."
                value={formData.welcome_message}
                onChange={(e) => setFormData({ ...formData, welcome_message: e.target.value })}
                rows={3}
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="closing">Mensaje de Cierre</Label>
              <Textarea
                id="closing"
                placeholder="Gracias por compartir tu experiencia..."
                value={formData.closing_message}
                onChange={(e) => setFormData({ ...formData, closing_message: e.target.value })}
                rows={3}
              />
            </div>
          </CardContent>
        </Card>

        {/* Steps */}
        <Card>
          <CardHeader>
            <div className="flex items-center justify-between">
              <div>
                <CardTitle className="flex items-center gap-2 font-['Outfit']">
                  <Clock className="w-5 h-5 text-orange-500" />
                  Preguntas del Guión
                </CardTitle>
                <CardDescription>
                  Define las preguntas que guiarán la conversación
                </CardDescription>
              </div>
              <Button 
                type="button"
                variant="outline"
                onClick={handleAddStep}
                data-testid="add-step-btn"
              >
                <Plus className="w-4 h-4 mr-2" />
                Agregar Pregunta
              </Button>
            </div>
          </CardHeader>
          <CardContent className="space-y-4">
            {formData.steps.length === 0 ? (
              <div className="text-center py-8 text-muted-foreground">
                <p>No hay preguntas definidas</p>
                <p className="text-sm">Agrega preguntas para estructurar el diálogo</p>
              </div>
            ) : (
              formData.steps.map((step, index) => (
                <Card key={step.id} className="bg-slate-50" data-testid={`step-${index}`}>
                  <CardContent className="p-4">
                    <div className="flex items-start gap-3">
                      <div className="flex flex-col items-center gap-1 pt-2">
                        <Button 
                          type="button"
                          variant="ghost" 
                          size="icon" 
                          className="h-6 w-6"
                          onClick={() => handleMoveStep(index, 'up')}
                          disabled={index === 0}
                        >
                          <GripVertical className="w-4 h-4" />
                        </Button>
                        <Badge variant="outline" className="text-xs">{step.order}</Badge>
                      </div>
                      <div className="flex-1 space-y-3">
                        <div className="space-y-2">
                          <Label>Pregunta *</Label>
                          <Textarea
                            placeholder="¿Cómo describirías tu experiencia...?"
                            value={step.question}
                            onChange={(e) => handleUpdateStep(index, 'question', e.target.value)}
                            rows={2}
                          />
                        </div>
                        <div className="grid grid-cols-2 gap-3">
                          <div className="space-y-2">
                            <Label>Tipo</Label>
                            <Select
                              value={step.type}
                              onValueChange={(value) => handleUpdateStep(index, 'type', value)}
                            >
                              <SelectTrigger>
                                <SelectValue />
                              </SelectTrigger>
                              <SelectContent>
                                <SelectItem value="open">Abierta</SelectItem>
                                <SelectItem value="scale">Escala (1-10)</SelectItem>
                                <SelectItem value="multiple_choice">Opción Múltiple</SelectItem>
                              </SelectContent>
                            </Select>
                          </div>
                          <div className="flex items-center gap-2 pt-6">
                            <Switch
                              checked={step.is_required}
                              onCheckedChange={(checked) => handleUpdateStep(index, 'is_required', checked)}
                            />
                            <Label className="text-sm">Requerida</Label>
                          </div>
                        </div>
                        <div className="space-y-2">
                          <Label>Prompt de seguimiento (opcional)</Label>
                          <Input
                            placeholder="Si el participante menciona X, profundizar en..."
                            value={step.follow_up_prompt || ''}
                            onChange={(e) => handleUpdateStep(index, 'follow_up_prompt', e.target.value)}
                          />
                        </div>
                      </div>
                      <Button 
                        type="button"
                        variant="ghost" 
                        size="icon"
                        className="text-red-500 hover:text-red-600 hover:bg-red-50"
                        onClick={() => handleRemoveStep(index)}
                      >
                        <Trash2 className="w-4 h-4" />
                      </Button>
                    </div>
                  </CardContent>
                </Card>
              ))
            )}
          </CardContent>
        </Card>
      </form>
    </div>
  );
};
