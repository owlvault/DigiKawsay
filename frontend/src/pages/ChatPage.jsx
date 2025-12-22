import React, { useState, useEffect, useRef } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useAuthStore, useCampaignStore, useSessionStore, useChatStore, useConsentStore } from '../stores';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Card, CardContent } from '../components/ui/card';
import { ScrollArea } from '../components/ui/scroll-area';
import { Avatar, AvatarFallback } from '../components/ui/avatar';
import { toast } from 'sonner';
import { 
  Send, 
  ArrowLeft, 
  MessageCircle,
  User,
  Sparkles,
  CheckCircle2,
  Loader2,
  Info
} from 'lucide-react';

export const ChatPage = () => {
  const { campaignId } = useParams();
  const navigate = useNavigate();
  const messagesEndRef = useRef(null);
  
  const { user } = useAuthStore();
  const { currentCampaign, getCampaign } = useCampaignStore();
  const { currentSession, createSession, completeSession, setCurrentSession } = useSessionStore();
  const { messages, sendMessage, fetchHistory, clearMessages, isLoading: chatLoading } = useChatStore();
  const { consents, fetchConsents } = useConsentStore();
  
  const [inputMessage, setInputMessage] = useState('');
  const [isInitializing, setIsInitializing] = useState(true);

  useEffect(() => {
    const initChat = async () => {
      setIsInitializing(true);
      clearMessages();
      
      // Fetch campaign
      const campaign = await getCampaign(campaignId);
      if (!campaign) {
        toast.error('Campaña no encontrada');
        navigate('/campaigns');
        return;
      }

      // Check consent
      await fetchConsents();
      const hasConsent = consents.some(
        c => c.campaign_id === campaignId && c.accepted && !c.revoked_at
      );
      
      if (!hasConsent) {
        toast.error('Necesitas dar tu consentimiento para participar');
        navigate('/campaigns');
        return;
      }

      // Create or get session
      const sessionResult = await createSession(campaignId);
      if (!sessionResult.success) {
        if (sessionResult.error?.includes('consentimiento')) {
          toast.error('Necesitas dar tu consentimiento para participar');
          navigate('/campaigns');
        } else {
          toast.error(sessionResult.error || 'Error al iniciar sesión');
        }
        return;
      }

      // Fetch chat history if exists
      if (sessionResult.data?.id) {
        await fetchHistory(sessionResult.data.id);
      }
      
      setIsInitializing(false);
    };

    initChat();
  }, [campaignId]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const handleSendMessage = async (e) => {
    e.preventDefault();
    if (!inputMessage.trim() || !currentSession?.id) return;

    const message = inputMessage;
    setInputMessage('');

    const result = await sendMessage(currentSession.id, message);
    if (!result.success) {
      toast.error(result.error || 'Error al enviar mensaje');
    }
  };

  const handleEndSession = async () => {
    if (!currentSession?.id) return;
    
    const result = await completeSession(currentSession.id);
    if (result.success) {
      toast.success('¡Sesión completada! Gracias por participar.');
      navigate('/dashboard');
    } else {
      toast.error(result.error || 'Error al finalizar sesión');
    }
  };

  if (isInitializing) {
    return (
      <div className="flex items-center justify-center h-[calc(100vh-200px)]">
        <div className="text-center space-y-4">
          <Loader2 className="w-12 h-12 animate-spin mx-auto text-orange-500" />
          <p className="text-muted-foreground">Preparando tu sesión con VAL...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="h-[calc(100vh-140px)] flex flex-col" data-testid="chat-page">
      {/* Header */}
      <div className="flex items-center justify-between pb-4 border-b mb-4">
        <div className="flex items-center gap-3">
          <Button 
            variant="ghost" 
            size="icon"
            onClick={() => navigate('/campaigns')}
            data-testid="back-btn"
          >
            <ArrowLeft className="w-5 h-5" />
          </Button>
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-full bg-gradient-to-br from-orange-400 to-orange-600 flex items-center justify-center">
              <Sparkles className="w-5 h-5 text-white" />
            </div>
            <div>
              <h2 className="font-semibold font-['Outfit']">VAL - Facilitadora</h2>
              <p className="text-xs text-muted-foreground">
                {currentCampaign?.name || 'Sesión de diálogo'}
              </p>
            </div>
          </div>
        </div>
        <Button 
          variant="outline" 
          onClick={handleEndSession}
          data-testid="end-session-btn"
        >
          <CheckCircle2 className="w-4 h-4 mr-2" />
          Finalizar Sesión
        </Button>
      </div>

      {/* Campaign Objective Banner */}
      {currentCampaign?.objective && (
        <Card className="mb-4 bg-slate-50 border-slate-200">
          <CardContent className="p-3 flex items-start gap-2">
            <Info className="w-4 h-4 text-slate-500 mt-0.5 flex-shrink-0" />
            <p className="text-sm text-slate-600">
              <strong>Objetivo:</strong> {currentCampaign.objective}
            </p>
          </CardContent>
        </Card>
      )}

      {/* Messages Area */}
      <ScrollArea className="flex-1 pr-4">
        <div className="space-y-4">
          {/* Welcome message */}
          {messages.length === 0 && (
            <div className="flex gap-3 animate-fade-in">
              <Avatar className="w-10 h-10 border-2 border-orange-200">
                <AvatarFallback className="bg-gradient-to-br from-orange-400 to-orange-600 text-white">
                  <Sparkles className="w-5 h-5" />
                </AvatarFallback>
              </Avatar>
              <div className="flex-1 max-w-[80%]">
                <div className="chat-bubble-assistant p-4">
                  <p className="text-sm leading-relaxed">
                    ¡Hola! Soy <strong>VAL</strong>, tu facilitadora conversacional. 
                    Estoy aquí para acompañarte en una reflexión sobre tu experiencia 
                    en la organización.
                  </p>
                  <p className="text-sm leading-relaxed mt-2">
                    Todo lo que compartas será tratado con confidencialidad y solo 
                    se utilizará de forma agregada y anonimizada.
                  </p>
                  <p className="text-sm leading-relaxed mt-2">
                    ¿Qué te gustaría explorar hoy?
                  </p>
                </div>
              </div>
            </div>
          )}

          {/* Chat messages */}
          {messages.map((msg, index) => (
            <div 
              key={index} 
              className={`flex gap-3 animate-fade-in ${msg.role === 'user' ? 'flex-row-reverse' : ''}`}
              style={{ animationDelay: `${index * 0.05}s` }}
            >
              <Avatar className={`w-10 h-10 ${msg.role === 'user' ? 'border-2 border-slate-200' : 'border-2 border-orange-200'}`}>
                <AvatarFallback className={msg.role === 'user' 
                  ? 'bg-slate-100 text-slate-700' 
                  : 'bg-gradient-to-br from-orange-400 to-orange-600 text-white'
                }>
                  {msg.role === 'user' 
                    ? <User className="w-5 h-5" />
                    : <Sparkles className="w-5 h-5" />
                  }
                </AvatarFallback>
              </Avatar>
              <div className={`flex-1 max-w-[80%] ${msg.role === 'user' ? 'flex justify-end' : ''}`}>
                <div className={msg.role === 'user' ? 'chat-bubble-user p-4' : 'chat-bubble-assistant p-4'}>
                  <p className="text-sm leading-relaxed whitespace-pre-wrap">{msg.content}</p>
                </div>
              </div>
            </div>
          ))}

          {/* Loading indicator */}
          {chatLoading && (
            <div className="flex gap-3 animate-fade-in">
              <Avatar className="w-10 h-10 border-2 border-orange-200">
                <AvatarFallback className="bg-gradient-to-br from-orange-400 to-orange-600 text-white">
                  <Sparkles className="w-5 h-5" />
                </AvatarFallback>
              </Avatar>
              <div className="chat-bubble-assistant p-4">
                <div className="flex items-center gap-2">
                  <Loader2 className="w-4 h-4 animate-spin" />
                  <span className="text-sm text-muted-foreground">VAL está escribiendo...</span>
                </div>
              </div>
            </div>
          )}

          <div ref={messagesEndRef} />
        </div>
      </ScrollArea>

      {/* Input Area */}
      <form onSubmit={handleSendMessage} className="mt-4 pt-4 border-t">
        <div className="flex gap-3">
          <Input
            value={inputMessage}
            onChange={(e) => setInputMessage(e.target.value)}
            placeholder="Escribe tu mensaje..."
            className="flex-1"
            disabled={chatLoading}
            data-testid="chat-input"
          />
          <Button 
            type="submit" 
            className="bg-primary hover:bg-primary/90"
            disabled={!inputMessage.trim() || chatLoading}
            data-testid="send-message-btn"
          >
            <Send className="w-4 h-4" />
          </Button>
        </div>
        <p className="text-xs text-muted-foreground mt-2 text-center">
          Tus respuestas son confidenciales y se procesan de forma anonimizada
        </p>
      </form>
    </div>
  );
};
