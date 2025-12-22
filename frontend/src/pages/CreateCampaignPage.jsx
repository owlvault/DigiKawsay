import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useCampaignStore } from '../stores';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Textarea } from '../components/ui/textarea';
import { Label } from '../components/ui/label';
import { Calendar } from '../components/ui/calendar';
import { Popover, PopoverContent, PopoverTrigger } from '../components/ui/popover';
import { toast } from 'sonner';
import { format } from 'date-fns';
import { es } from 'date-fns/locale';
import { 
  ArrowLeft, 
  CalendarIcon, 
  Save,
  Target,
  FileText,
  Clock
} from 'lucide-react';
import { cn } from '../lib/utils';

export const CreateCampaignPage = () => {
  const navigate = useNavigate();
  const { createCampaign, isLoading } = useCampaignStore();
  
  const [formData, setFormData] = useState({
    name: '',
    description: '',
    objective: '',
    start_date: null,
    end_date: null
  });

  const handleSubmit = async (e) => {
    e.preventDefault();
    
    if (!formData.name.trim()) {
      toast.error('El nombre de la campaña es requerido');
      return;
    }
    if (!formData.objective.trim()) {
      toast.error('El objetivo de la campaña es requerido');
      return;
    }

    const campaignData = {
      ...formData,
      start_date: formData.start_date?.toISOString(),
      end_date: formData.end_date?.toISOString()
    };

    const result = await createCampaign(campaignData);
    if (result.success) {
      toast.success('¡Campaña creada exitosamente!');
      navigate('/campaigns');
    } else {
      toast.error(result.error || 'Error al crear la campaña');
    }
  };

  return (
    <div className="max-w-3xl mx-auto space-y-6" data-testid="create-campaign-page">
      {/* Header */}
      <div className="flex items-center gap-4">
        <Button 
          variant="ghost" 
          size="icon"
          onClick={() => navigate('/campaigns')}
          data-testid="back-btn"
        >
          <ArrowLeft className="w-5 h-5" />
        </Button>
        <div>
          <h1 className="text-3xl font-bold font-['Outfit'] tracking-tight">Nueva Campaña</h1>
          <p className="text-muted-foreground mt-1">
            Configura una nueva campaña de diálogo facilitado
          </p>
        </div>
      </div>

      <form onSubmit={handleSubmit} className="space-y-6">
        {/* Basic Info */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2 font-['Outfit']">
              <FileText className="w-5 h-5 text-orange-500" />
              Información Básica
            </CardTitle>
            <CardDescription>
              Define el nombre y descripción de tu campaña
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="name">Nombre de la Campaña *</Label>
              <Input
                id="name"
                placeholder="Ej: Diagnóstico Cultural Q4 2024"
                value={formData.name}
                onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                data-testid="campaign-name"
                required
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="description">Descripción</Label>
              <Textarea
                id="description"
                placeholder="Describe brevemente el propósito de esta campaña..."
                value={formData.description}
                onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                data-testid="campaign-description"
                rows={3}
              />
            </div>
          </CardContent>
        </Card>

        {/* Objective */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2 font-['Outfit']">
              <Target className="w-5 h-5 text-orange-500" />
              Objetivo
            </CardTitle>
            <CardDescription>
              El objetivo guiará las conversaciones de VAL con los participantes
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-2">
              <Label htmlFor="objective">Objetivo de la Campaña *</Label>
              <Textarea
                id="objective"
                placeholder="Ej: Explorar las percepciones del equipo sobre la comunicación interdepartamental y identificar oportunidades de mejora en la colaboración."
                value={formData.objective}
                onChange={(e) => setFormData({ ...formData, objective: e.target.value })}
                data-testid="campaign-objective"
                rows={4}
                required
              />
              <p className="text-xs text-muted-foreground">
                Este objetivo será utilizado por VAL para orientar las preguntas y profundizar en los temas relevantes.
              </p>
            </div>
          </CardContent>
        </Card>

        {/* Schedule */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2 font-['Outfit']">
              <Clock className="w-5 h-5 text-orange-500" />
              Programación
            </CardTitle>
            <CardDescription>
              Define las fechas de inicio y fin de la campaña (opcional)
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label>Fecha de Inicio</Label>
                <Popover>
                  <PopoverTrigger asChild>
                    <Button
                      variant="outline"
                      className={cn(
                        "w-full justify-start text-left font-normal",
                        !formData.start_date && "text-muted-foreground"
                      )}
                      data-testid="start-date-btn"
                    >
                      <CalendarIcon className="mr-2 h-4 w-4" />
                      {formData.start_date 
                        ? format(formData.start_date, "PPP", { locale: es })
                        : "Seleccionar fecha"}
                    </Button>
                  </PopoverTrigger>
                  <PopoverContent className="w-auto p-0" align="start">
                    <Calendar
                      mode="single"
                      selected={formData.start_date}
                      onSelect={(date) => setFormData({ ...formData, start_date: date })}
                      initialFocus
                    />
                  </PopoverContent>
                </Popover>
              </div>
              <div className="space-y-2">
                <Label>Fecha de Fin</Label>
                <Popover>
                  <PopoverTrigger asChild>
                    <Button
                      variant="outline"
                      className={cn(
                        "w-full justify-start text-left font-normal",
                        !formData.end_date && "text-muted-foreground"
                      )}
                      data-testid="end-date-btn"
                    >
                      <CalendarIcon className="mr-2 h-4 w-4" />
                      {formData.end_date 
                        ? format(formData.end_date, "PPP", { locale: es })
                        : "Seleccionar fecha"}
                    </Button>
                  </PopoverTrigger>
                  <PopoverContent className="w-auto p-0" align="start">
                    <Calendar
                      mode="single"
                      selected={formData.end_date}
                      onSelect={(date) => setFormData({ ...formData, end_date: date })}
                      disabled={(date) => formData.start_date && date < formData.start_date}
                      initialFocus
                    />
                  </PopoverContent>
                </Popover>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Actions */}
        <div className="flex justify-end gap-3 pt-4">
          <Button 
            type="button" 
            variant="outline"
            onClick={() => navigate('/campaigns')}
          >
            Cancelar
          </Button>
          <Button 
            type="submit"
            className="bg-secondary hover:bg-secondary/90 text-white"
            disabled={isLoading}
            data-testid="submit-campaign"
          >
            <Save className="w-4 h-4 mr-2" />
            {isLoading ? 'Creando...' : 'Crear Campaña'}
          </Button>
        </div>
      </form>
    </div>
  );
};
