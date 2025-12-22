import React, { useEffect, useState } from 'react';
import { useTaxonomyStore } from '../stores';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Badge } from '../components/ui/badge';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../components/ui/select';
import { Dialog, DialogContent, DialogFooter, DialogHeader, DialogTitle } from '../components/ui/dialog';
import { toast } from 'sonner';
import { Plus, Edit, Trash2, Tag, Palette } from 'lucide-react';

const TYPE_CONFIG = {
  theme: { label: 'Tema', color: 'bg-blue-100 text-blue-700' },
  tension: { label: 'Tensión', color: 'bg-red-100 text-red-700' },
  symbol: { label: 'Símbolo', color: 'bg-purple-100 text-purple-700' },
  opportunity: { label: 'Oportunidad', color: 'bg-green-100 text-green-700' },
  risk: { label: 'Riesgo', color: 'bg-orange-100 text-orange-700' }
};

const COLORS = ['#3B82F6', '#EF4444', '#8B5CF6', '#22C55E', '#F97316', '#EC4899', '#14B8A6', '#F59E0B'];

export const TaxonomyPage = () => {
  const { categories, fetchCategories, createCategory, updateCategory, deleteCategory, isLoading } = useTaxonomyStore();
  const [dialog, setDialog] = useState({ open: false, mode: 'create', data: null });
  const [formData, setFormData] = useState({ name: '', type: 'theme', description: '', color: '#3B82F6' });
  const [typeFilter, setTypeFilter] = useState('');

  useEffect(() => { fetchCategories(); }, []);

  const handleOpenCreate = () => {
    setFormData({ name: '', type: 'theme', description: '', color: '#3B82F6' });
    setDialog({ open: true, mode: 'create', data: null });
  };

  const handleOpenEdit = (cat) => {
    setFormData({ name: cat.name, type: cat.type, description: cat.description || '', color: cat.color || '#3B82F6' });
    setDialog({ open: true, mode: 'edit', data: cat });
  };

  const handleSubmit = async () => {
    if (!formData.name.trim()) { toast.error('El nombre es requerido'); return; }
    
    const result = dialog.mode === 'create' 
      ? await createCategory(formData)
      : await updateCategory(dialog.data.id, formData);
    
    if (result.success) {
      toast.success(dialog.mode === 'create' ? 'Categoría creada' : 'Categoría actualizada');
      setDialog({ open: false, mode: 'create', data: null });
    } else {
      toast.error(result.error || 'Error');
    }
  };

  const handleDelete = async (id) => {
    if (!window.confirm('¿Eliminar esta categoría?')) return;
    const result = await deleteCategory(id);
    if (result.success) toast.success('Categoría eliminada');
    else toast.error(result.error);
  };

  const filteredCategories = typeFilter 
    ? categories.filter(c => c.type === typeFilter)
    : categories;

  const groupedCategories = filteredCategories.reduce((acc, cat) => {
    if (!acc[cat.type]) acc[cat.type] = [];
    acc[cat.type].push(cat);
    return acc;
  }, {});

  return (
    <div className="space-y-6" data-testid="taxonomy-page">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold font-['Outfit'] tracking-tight">Taxonomía</h1>
          <p className="text-muted-foreground mt-1">Gestiona las categorías para clasificar hallazgos</p>
        </div>
        <Button className="bg-secondary hover:bg-secondary/90 text-white" onClick={handleOpenCreate}>
          <Plus className="w-4 h-4 mr-2" />
          Nueva Categoría
        </Button>
      </div>

      <div className="flex gap-2">
        <Button variant={typeFilter === '' ? 'default' : 'outline'} size="sm" onClick={() => setTypeFilter('')}>Todas</Button>
        {Object.entries(TYPE_CONFIG).map(([type, config]) => (
          <Button key={type} variant={typeFilter === type ? 'default' : 'outline'} size="sm" onClick={() => setTypeFilter(type)}>
            {config.label}
          </Button>
        ))}
      </div>

      {Object.keys(groupedCategories).length === 0 ? (
        <Card className="border-dashed">
          <CardContent className="flex flex-col items-center justify-center py-16">
            <Tag className="w-12 h-12 text-muted-foreground mb-4" />
            <h3 className="font-medium text-lg">No hay categorías</h3>
            <p className="text-muted-foreground">Crea categorías para clasificar los hallazgos</p>
          </CardContent>
        </Card>
      ) : (
        <div className="space-y-6">
          {Object.entries(groupedCategories).map(([type, cats]) => (
            <div key={type}>
              <h3 className="font-medium mb-3 flex items-center gap-2">
                <Badge className={TYPE_CONFIG[type]?.color}>{TYPE_CONFIG[type]?.label || type}</Badge>
                <span className="text-muted-foreground text-sm">({cats.length})</span>
              </h3>
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
                {cats.map((cat) => (
                  <Card key={cat.id} className="card-hover">
                    <CardContent className="p-4">
                      <div className="flex items-start justify-between">
                        <div className="flex items-center gap-3">
                          <div className="w-4 h-4 rounded" style={{ backgroundColor: cat.color || '#3B82F6' }} />
                          <div>
                            <p className="font-medium">{cat.name}</p>
                            {cat.description && <p className="text-xs text-muted-foreground">{cat.description}</p>}
                          </div>
                        </div>
                        <div className="flex gap-1">
                          <Button size="icon" variant="ghost" className="h-8 w-8" onClick={() => handleOpenEdit(cat)}>
                            <Edit className="w-4 h-4" />
                          </Button>
                          <Button size="icon" variant="ghost" className="h-8 w-8 text-red-500" onClick={() => handleDelete(cat.id)}>
                            <Trash2 className="w-4 h-4" />
                          </Button>
                        </div>
                      </div>
                      <p className="text-xs text-muted-foreground mt-2">{cat.usage_count || 0} usos</p>
                    </CardContent>
                  </Card>
                ))}
              </div>
            </div>
          ))}
        </div>
      )}

      <Dialog open={dialog.open} onOpenChange={(open) => setDialog({ ...dialog, open })}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>{dialog.mode === 'create' ? 'Nueva Categoría' : 'Editar Categoría'}</DialogTitle>
          </DialogHeader>
          <div className="space-y-4 py-4">
            <div className="space-y-2">
              <Label>Nombre *</Label>
              <Input value={formData.name} onChange={(e) => setFormData({ ...formData, name: e.target.value })} placeholder="Nombre de la categoría" />
            </div>
            <div className="space-y-2">
              <Label>Tipo</Label>
              <Select value={formData.type} onValueChange={(v) => setFormData({ ...formData, type: v })}>
                <SelectTrigger><SelectValue /></SelectTrigger>
                <SelectContent>
                  {Object.entries(TYPE_CONFIG).map(([k, v]) => (<SelectItem key={k} value={k}>{v.label}</SelectItem>))}
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-2">
              <Label>Descripción</Label>
              <Input value={formData.description} onChange={(e) => setFormData({ ...formData, description: e.target.value })} placeholder="Descripción opcional" />
            </div>
            <div className="space-y-2">
              <Label>Color</Label>
              <div className="flex gap-2">
                {COLORS.map((color) => (
                  <button
                    key={color}
                    type="button"
                    className={`w-8 h-8 rounded-full border-2 ${formData.color === color ? 'border-slate-900' : 'border-transparent'}`}
                    style={{ backgroundColor: color }}
                    onClick={() => setFormData({ ...formData, color })}
                  />
                ))}
              </div>
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setDialog({ open: false, mode: 'create', data: null })}>Cancelar</Button>
            <Button className="bg-secondary hover:bg-secondary/90 text-white" onClick={handleSubmit} disabled={isLoading}>
              {dialog.mode === 'create' ? 'Crear' : 'Guardar'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
};
