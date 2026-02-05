import React, { useState, useEffect, useRef } from 'react';
import { 
  Activity, 
  MessageSquare, 
  Settings, 
  AlertCircle, 
  CheckCircle2, 
  Send,
  Zap,
  Thermometer,
  Gauge,
  Wind,
  LayoutDashboard,
  Globe
} from 'lucide-react';
import axios from 'axios';
import { 
  LineChart, 
  Line, 
  XAxis, 
  YAxis, 
  CartesianGrid, 
  Tooltip, 
  ResponsiveContainer 
} from 'recharts';

// --- Tipos ---
interface SensorData {
  timestamp: string;
  values: Record<string, number>;
}

interface Message {
  role: 'user' | 'assistant';
  content: string;
  tool_request?: {
    tool: string;
    args: { tag: string; value: number };
    thought: string;
  };
}

// --- Componentes Auxiliares ---

const SensorCard = ({ label, value, unit, icon: Icon, color }: any) => (
  <div className="bg-white p-4 rounded-xl shadow-sm border border-slate-200 flex items-center space-x-4">
    <div className={`p-3 rounded-lg ${color}`}>
      <Icon size={24} className="text-white" />
    </div>
    <div>
      <p className="text-sm text-slate-500 font-medium uppercase">{label}</p>
      <div className="flex items-baseline space-x-1">
        <span className="text-2xl font-bold text-slate-800">{value.toFixed(2)}</span>
        <span className="text-sm text-slate-400 font-medium">{unit}</span>
      </div>
    </div>
  </div>
);

