import React, { useState, useEffect, useMemo } from "react";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "../components/ui/card";
import { Button } from "../components/ui/button";
import { Input } from "../components/ui/input";
import { Label } from "../components/ui/label";
import { Badge } from "../components/ui/badge";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "../components/ui/select";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter, DialogDescription } from "../components/ui/dialog";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "../components/ui/table";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "../components/ui/tabs";
import { toast } from "sonner";
import { useAuthStore } from "../stores";
import { 
  Users, UserPlus, Search, Filter, MoreHorizontal, Edit, Trash2, 
  Shield, UserCheck, UserX, Building2, Mail, Lock, RefreshCw,
  Download, Upload, ChevronLeft, ChevronRight
} from "lucide-react";

const API_URL = process.env.REACT_APP_BACKEND_URL;

const ROLES = [
  { value: "admin", label: "Administrador", color: "bg-red-100 text-red-800" },
  { value: "facilitator", label: "Facilitador", color: "bg-blue-100 text-blue-800" },
  { value: "analyst", label: "Analista", color: "bg-purple-100 text-purple-800" },
  { value: "security_officer", label: "Oficial de Seguridad", color: "bg-orange-100 text-orange-800" },
  { value: "privacy_officer", label: "Oficial de Privacidad", color: "bg-green-100 text-green-800" },
  { value: "participant", label: "Participante", color: "bg-gray-100 text-gray-800" },
];

const DEPARTMENTS = [
  "Mercadeo", "Comercial", "Dirección Financiera", "Producción", "Tecnología",
  "Gestión Humana", "Dirección General", "Legal", "Operaciones", "Calidad"
];

