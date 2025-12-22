import React, { useState, useEffect } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { useInsightStore, useTaxonomyStore, useCampaignStore } from '../stores';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Textarea } from '../components/ui/textarea';
import { Label } from '../components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../components/ui/select';
import { Slider } from '../components/ui/slider';
import { toast } from 'sonner';
import { ArrowLeft, Save, Lightbulb } from 'lucide-react';

export const CreateInsightPage = () => {
  const { campaignId } = useParams();
  const navigate = useNavigate();
  const { createInsight, isLoading } = useInsightStore();
  const { categories, fetchCategories } = useTaxonomyStore();
  const { currentCampaign, getCampaign } = useCampaignStore();

  const [formData, setFormData] = useState({
    campaign_id: campaignId,
    content: '',
    type: 'theme',
    category_id: '',
    source_quote: '',
    sentiment: 'neutral',
    importance: 5
  });

  useEffect(() => {
    getCampaign(campaignId);
    fetchCategories();
  }, [campaignId]);

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!formData.content.trim()) {
      toast.error('El contenido es requerido');
      return;
    }
    const result = await createInsight(formData);
    if (result.success) {
      toast.success('Insight creado');
      navigate(`/insights/${campaignId}`);
    } else {
      toast.error(result.error || 'Error al crear');
    }
  };

  return (
    <div className="max-w-2xl mx-auto space-y-6" data-testid="create-insight-page">
      <div className="flex items-center gap-4">
        <Button variant="ghost" size="icon" onClick={() => navigate(`/insights/${campaignId}`)}>
          <ArrowLeft className="w-5 h-5" />
        </Button>
        <div>
          <h1 className="text-3xl font-bold font-['Outfit']">Nuevo Hallazgo</h1>
          <p className="text-muted-foreground">{currentCampaign?.name}</p>
        </div>
      </div>

      <form onSubmit={handleSubmit} className="space-y-6">
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2 font-['Outfit']">
              <Lightbulb className="w-5 h-5 text-orange-500" />
              Información del Hallazgo
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="space-y-2">
              <Label>Contenido *</Label>
              <Textarea
                placeholder="Describe el hallazgo identificado..."
                value={formData.content}
                onChange={(e) => setFormData({ ...formData, content: e.target.value })}
                rows={4}
                required
              />
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label>Tipo</Label>
                <Select value={formData.type} onValueChange={(v) => setFormData({ ...formData, type: v })}>
                  <SelectTrigger><SelectValue /></SelectTrigger>
                  <SelectContent>
                    <SelectItem value="theme">Tema</SelectItem>
                    <SelectItem value="tension">Tensión</SelectItem>
                    <SelectItem value="symbol">Símbolo</SelectItem>
                    <SelectItem value="opportunity">Oportunidad</SelectItem>
                    <SelectItem value="risk">Riesgo</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              <div className="space-y-2">
                <Label>Sentimiento</Label>
                <Select value={formData.sentiment} onValueChange={(v) => setFormData({ ...formData, sentiment: v })}>
                  <SelectTrigger><SelectValue /></SelectTrigger>
                  <SelectContent>
                    <SelectItem value="positive">Positivo</SelectItem>
                    <SelectItem value="negative">Negativo</SelectItem>
                    <SelectItem value="neutral">Neutral</SelectItem>
                    <SelectItem value="mixed">Mixto</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </div>

            <div className="space-y-2">
              <Label>Categoría (opcional)</Label>
              <Select value={formData.category_id} onValueChange={(v) => setFormData({ ...formData, category_id: v })}>
                <SelectTrigger><SelectValue placeholder="Seleccionar categoría" /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="">Sin categoría</SelectItem>
                  {categories.map((cat) => (<SelectItem key={cat.id} value={cat.id}>{cat.name}</SelectItem>))}
                </SelectContent>
              </Select>
            </div>

            <div className="space-y-2">
              <Label>Importancia: {formData.importance}/10</Label>
              <Slider
                value={[formData.importance]}
                onValueChange={([v]) => setFormData({ ...formData, importance: v })}
                max={10}
                min={1}
                step={1}
              />
            </div>

            <div className="space-y-2">
              <Label>Cita de evidencia (opcional)</Label>
              <Textarea
                placeholder="Cita textual que respalda este hallazgo..."
                value={formData.source_quote}
                onChange={(e) => setFormData({ ...formData, source_quote: e.target.value })}
                rows={2}
              />
            </div>
          </CardContent>
        </Card>

        <div className="flex justify-end gap-3">
          <Button type="button" variant="outline" onClick={() => navigate(`/insights/${campaignId}`)}>Cancelar</Button>
          <Button type="submit" className="bg-secondary hover:bg-secondary/90 text-white" disabled={isLoading}>
            <Save className="w-4 h-4 mr-2" />
            {isLoading ? 'Guardando...' : 'Guardar Hallazgo'}
          </Button>
        </div>
      </form>
    </div>
  );
};