function App() {
  // Estados
  const [data, setData] = useState<SensorData | null>(null);
  const [history, setHistory] = useState<any[]>([]);
  const [messages, setMessages] = useState<Message[]>([
    { role: 'assistant', content: 'Olá! Sou seu assistente SCADA. Como posso ajudar hoje?' }
  ]);
  const [input, setInput] = useState('');
  const [isConnected, setIsConnected] = useState(false);
  const [isTyping, setIsTyping] = useState(false);
  
  // Novos estados para navegação
  const [view, setView] = useState<'dashboard' | 'scada'>('dashboard');
  
  // URL do SCADA: Prioriza VITE_SCADA_DASHBOARD_URL se existir
  const [scadaUrl, setScadaUrl] = useState<string>(import.meta.env.VITE_SCADA_DASHBOARD_URL || '');

  const chatEndRef = useRef<HTMLDivElement>(null);

  // Auto-scroll do chat
  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  // Busca URL do SCADA na inicialização
  useEffect(() => {
    const fetchStatus = async () => {
      try {
        const res = await axios.get('http://localhost:8000/api/status');
        
        // Lógica de Prioridade:
        // 1. Backend Dashboard URL (Proxy Seguro ou Configurado no Backend)
        // 2. VITE_SCADA_DASHBOARD_URL (Configuração Local do Frontend)
        // 3. Backend Base URL (Fallback)
        
        const backendDash = res.data.scada_dashboard_url;
        const localEnvDash = import.meta.env.VITE_SCADA_DASHBOARD_URL;
        const backendBase = res.data.scada_url;

        let finalUrl = backendDash;

        if (!finalUrl && localEnvDash) {
          finalUrl = localEnvDash;
        }

        if (!finalUrl) {
          finalUrl = backendBase;
        }
        
        if (finalUrl) {
          setScadaUrl(finalUrl);
          console.log("🔗 URL SCADA Definida:", finalUrl);
        }
      } catch (err) {
        console.error("Erro ao buscar status:", err);
        // Fallback final se a API falhar
        if (import.meta.env.VITE_SCADA_DASHBOARD_URL) {
           setScadaUrl(import.meta.env.VITE_SCADA_DASHBOARD_URL);
        }
      }
    };
    fetchStatus();
  }, []);

  // Conexão WebSocket
  useEffect(() => {
    let socket: WebSocket | null = null;
    let reconnectTimeout: number;

    const connect = () => {
      console.log("Tentando conectar ao WebSocket...");
      socket = new WebSocket('ws://localhost:8000/ws/data');
      
      socket.onopen = () => {
        console.log("✅ WebSocket Conectado!");
        setIsConnected(true);
      };

      socket.onclose = () => {
        console.log("❌ WebSocket Desconectado. Tentando reconectar em 3s...");
        setIsConnected(false);
        reconnectTimeout = window.setTimeout(connect, 3000);
      };

      socket.onerror = (err) => {
        console.error("⚠️ Erro no WebSocket:", err);
      };
      
      socket.onmessage = (event) => {
        const payload = JSON.parse(event.data);
        setData(payload);
        
        setHistory(prev => {
          const newPoint = { 
            time: new Date(payload.timestamp).toLocaleTimeString(),
            ...payload.values 
          };
          const updated = [...prev, newPoint];
          return updated.length > 20 ? updated.slice(1) : updated;
        });
      };
    };

    connect();

    return () => {
      if (socket) socket.close();
      clearTimeout(reconnectTimeout);
    };
  }, []);

  // Enviar Mensagem
  const handleSendMessage = async () => {
    if (!input.trim()) return;
    
    const userMsg: Message = { role: 'user', content: input };
    setMessages(prev => [...prev, userMsg]);
    setInput('');
    setIsTyping(true);

    try {
      const response = await axios.post('http://localhost:8000/api/chat', { message: input });
      const assistantMsg: Message = { 
        role: 'assistant', 
        content: response.data.response,
        tool_request: response.data.tool_request
      };
      setMessages(prev => [...prev, assistantMsg]);
    } catch (error) {
      console.error("Erro ao falar com agente:", error);
    } finally {
      setIsTyping(false);
    }
  };

  // Aprovar Ação
  const handleApproveAction = async (tag: string, value: number) => {
    try {
      await axios.post('http://localhost:8000/api/action/approve', { tag, value });
      setMessages(prev => [...prev, { 
        role: 'assistant', 
        content: `✅ Comando executado: ${tag} definido para ${value}.` 
      }]);
    } catch (error) {
      alert("Falha ao executar ação.");
    }
  };

  return (
    <div className="flex h-screen bg-slate-50 font-sans overflow-hidden">
      
      {/* --- SIDEBAR OPERACIONAL --- */}
      <div className="w-2/3 flex flex-col p-6 space-y-6 overflow-y-auto">
        <header className="flex justify-between items-center">
          <div>
            <h1 className="text-2xl font-bold text-slate-800 flex items-center gap-2">
              <Activity className="text-blue-600" /> SCADA Agent Dashboard
            </h1>
            <p className="text-slate-500">Monitoramento Industrial em Tempo Real</p>
          </div>
          <div className={`flex items-center gap-2 px-3 py-1 rounded-full text-xs font-bold ${isConnected ? 'bg-green-100 text-green-700' : 'bg-red-100 text-red-700'}`}>
            <div className={`w-2 h-2 rounded-full ${isConnected ? 'bg-green-500 animate-pulse' : 'bg-red-500'}`} />
            {isConnected ? 'SISTEMA ONLINE' : 'SISTEMA OFFLINE'}
          </div>
        </header>

        {/* Navegação de Abas */}
        <div className="flex space-x-4 border-b border-slate-200">
          <button
            onClick={() => setView('dashboard')}
            className={`pb-3 flex items-center gap-2 text-sm font-medium transition-colors ${
              view === 'dashboard' 
                ? 'border-b-2 border-blue-600 text-blue-600' 
                : 'text-slate-500 hover:text-slate-700'
            }`}
          >
            <LayoutDashboard size={18} />
            Dashboard IA
          </button>
          <button
            onClick={() => setView('scada')}
            className={`pb-3 flex items-center gap-2 text-sm font-medium transition-colors ${
              view === 'scada' 
                ? 'border-b-2 border-blue-600 text-blue-600' 
                : 'text-slate-500 hover:text-slate-700'
            }`}
          >
            <Globe size={18} />
            Acesso SCADA-LTS
          </button>
        </div>

        {/* Conteúdo Principal (Alternável) */}
        <div className="flex-1 flex flex-col min-h-0">
          {view === 'dashboard' ? (
            <div className="space-y-6">
              {/* Grid de Sensores */}
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                <SensorCard 
                  label="Pressão PT1" 
                  value={data?.values.pt1 || 0} 
                  unit="bar" 
                  icon={Gauge} 
                  color="bg-blue-500" 
                />
                <SensorCard 
                  label="Pressão PT2" 
                  value={data?.values.pt2 || 0} 
                  unit="bar" 
                  icon={Thermometer} 
                  color="bg-indigo-500" 
                />
                <SensorCard 
                  label="Vazão FT1" 
                  value={data?.values.ft1 || 0} 
                  unit="m³/h" 
                  icon={Wind} 
                  color="bg-cyan-500" 
                />
                <SensorCard 
                  label="Válvula CV" 
                  value={data?.values.cv || 0} 
                  unit="%" 
                  icon={Settings} 
                  color="bg-slate-700" 
                />
                <SensorCard 
                  label="Bomba Freq" 
                  value={data?.values.freq1 || 0} 
                  unit="Hz" 
                  icon={Zap} 
                  color="bg-orange-500" 
                />
              </div>

              {/* Gráfico Principal */}
              <div className="bg-white p-6 rounded-2xl shadow-sm border border-slate-200 flex-1">
                <h3 className="text-lg font-semibold text-slate-800 mb-4">Tendência das Pressões</h3>
                <div className="h-64">
                  <ResponsiveContainer width="100%" height="100%">
                    <LineChart data={history}>
                      <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#f1f5f9" />
                      <XAxis dataKey="time" hide />
                      <YAxis stroke="#94a3b8" fontSize={12} tickLine={false} axisLine={false} />
                      <Tooltip />
                      <Line type="monotone" dataKey="pt1" stroke="#3b82f6" strokeWidth={3} dot={false} isAnimationActive={false} />
                      <Line type="monotone" dataKey="pt2" stroke="#6366f1" strokeWidth={3} dot={false} isAnimationActive={false} />
                    </LineChart>
                  </ResponsiveContainer>
                </div>
              </div>
            </div>
          ) : (
            <div className="flex-1 bg-white rounded-2xl shadow-sm border border-slate-200 overflow-hidden flex flex-col">
              <iframe 
                src={scadaUrl} 
                className="w-full h-full border-0"
                title="SCADA-LTS Interface"
              />
            </div>
          )}
        </div>
      </div>

      {/* --- COLUNA DE CHAT (IA) --- */}
      <div className="w-1/3 bg-white border-l border-slate-200 flex flex-col shadow-xl">
        <div className="p-4 border-b border-slate-100 flex items-center space-x-3">
          <div className="bg-blue-600 p-2 rounded-lg">
            <MessageSquare className="text-white" size={20} />
          </div>
          <div>
            <h2 className="font-bold text-slate-800">Assistente Inteligente</h2>
            <p className="text-xs text-slate-400">Powered by Gemini / Claude</p>
          </div>
        </div>

        {/* Mensagens */}
        <div className="flex-1 overflow-y-auto p-4 space-y-4">
          {messages.map((msg, idx) => (
            <div key={idx} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
              <div className={`max-w-[85%] p-3 rounded-2xl ${
                msg.role === 'user' 
                  ? 'bg-blue-600 text-white rounded-br-none' 
                  : 'bg-slate-100 text-slate-800 rounded-bl-none border border-slate-200'
              }`}>
                <p className="text-sm whitespace-pre-wrap">{msg.content}</p>
                
                {/* Card de Ação IA */}
                {msg.tool_request && (
                  <div className="mt-3 bg-white p-3 rounded-xl border border-slate-200 shadow-sm text-slate-800">
                    <p className="text-xs font-bold text-slate-400 mb-2 flex items-center gap-1">
                      <AlertCircle size={12} /> AÇÃO RECOMENDADA
                    </p>
                    <p className="text-sm font-semibold mb-3">
                      Definir <span className="text-blue-600">{msg.tool_request.args.tag}</span> para <span className="text-blue-600">{msg.tool_request.args.value}</span>?
                    </p>
                    <div className="flex gap-2">
                      <button 
                        onClick={() => handleApproveAction(msg.tool_request!.args.tag, msg.tool_request!.args.value)}
                        className="flex-1 bg-green-500 hover:bg-green-600 text-white text-xs py-2 rounded-lg font-bold transition-colors flex items-center justify-center gap-1"
                      >
                        <CheckCircle2 size={14} /> APROVAR
                      </button>
                      <button className="flex-1 bg-slate-100 hover:bg-slate-200 text-slate-500 text-xs py-2 rounded-lg font-bold transition-colors">
                        RECUSAR
                      </button>
                    </div>
                  </div>
                )}
              </div>
            </div>
          ))}
          {isTyping && (
            <div className="flex justify-start">
              <div className="bg-slate-100 p-3 rounded-2xl rounded-bl-none animate-pulse text-slate-400 text-xs">
                IA está pensando...
              </div>
            </div>
          )}
          <div ref={chatEndRef} />
        </div>

        {/* Input */}
        <div className="p-4 border-t border-slate-100">
          <div className="relative">
            <input 
              type="text" 
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyPress={(e) => e.key === 'Enter' && handleSendMessage()}
              placeholder="Pergunte sobre o sistema..."
              className="w-full bg-slate-50 border border-slate-200 rounded-xl py-3 pl-4 pr-12 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all"
            />
            <button 
              onClick={handleSendMessage}
              className="absolute right-2 top-2 bg-blue-600 p-1.5 rounded-lg text-white hover:bg-blue-700 transition-colors"
            >
              <Send size={18} />
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

export default App;