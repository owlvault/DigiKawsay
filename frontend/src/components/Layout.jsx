import React from 'react';
import { NavLink, useNavigate } from 'react-router-dom';
import { useAuthStore } from '../stores';
import { Button } from '../components/ui/button';
import { ScrollArea } from '../components/ui/scroll-area';
import { Avatar, AvatarFallback } from '../components/ui/avatar';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '../components/ui/dropdown-menu';
import { 
  LayoutDashboard, 
  MessageCircle, 
  BarChart3, 
  Network, 
  Route,
  Settings,
  Shield,
  LogOut,
  ChevronDown,
  Sparkles,
  User,
  Bell,
  FileText
} from 'lucide-react';
import { cn } from '../lib/utils';

const NavItem = ({ to, icon: Icon, label, disabled = false }) => (
  <NavLink
    to={to}
    className={({ isActive }) => cn(
      "flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-all",
      isActive 
        ? "bg-primary text-primary-foreground shadow-sm" 
        : "text-muted-foreground hover:bg-muted hover:text-foreground",
      disabled && "opacity-50 pointer-events-none"
    )}
  >
    <Icon className="w-5 h-5" />
    <span>{label}</span>
  </NavLink>
);

export const Layout = ({ children }) => {
  const navigate = useNavigate();
  const { user, logout } = useAuthStore();

  const isAdmin = user?.role === 'admin' || user?.role === 'facilitator' || user?.role === 'analyst';

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  const navItems = [
    { to: '/dashboard', icon: LayoutDashboard, label: 'Dashboard', roles: ['all'] },
    { to: '/campaigns', icon: MessageCircle, label: 'Campañas', roles: ['all'] },
    { to: '/scripts', icon: FileText, label: 'Guiones', roles: ['admin', 'facilitator'] },
    { to: '/insights', icon: BarChart3, label: 'Hallazgos', roles: ['admin', 'facilitator', 'analyst'], disabled: true },
    { to: '/network', icon: Network, label: 'Red Social', roles: ['admin', 'facilitator', 'analyst'], disabled: true },
    { to: '/roadmap', icon: Route, label: 'Roadmap', roles: ['admin', 'facilitator', 'sponsor'], disabled: true },
    { to: '/governance', icon: Shield, label: 'Gobernanza', roles: ['admin'], disabled: true },
  ];

  const filteredNavItems = navItems.filter(item => 
    item.roles.includes('all') || item.roles.includes(user?.role)
  );

  const getRoleBadge = (role) => {
    const badges = {
      admin: 'Administrador',
      facilitator: 'Facilitador',
      analyst: 'Analista',
      participant: 'Participante',
      sponsor: 'Sponsor'
    };
    return badges[role] || role;
  };

  return (
    <div className="min-h-screen flex bg-slate-50">
      {/* Sidebar */}
      <aside className="hidden md:flex w-64 flex-col bg-white border-r shadow-sm">
        {/* Logo */}
        <div className="p-6 border-b">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-orange-500 to-orange-600 flex items-center justify-center shadow-lg shadow-orange-200">
              <Sparkles className="w-5 h-5 text-white" />
            </div>
            <div>
              <h1 className="font-bold text-lg font-['Outfit'] tracking-tight">DigiKawsay</h1>
              <p className="text-xs text-muted-foreground">Facilitación Conversacional</p>
            </div>
          </div>
        </div>

        {/* Navigation */}
        <ScrollArea className="flex-1 px-3 py-4">
          <nav className="space-y-1">
            {filteredNavItems.map((item) => (
              <NavItem 
                key={item.to} 
                {...item} 
              />
            ))}
          </nav>
        </ScrollArea>

        {/* User Section */}
        <div className="p-4 border-t">
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button variant="ghost" className="w-full justify-start gap-3 h-auto py-3">
                <Avatar className="w-9 h-9">
                  <AvatarFallback className="bg-slate-100 text-slate-700 text-sm">
                    {user?.full_name?.charAt(0)?.toUpperCase() || 'U'}
                  </AvatarFallback>
                </Avatar>
                <div className="flex-1 text-left">
                  <p className="text-sm font-medium truncate">{user?.full_name || 'Usuario'}</p>
                  <p className="text-xs text-muted-foreground">{getRoleBadge(user?.role)}</p>
                </div>
                <ChevronDown className="w-4 h-4 text-muted-foreground" />
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end" className="w-56">
              <DropdownMenuLabel>Mi Cuenta</DropdownMenuLabel>
              <DropdownMenuSeparator />
              <DropdownMenuItem>
                <User className="w-4 h-4 mr-2" />
                Perfil
              </DropdownMenuItem>
              <DropdownMenuItem>
                <Settings className="w-4 h-4 mr-2" />
                Configuración
              </DropdownMenuItem>
              <DropdownMenuSeparator />
              <DropdownMenuItem onClick={handleLogout} className="text-red-600">
                <LogOut className="w-4 h-4 mr-2" />
                Cerrar Sesión
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
        </div>
      </aside>

      {/* Main Content */}
      <div className="flex-1 flex flex-col">
        {/* Top Bar */}
        <header className="h-16 bg-white border-b px-6 flex items-center justify-between shadow-sm">
          <div className="md:hidden flex items-center gap-3">
            <div className="w-8 h-8 rounded-lg bg-orange-500 flex items-center justify-center">
              <Sparkles className="w-4 h-4 text-white" />
            </div>
            <span className="font-bold font-['Outfit']">DigiKawsay</span>
          </div>
          
          <div className="flex-1" />
          
          <div className="flex items-center gap-3">
            <Button variant="ghost" size="icon" className="relative">
              <Bell className="w-5 h-5" />
              <span className="absolute top-1 right-1 w-2 h-2 bg-orange-500 rounded-full" />
            </Button>
            
            <div className="md:hidden">
              <DropdownMenu>
                <DropdownMenuTrigger asChild>
                  <Button variant="ghost" size="icon">
                    <Avatar className="w-8 h-8">
                      <AvatarFallback className="bg-slate-100 text-slate-700 text-sm">
                        {user?.full_name?.charAt(0)?.toUpperCase() || 'U'}
                      </AvatarFallback>
                    </Avatar>
                  </Button>
                </DropdownMenuTrigger>
                <DropdownMenuContent align="end">
                  <DropdownMenuLabel>{user?.full_name}</DropdownMenuLabel>
                  <DropdownMenuSeparator />
                  {filteredNavItems.map((item) => (
                    <DropdownMenuItem key={item.to} onClick={() => navigate(item.to)} disabled={item.disabled}>
                      <item.icon className="w-4 h-4 mr-2" />
                      {item.label}
                    </DropdownMenuItem>
                  ))}
                  <DropdownMenuSeparator />
                  <DropdownMenuItem onClick={handleLogout} className="text-red-600">
                    <LogOut className="w-4 h-4 mr-2" />
                    Cerrar Sesión
                  </DropdownMenuItem>
                </DropdownMenuContent>
              </DropdownMenu>
            </div>
          </div>
        </header>

        {/* Page Content */}
        <main className="flex-1 p-6 overflow-auto">
          <div className="max-w-7xl mx-auto">
            {children}
          </div>
        </main>
      </div>
    </div>
  );
};
