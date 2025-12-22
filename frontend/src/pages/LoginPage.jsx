import React, { useState, useEffect } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { useAuthStore } from '../stores';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../components/ui/card';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../components/ui/tabs';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../components/ui/select';
import { toast } from 'sonner';
import { MessageCircle, Users, BarChart3, Shield, ArrowRight, Sparkles } from 'lucide-react';

export const LoginPage = () => {
  const navigate = useNavigate();
  const location = useLocation();
  const { login, register, isLoading, isAuthenticated, error, initAuth } = useAuthStore();
  
  const [loginData, setLoginData] = useState({ email: '', password: '' });
  const [registerData, setRegisterData] = useState({ 
    email: '', 
    password: '', 
    fullName: '', 
    role: 'participant' 
  });

  useEffect(() => {
    initAuth();
    if (isAuthenticated) {
      const from = location.state?.from?.pathname || '/dashboard';
      navigate(from, { replace: true });
    }
  }, [isAuthenticated, navigate, location, initAuth]);

  const handleLogin = async (e) => {
    e.preventDefault();
    const result = await login(loginData.email, loginData.password);
    if (result.success) {
      toast.success('¡Bienvenido de vuelta!');
      navigate('/dashboard');
    } else {
      toast.error(result.error);
    }
  };

  const handleRegister = async (e) => {
    e.preventDefault();
    const result = await register(
      registerData.email, 
      registerData.password, 
      registerData.fullName,
      registerData.role
    );
    if (result.success) {
      toast.success('¡Cuenta creada exitosamente!');
      navigate('/dashboard');
    } else {
      toast.error(result.error);
    }
  };

  const features = [
    { icon: MessageCircle, title: 'Diálogos Facilitados', desc: 'Conversaciones guiadas por IA' },
    { icon: Users, title: 'Análisis de Redes', desc: 'Visualiza relaciones organizacionales' },
    { icon: BarChart3, title: 'Insights Culturales', desc: 'Extrae patrones y tendencias' },
    { icon: Shield, title: 'Privacidad por Diseño', desc: 'Datos anonimizados y seguros' },
  ];

  return (
    <div className="min-h-screen flex">
      {/* Left Panel - Branding */}
      <div className="hidden lg:flex lg:w-1/2 gradient-hero text-white p-12 flex-col justify-between">
        <div>
          <div className="flex items-center gap-3 mb-2">
            <div className="w-12 h-12 rounded-xl bg-orange-500 flex items-center justify-center">
              <Sparkles className="w-7 h-7" />
            </div>
            <h1 className="text-3xl font-bold tracking-tight font-['Outfit']">DigiKawsay</h1>
          </div>
          <p className="text-slate-400 text-lg">Transformando conversaciones en evidencia</p>
        </div>
        
        <div className="space-y-6">
          <h2 className="text-2xl font-semibold font-['Outfit']">
            Plataforma de Facilitación Conversacional
          </h2>
          <p className="text-slate-300 leading-relaxed">
            DigiKawsay transforma los diálogos organizacionales en insights accionables 
            mediante coaching ontológico e Investigación Acción Participativa.
          </p>
          
          <div className="grid grid-cols-2 gap-4 mt-8">
            {features.map((feature, i) => (
              <div key={i} className="p-4 rounded-lg bg-white/5 border border-white/10 backdrop-blur-sm">
                <feature.icon className="w-6 h-6 text-orange-400 mb-2" />
                <h3 className="font-medium text-sm">{feature.title}</h3>
                <p className="text-xs text-slate-400 mt-1">{feature.desc}</p>
              </div>
            ))}
          </div>
        </div>
        
        <p className="text-sm text-slate-500">
          © 2024 DigiKawsay. Todos los derechos reservados.
        </p>
      </div>

      {/* Right Panel - Auth Forms */}
      <div className="w-full lg:w-1/2 flex items-center justify-center p-8 bg-slate-50">
        <div className="w-full max-w-md">
          <div className="lg:hidden mb-8 text-center">
            <div className="flex items-center justify-center gap-3 mb-2">
              <div className="w-10 h-10 rounded-xl bg-orange-500 flex items-center justify-center">
                <Sparkles className="w-6 h-6 text-white" />
              </div>
              <h1 className="text-2xl font-bold font-['Outfit']">DigiKawsay</h1>
            </div>
          </div>

          <Card className="border-0 shadow-xl">
            <CardHeader className="text-center pb-2">
              <CardTitle className="text-2xl font-['Outfit']">Acceder</CardTitle>
              <CardDescription>Ingresa a la plataforma de facilitación</CardDescription>
            </CardHeader>
            <CardContent>
              <Tabs defaultValue="login" className="w-full">
                <TabsList className="grid w-full grid-cols-2 mb-6">
                  <TabsTrigger value="login" data-testid="login-tab">Iniciar Sesión</TabsTrigger>
                  <TabsTrigger value="register" data-testid="register-tab">Registrarse</TabsTrigger>
                </TabsList>

                <TabsContent value="login">
                  <form onSubmit={handleLogin} className="space-y-4">
                    <div className="space-y-2">
                      <Label htmlFor="login-email">Correo electrónico</Label>
                      <Input
                        id="login-email"
                        data-testid="login-email"
                        type="email"
                        placeholder="tu@email.com"
                        value={loginData.email}
                        onChange={(e) => setLoginData({ ...loginData, email: e.target.value })}
                        required
                      />
                    </div>
                    <div className="space-y-2">
                      <Label htmlFor="login-password">Contraseña</Label>
                      <Input
                        id="login-password"
                        data-testid="login-password"
                        type="password"
                        placeholder="••••••••"
                        value={loginData.password}
                        onChange={(e) => setLoginData({ ...loginData, password: e.target.value })}
                        required
                      />
                    </div>
                    <Button 
                      type="submit" 
                      className="w-full bg-primary hover:bg-primary/90"
                      data-testid="login-submit"
                      disabled={isLoading}
                    >
                      {isLoading ? 'Ingresando...' : 'Ingresar'}
                      <ArrowRight className="w-4 h-4 ml-2" />
                    </Button>
                  </form>
                </TabsContent>

                <TabsContent value="register">
                  <form onSubmit={handleRegister} className="space-y-4">
                    <div className="space-y-2">
                      <Label htmlFor="register-name">Nombre completo</Label>
                      <Input
                        id="register-name"
                        data-testid="register-name"
                        type="text"
                        placeholder="Tu nombre"
                        value={registerData.fullName}
                        onChange={(e) => setRegisterData({ ...registerData, fullName: e.target.value })}
                        required
                      />
                    </div>
                    <div className="space-y-2">
                      <Label htmlFor="register-email">Correo electrónico</Label>
                      <Input
                        id="register-email"
                        data-testid="register-email"
                        type="email"
                        placeholder="tu@email.com"
                        value={registerData.email}
                        onChange={(e) => setRegisterData({ ...registerData, email: e.target.value })}
                        required
                      />
                    </div>
                    <div className="space-y-2">
                      <Label htmlFor="register-password">Contraseña</Label>
                      <Input
                        id="register-password"
                        data-testid="register-password"
                        type="password"
                        placeholder="••••••••"
                        value={registerData.password}
                        onChange={(e) => setRegisterData({ ...registerData, password: e.target.value })}
                        required
                      />
                    </div>
                    <div className="space-y-2">
                      <Label htmlFor="register-role">Rol</Label>
                      <Select 
                        value={registerData.role} 
                        onValueChange={(value) => setRegisterData({ ...registerData, role: value })}
                      >
                        <SelectTrigger data-testid="register-role">
                          <SelectValue placeholder="Selecciona tu rol" />
                        </SelectTrigger>
                        <SelectContent>
                          <SelectItem value="participant">Participante</SelectItem>
                          <SelectItem value="facilitator">Facilitador</SelectItem>
                          <SelectItem value="analyst">Analista</SelectItem>
                          <SelectItem value="admin">Administrador</SelectItem>
                        </SelectContent>
                      </Select>
                    </div>
                    <Button 
                      type="submit" 
                      className="w-full bg-secondary hover:bg-secondary/90 text-white"
                      data-testid="register-submit"
                      disabled={isLoading}
                    >
                      {isLoading ? 'Creando cuenta...' : 'Crear cuenta'}
                      <ArrowRight className="w-4 h-4 ml-2" />
                    </Button>
                  </form>
                </TabsContent>
              </Tabs>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
};