export function UsersAdminPage() {
  const { token, user: currentUser } = useAuthStore();
  const [users, setUsers] = useState([]);
  const [filteredUsers, setFilteredUsers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState("");
  const [filterRole, setFilterRole] = useState("all");
  const [filterDepartment, setFilterDepartment] = useState("all");
  const [filterStatus, setFilterStatus] = useState("all");
  
  // Pagination
  const [currentPage, setCurrentPage] = useState(1);
  const itemsPerPage = 15;
  
  // Dialogs
  const [showCreateDialog, setShowCreateDialog] = useState(false);
  const [showEditDialog, setShowEditDialog] = useState(false);
  const [showDeleteDialog, setShowDeleteDialog] = useState(false);
  const [selectedUser, setSelectedUser] = useState(null);
  
  // Form state
  const [formData, setFormData] = useState({
    email: "",
    full_name: "",
    password: "",
    role: "participant",
    department: "",
    position: "",
    is_active: true
  });

  // Stats
  const stats = useMemo(() => {
    const total = users.length;
    const active = users.filter(u => u.is_active).length;
    const byRole = ROLES.map(r => ({
      ...r,
      count: users.filter(u => u.role === r.value).length
    }));
    const departments = [...new Set(users.map(u => u.department).filter(Boolean))];
    return { total, active, inactive: total - active, byRole, departments };
  }, [users]);

  useEffect(() => {
    fetchUsers();
  }, []);

  useEffect(() => {
    filterUsers();
  }, [users, searchTerm, filterRole, filterDepartment, filterStatus]);

  const fetchUsers = async () => {
    setLoading(true);
    try {
      const res = await fetch(`${API_URL}/api/users/`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      if (res.ok) {
        const data = await res.json();
        setUsers(data);
      }
    } catch (error) {
      toast.error("Error al cargar usuarios");
    } finally {
      setLoading(false);
    }
  };

  const filterUsers = () => {
    let filtered = [...users];
    
    if (searchTerm) {
      const term = searchTerm.toLowerCase();
      filtered = filtered.filter(u => 
        u.full_name?.toLowerCase().includes(term) ||
        u.email?.toLowerCase().includes(term) ||
        u.department?.toLowerCase().includes(term) ||
        u.position?.toLowerCase().includes(term)
      );
    }
    
    if (filterRole !== "all") {
      filtered = filtered.filter(u => u.role === filterRole);
    }
    
    if (filterDepartment !== "all") {
      filtered = filtered.filter(u => u.department === filterDepartment);
    }
    
    if (filterStatus !== "all") {
      filtered = filtered.filter(u => 
        filterStatus === "active" ? u.is_active : !u.is_active
      );
    }
    
    setFilteredUsers(filtered);
    setCurrentPage(1);
  };

  const paginatedUsers = useMemo(() => {
    const start = (currentPage - 1) * itemsPerPage;
    return filteredUsers.slice(start, start + itemsPerPage);
  }, [filteredUsers, currentPage]);

  const totalPages = Math.ceil(filteredUsers.length / itemsPerPage);

  const handleCreateUser = async () => {
    try {
      const res = await fetch(`${API_URL}/api/users/`, {
        method: "POST",
        headers: {
          Authorization: `Bearer ${token}`,
          "Content-Type": "application/json"
        },
        body: JSON.stringify(formData)
      });
      
      if (res.ok) {
        toast.success("Usuario creado exitosamente");
        setShowCreateDialog(false);
        resetForm();
        fetchUsers();
      } else {
        const error = await res.json();
        toast.error(error.detail || "Error al crear usuario");
      }
    } catch (error) {
      toast.error("Error de conexión");
    }
  };

  const handleUpdateUser = async () => {
    try {
      const updateData = { ...formData };
      if (!updateData.password) delete updateData.password;
      
      const res = await fetch(`${API_URL}/api/users/${selectedUser.id}`, {
        method: "PUT",
        headers: {
          Authorization: `Bearer ${token}`,
          "Content-Type": "application/json"
        },
        body: JSON.stringify(updateData)
      });
      
      if (res.ok) {
        toast.success("Usuario actualizado exitosamente");
        setShowEditDialog(false);
        resetForm();
        fetchUsers();
      } else {
        const error = await res.json();
        toast.error(error.detail || "Error al actualizar usuario");
      }
    } catch (error) {
      toast.error("Error de conexión");
    }
  };

  const handleDeleteUser = async () => {
    try {
      const res = await fetch(`${API_URL}/api/users/${selectedUser.id}`, {
        method: "DELETE",
        headers: { Authorization: `Bearer ${token}` }
      });
      
      if (res.ok) {
        toast.success("Usuario eliminado exitosamente");
        setShowDeleteDialog(false);
        fetchUsers();
      } else {
        const error = await res.json();
        toast.error(error.detail || "Error al eliminar usuario");
      }
    } catch (error) {
      toast.error("Error de conexión");
    }
  };

  const handleToggleStatus = async (user) => {
    try {
      const res = await fetch(`${API_URL}/api/users/${user.id}`, {
        method: "PUT",
        headers: {
          Authorization: `Bearer ${token}`,
          "Content-Type": "application/json"
        },
        body: JSON.stringify({ is_active: !user.is_active })
      });
      
      if (res.ok) {
        toast.success(user.is_active ? "Usuario desactivado" : "Usuario activado");
        fetchUsers();
      }
    } catch (error) {
      toast.error("Error al cambiar estado");
    }
  };

  const resetForm = () => {
    setFormData({
      email: "",
      full_name: "",
      password: "",
      role: "participant",
      department: "",
      position: "",
      is_active: true
    });
    setSelectedUser(null);
  };

  const openEditDialog = (user) => {
    setSelectedUser(user);
    setFormData({
      email: user.email,
      full_name: user.full_name,
      password: "",
      role: user.role,
      department: user.department || "",
      position: user.position || "",
      is_active: user.is_active
    });
    setShowEditDialog(true);
  };

  const getRoleBadge = (role) => {
    const roleInfo = ROLES.find(r => r.value === role) || { label: role, color: "bg-gray-100 text-gray-800" };
    return <Badge className={`${roleInfo.color} font-medium`}>{roleInfo.label}</Badge>;
  };

  const exportUsers = () => {
    const csv = [
      ["Email", "Nombre", "Rol", "Departamento", "Cargo", "Estado"].join(","),
      ...filteredUsers.map(u => [
        u.email, u.full_name, u.role, u.department || "", u.position || "", u.is_active ? "Activo" : "Inactivo"
      ].join(","))
    ].join("\n");
    
    const blob = new Blob([csv], { type: "text/csv" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `usuarios_${new Date().toISOString().split("T")[0]}.csv`;
    a.click();
    toast.success("Usuarios exportados");
  };

  if (currentUser?.role !== "admin" && currentUser?.role !== "security_officer") {
    return (
      <div className="flex items-center justify-center h-96">
        <Card className="p-8 text-center">
          <Shield className="w-16 h-16 mx-auto text-muted-foreground mb-4" />
          <h2 className="text-xl font-bold">Acceso Restringido</h2>
          <p className="text-muted-foreground mt-2">Solo administradores pueden acceder a esta sección</p>
        </Card>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex justify-between items-start">
        <div>
          <h1 className="text-3xl font-bold font-['Outfit'] flex items-center gap-3">
            <Users className="w-8 h-8 text-primary" />
            Administración de Usuarios
          </h1>
          <p className="text-muted-foreground mt-1">
            Gestiona los usuarios y permisos de tu organización
          </p>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" onClick={exportUsers}>
            <Download className="w-4 h-4 mr-2" />
            Exportar
          </Button>
          <Button onClick={() => { resetForm(); setShowCreateDialog(true); }}>
            <UserPlus className="w-4 h-4 mr-2" />
            Nuevo Usuario
          </Button>
        </div>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-4">
        <Card>
          <CardContent className="p-4 text-center">
            <div className="text-3xl font-bold text-primary">{stats.total}</div>
            <div className="text-sm text-muted-foreground">Total Usuarios</div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-4 text-center">
            <div className="text-3xl font-bold text-green-600">{stats.active}</div>
            <div className="text-sm text-muted-foreground">Activos</div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-4 text-center">
            <div className="text-3xl font-bold text-red-600">{stats.inactive}</div>
            <div className="text-sm text-muted-foreground">Inactivos</div>
          </CardContent>
        </Card>
        {stats.byRole.slice(0, 3).map(role => (
          <Card key={role.value}>
            <CardContent className="p-4 text-center">
              <div className="text-3xl font-bold">{role.count}</div>
              <div className="text-sm text-muted-foreground">{role.label}s</div>
            </CardContent>
          </Card>
        ))}
      </div>

      {/* Filters */}
      <Card>
        <CardContent className="p-4">
          <div className="flex flex-wrap gap-4 items-end">
            <div className="flex-1 min-w-[200px]">
              <Label className="text-xs text-muted-foreground">Buscar</Label>
              <div className="relative">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
                <Input
                  placeholder="Buscar por nombre, email, cargo..."
                  value={searchTerm}
                  onChange={(e) => setSearchTerm(e.target.value)}
                  className="pl-10"
                />
              </div>
            </div>
            <div className="w-[160px]">
              <Label className="text-xs text-muted-foreground">Rol</Label>
              <Select value={filterRole} onValueChange={setFilterRole}>
                <SelectTrigger>
                  <SelectValue placeholder="Todos" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">Todos los roles</SelectItem>
                  {ROLES.map(role => (
                    <SelectItem key={role.value} value={role.value}>{role.label}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="w-[180px]">
              <Label className="text-xs text-muted-foreground">Departamento</Label>
              <Select value={filterDepartment} onValueChange={setFilterDepartment}>
                <SelectTrigger>
                  <SelectValue placeholder="Todos" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">Todos</SelectItem>
                  {stats.departments.map(dept => (
                    <SelectItem key={dept} value={dept}>{dept}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="w-[140px]">
              <Label className="text-xs text-muted-foreground">Estado</Label>
              <Select value={filterStatus} onValueChange={setFilterStatus}>
                <SelectTrigger>
                  <SelectValue placeholder="Todos" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">Todos</SelectItem>
                  <SelectItem value="active">Activos</SelectItem>
                  <SelectItem value="inactive">Inactivos</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <Button variant="ghost" size="icon" onClick={fetchUsers}>
              <RefreshCw className="w-4 h-4" />
            </Button>
          </div>
        </CardContent>
      </Card>

      {/* Users Table */}
      <Card>
        <CardContent className="p-0">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Usuario</TableHead>
                <TableHead>Rol</TableHead>
                <TableHead>Departamento</TableHead>
                <TableHead>Cargo</TableHead>
                <TableHead className="text-center">Estado</TableHead>
                <TableHead className="text-right">Acciones</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {loading ? (
                <TableRow>
                  <TableCell colSpan={6} className="text-center py-8">
                    <RefreshCw className="w-6 h-6 animate-spin mx-auto text-muted-foreground" />
                  </TableCell>
                </TableRow>
              ) : paginatedUsers.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={6} className="text-center py-8 text-muted-foreground">
                    No se encontraron usuarios
                  </TableCell>
                </TableRow>
              ) : (
                paginatedUsers.map(user => (
                  <TableRow key={user.id} className={!user.is_active ? "opacity-60" : ""}>
                    <TableCell>
                      <div className="flex items-center gap-3">
                        <div className="w-10 h-10 rounded-full bg-primary/10 flex items-center justify-center">
                          <span className="text-primary font-semibold">
                            {user.full_name?.charAt(0).toUpperCase()}
                          </span>
                        </div>
                        <div>
                          <div className="font-medium">{user.full_name}</div>
                          <div className="text-sm text-muted-foreground">{user.email}</div>
                        </div>
                      </div>
                    </TableCell>
                    <TableCell>{getRoleBadge(user.role)}</TableCell>
                    <TableCell>
                      <div className="flex items-center gap-2">
                        <Building2 className="w-4 h-4 text-muted-foreground" />
                        {user.department || "-"}
                      </div>
                    </TableCell>
                    <TableCell>{user.position || "-"}</TableCell>
                    <TableCell className="text-center">
                      <Badge variant={user.is_active ? "default" : "secondary"}>
                        {user.is_active ? "Activo" : "Inactivo"}
                      </Badge>
                    </TableCell>
                    <TableCell className="text-right">
                      <div className="flex justify-end gap-1">
                        <Button
                          variant="ghost"
                          size="icon"
                          onClick={() => openEditDialog(user)}
                          disabled={user.id === currentUser?.id}
                        >
                          <Edit className="w-4 h-4" />
                        </Button>
                        <Button
                          variant="ghost"
                          size="icon"
                          onClick={() => handleToggleStatus(user)}
                          disabled={user.id === currentUser?.id}
                        >
                          {user.is_active ? <UserX className="w-4 h-4" /> : <UserCheck className="w-4 h-4" />}
                        </Button>
                        <Button
                          variant="ghost"
                          size="icon"
                          onClick={() => { setSelectedUser(user); setShowDeleteDialog(true); }}
                          disabled={user.id === currentUser?.id}
                          className="text-destructive hover:text-destructive"
                        >
                          <Trash2 className="w-4 h-4" />
                        </Button>
                      </div>
                    </TableCell>
                  </TableRow>
                ))
              )}
            </TableBody>
          </Table>
          
          {/* Pagination */}
          {totalPages > 1 && (
            <div className="flex items-center justify-between px-4 py-3 border-t">
              <div className="text-sm text-muted-foreground">
                Mostrando {((currentPage - 1) * itemsPerPage) + 1} - {Math.min(currentPage * itemsPerPage, filteredUsers.length)} de {filteredUsers.length}
              </div>
              <div className="flex items-center gap-2">
                <Button
                  variant="outline"
                  size="icon"
                  onClick={() => setCurrentPage(p => Math.max(1, p - 1))}
                  disabled={currentPage === 1}
                >
                  <ChevronLeft className="w-4 h-4" />
                </Button>
                <span className="text-sm">
                  Página {currentPage} de {totalPages}
                </span>
                <Button
                  variant="outline"
                  size="icon"
                  onClick={() => setCurrentPage(p => Math.min(totalPages, p + 1))}
                  disabled={currentPage === totalPages}
                >
                  <ChevronRight className="w-4 h-4" />
                </Button>
              </div>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Create User Dialog */}
      <Dialog open={showCreateDialog} onOpenChange={setShowCreateDialog}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <UserPlus className="w-5 h-5" />
              Crear Nuevo Usuario
            </DialogTitle>
            <DialogDescription>
              Ingresa los datos del nuevo usuario
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4">
            <div>
              <Label>Nombre Completo *</Label>
              <Input
                value={formData.full_name}
                onChange={(e) => setFormData({ ...formData, full_name: e.target.value })}
                placeholder="Juan Pérez"
              />
            </div>
            <div>
              <Label>Email *</Label>
              <Input
                type="email"
                value={formData.email}
                onChange={(e) => setFormData({ ...formData, email: e.target.value })}
                placeholder="juan.perez@empresa.com"
              />
            </div>
            <div>
              <Label>Contraseña *</Label>
              <Input
                type="password"
                value={formData.password}
                onChange={(e) => setFormData({ ...formData, password: e.target.value })}
                placeholder="Mínimo 8 caracteres"
              />
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <Label>Rol *</Label>
                <Select value={formData.role} onValueChange={(v) => setFormData({ ...formData, role: v })}>
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {ROLES.map(role => (
                      <SelectItem key={role.value} value={role.value}>{role.label}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              <div>
                <Label>Departamento</Label>
                <Select value={formData.department} onValueChange={(v) => setFormData({ ...formData, department: v })}>
                  <SelectTrigger>
                    <SelectValue placeholder="Seleccionar" />
                  </SelectTrigger>
                  <SelectContent>
                    {DEPARTMENTS.map(dept => (
                      <SelectItem key={dept} value={dept}>{dept}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            </div>
            <div>
              <Label>Cargo</Label>
              <Input
                value={formData.position}
                onChange={(e) => setFormData({ ...formData, position: e.target.value })}
                placeholder="Analista de Datos"
              />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowCreateDialog(false)}>Cancelar</Button>
            <Button onClick={handleCreateUser} disabled={!formData.email || !formData.full_name || !formData.password}>
              Crear Usuario
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Edit User Dialog */}
      <Dialog open={showEditDialog} onOpenChange={setShowEditDialog}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <Edit className="w-5 h-5" />
              Editar Usuario
            </DialogTitle>
            <DialogDescription>
              Modifica los datos del usuario
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4">
            <div>
              <Label>Nombre Completo *</Label>
              <Input
                value={formData.full_name}
                onChange={(e) => setFormData({ ...formData, full_name: e.target.value })}
              />
            </div>
            <div>
              <Label>Email *</Label>
              <Input
                type="email"
                value={formData.email}
                onChange={(e) => setFormData({ ...formData, email: e.target.value })}
              />
            </div>
            <div>
              <Label>Nueva Contraseña (dejar vacío para mantener actual)</Label>
              <Input
                type="password"
                value={formData.password}
                onChange={(e) => setFormData({ ...formData, password: e.target.value })}
                placeholder="••••••••"
              />
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <Label>Rol *</Label>
                <Select value={formData.role} onValueChange={(v) => setFormData({ ...formData, role: v })}>
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {ROLES.map(role => (
                      <SelectItem key={role.value} value={role.value}>{role.label}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              <div>
                <Label>Departamento</Label>
                <Select value={formData.department} onValueChange={(v) => setFormData({ ...formData, department: v })}>
                  <SelectTrigger>
                    <SelectValue placeholder="Seleccionar" />
                  </SelectTrigger>
                  <SelectContent>
                    {DEPARTMENTS.map(dept => (
                      <SelectItem key={dept} value={dept}>{dept}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            </div>
            <div>
              <Label>Cargo</Label>
              <Input
                value={formData.position}
                onChange={(e) => setFormData({ ...formData, position: e.target.value })}
              />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowEditDialog(false)}>Cancelar</Button>
            <Button onClick={handleUpdateUser}>Guardar Cambios</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Delete Confirmation Dialog */}
      <Dialog open={showDeleteDialog} onOpenChange={setShowDeleteDialog}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle className="text-destructive flex items-center gap-2">
              <Trash2 className="w-5 h-5" />
              Eliminar Usuario
            </DialogTitle>
            <DialogDescription>
              ¿Estás seguro de que deseas eliminar a <strong>{selectedUser?.full_name}</strong>? 
              Esta acción no se puede deshacer.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowDeleteDialog(false)}>Cancelar</Button>
            <Button variant="destructive" onClick={handleDeleteUser}>Eliminar</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
