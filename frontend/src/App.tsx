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
  Globe,
  Droplets,
  ArrowUpRight,
  ArrowDownRight,
  Plus,
  Trash2,
  X
} from 'lucide-react';
import axios from 'axios';
import { 
  AreaChart,
  Area,
  ResponsiveContainer,
  YAxis 
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

interface PointDetail {
  name: string;
  xid: string;
  friendly_name: string;
  unit: string;
  min_val: number;
  max_val: number;
}

// --- Componente Industrial Sensor Card v2 (Refinado + Draggable) ---
const IndustrialSensorCard = ({ 
  label, value, unit, icon: Icon, color, stroke, history, minLimit, maxLimit,
  onDragStart, onDragOver, onDrop, isDragging 
}: any) => {
  // Calcula estatísticas locais para dar contexto
  const relevantHistory = history.map((h: any) => h[label] || 0);
  const min = relevantHistory.length ? Math.min(...relevantHistory) : 0;
  const max = relevantHistory.length ? Math.max(...relevantHistory) : 0;
  
  // Tendência
  const last = relevantHistory[relevantHistory.length - 1] || 0;
  const prev = relevantHistory[relevantHistory.length - 2] || 0;
  const isRising = last > prev;

  return (
    <div 
      draggable
      onDragStart={onDragStart}
      onDragOver={onDragOver}
      onDrop={onDrop}
      className={`bg-white rounded-xl shadow-sm border border-slate-200 overflow-hidden flex flex-col h-64 transition-all duration-300 hover:shadow-lg hover:border-blue-300 group hover:-translate-y-1 cursor-grab active:cursor-grabbing ${isDragging ? 'opacity-50 scale-95 border-blue-400 border-dashed' : ''}`}
    >
      {/* Header com indicador de tipo */}
      <div className={`px-5 py-4 flex justify-between items-center border-b border-slate-50 bg-white border-l-[6px] ${color.replace('bg-', 'border-')}`}>
        <div className="flex items-center gap-2.5">
          <div className={`p-1.5 rounded-lg ${color} bg-opacity-10`}>
             <Icon size={18} className={`${color.replace('bg-', 'text-')}`} />
          </div>
          <h3 className="font-bold text-slate-600 uppercase text-xs tracking-wider">{label}</h3>
        </div>
        <div className={`flex items-center text-xs font-bold px-2 py-1 rounded-full ${isRising ? 'bg-green-50 text-green-600' : 'bg-red-50 text-red-500'}`}>
          {isRising ? <ArrowUpRight size={14} /> : <ArrowDownRight size={14} />}
        </div>
      </div>

      {/* Display Principal */}
      <div className="px-6 py-2 flex-1 flex flex-col justify-center">
        <div className="flex items-baseline gap-1">
          <span className="text-5xl font-sans font-bold text-slate-800 tracking-tight tabular-nums">
            {typeof value === 'number' ? value.toFixed(1) : '--'}
          </span>
          <span className="text-xl text-slate-400 font-medium ml-1">{unit}</span>
        </div>
      </div>

      {/* Área de Contexto e Gráfico */}
      <div className="h-24 bg-slate-50 border-t border-slate-100 relative flex flex-col justify-end pb-0">
         {/* Stats Labels */}
        <div className="absolute top-2 left-4 flex gap-4 text-xs font-medium text-slate-500 z-10">
           <span className="flex items-center gap-1"><span className="w-1.5 h-1.5 rounded-full bg-blue-400"></span> Min: {min.toFixed(1)}</span>
           <span className="flex items-center gap-1"><span className="w-1.5 h-1.5 rounded-full bg-orange-400"></span> Max: {max.toFixed(1)}</span>
        </div>
        
        {/* Gráfico Sparkline Contido */}
        <div className="w-full h-16 opacity-80">
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={history}>
              <defs>
                <linearGradient id={`fill-${label}`} x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor={stroke} stopOpacity={0.3}/>
                  <stop offset="95%" stopColor={stroke} stopOpacity={0.0}/>
                </linearGradient>
              </defs>
              <YAxis domain={['auto', 'auto']} hide />
              <Area 
                type="monotone" 
                dataKey={label} 
                stroke={stroke} 
                strokeWidth={2.5} 
                fill={`url(#fill-${label})`} 
                isAnimationActive={false}
              />
            </AreaChart>
          </ResponsiveContainer>
        </div>
      </div>
    </div>
  );
};

function App() {
  // Estados
  const [data, setData] = useState<SensorData | null>(null);
  const [history, setHistory] = useState<any[]>([]);
  const [sensorConfig, setSensorConfig] = useState<Record<string, string>>({});
  const [pointDetails, setPointDetails] = useState<PointDetail[]>([]);
  const [messages, setMessages] = useState<Message[]>([
    { role: 'assistant', content: 'Olá! Sou seu assistente SCADA. Como posso ajudar hoje?' }
  ]);
  const [input, setInput] = useState('');
  const [isConnected, setIsConnected] = useState(false);
  const [isTyping, setIsTyping] = useState(false);
  const [view, setView] = useState<'dashboard' | 'scada'>('dashboard');
  const [scadaUrl, setScadaUrl] = useState<string>(import.meta.env.VITE_SCADA_DASHBOARD_URL || '');
  
  // Modal State
  const [showConfigModal, setShowConfigModal] = useState(false);
  const [newPoint, setNewPoint] = useState({ name: '', xid: '', friendly_name: '', unit: '', min_val: 0, max_val: 100 });

  // Drag State
  const [draggedIndex, setDraggedIndex] = useState<number | null>(null);

  const chatEndRef = useRef<HTMLDivElement>(null);

  // Heurística de Estilo
  const getSensorStyle = (name: string, explicitUnit?: string) => {
    const n = name.toLowerCase();
    let style = { icon: Zap, color: 'bg-slate-500', stroke: '#64748b', unit: '' };
    
    // Temperaturas
    if (n.includes('temp') || n.includes('t_') || n.includes('grau')) 
      style = { icon: Thermometer, color: 'bg-orange-500', stroke: '#f97316', unit: '°C' };
    // Pressões
    else if (n.includes('press') || n.includes('pt') || n.includes('bar')) 
      style = { icon: Gauge, color: 'bg-blue-500', stroke: '#3b82f6', unit: 'bar' };
    // Vazões
    else if (n.includes('vaz') || n.includes('ft') || n.includes('flow')) 
      style = { icon: Wind, color: 'bg-cyan-500', stroke: '#06b6d4', unit: 'm³/h' };
    // Elétrica
    else if (n.includes('freq') || n.includes('hz') || n.includes('rpm')) 
      style = { icon: Activity, color: 'bg-purple-500', stroke: '#a855f7', unit: 'Hz' };
    else if (n.includes('cv') || n.includes('valve') || n.includes('valvula')) 
        style = { icon: Settings, color: 'bg-slate-600', stroke: '#475569', unit: '%' };
    else if (n.includes('nivel') || n.includes('lvl') || n.includes('tank')) 
        style = { icon: Droplets, color: 'bg-blue-400', stroke: '#60a5fa', unit: '%' };

    if (explicitUnit) style.unit = explicitUnit;
    return style;
  };

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const fetchConfig = async () => {
    try {
      const [statusRes, configRes] = await Promise.all([
        axios.get('http://localhost:8000/api/status'),
        axios.get('http://localhost:8000/api/config')
      ]);
      
      const backendDash = statusRes.data.scada_dashboard_url;
      const localEnvDash = import.meta.env.VITE_SCADA_DASHBOARD_URL;
      const backendBase = statusRes.data.scada_url;
      let finalUrl = backendDash || localEnvDash || backendBase;
      if (finalUrl) setScadaUrl(finalUrl);
      
      if (configRes.data.points) {
        setSensorConfig(configRes.data.points);
      }
      if (configRes.data.details) {
        setPointDetails(configRes.data.details);
      }
    } catch (err) {
      console.error("Erro ao buscar configurações:", err);
    }
  };

  useEffect(() => { fetchConfig(); }, []);

  const handleAddPoint = async () => {
    try {
      await axios.post('http://localhost:8000/api/points', newPoint);
      setNewPoint({ name: '', xid: '', friendly_name: '', unit: '', min_val: 0, max_val: 100 });
      fetchConfig();
      alert("Ponto adicionado!");
    } catch (err) {
      alert("Erro ao adicionar ponto. Verifique se o nome é único.");
    }
  };

  const handleDeletePoint = async (name: string) => {
    if (!confirm(`Remover sensor ${name}?`)) return;
    try {
      await axios.delete(`http://localhost:8000/api/points/${name}`);
      fetchConfig();
    } catch (err) {
      alert("Erro ao remover ponto.");
    }
  };

  // Drag & Drop Handlers
  const handleDragStart = (index: number) => {
    setDraggedIndex(index);
  };

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault(); 
  };

  const handleDrop = async (targetIndex: number) => {
    if (draggedIndex === null || draggedIndex === targetIndex) return;

    const newOrder = [...pointDetails];
    const item = newOrder.splice(draggedIndex, 1)[0];
    newOrder.splice(targetIndex, 0, item);
    
    setPointDetails(newOrder);
    setDraggedIndex(null);

    try {
        const orderedNames = newOrder.map(p => p.name);
        await axios.post('http://localhost:8000/api/points/reorder', { points: orderedNames });
    } catch (err) {
        console.error("Erro ao salvar ordem:", err);
        fetchConfig();
    }
  };

  useEffect(() => {
    let socket: WebSocket | null = null;
    let reconnectTimeout: number;

    const connect = () => {
      socket = new WebSocket('ws://localhost:8000/ws/data');
      socket.onopen = () => setIsConnected(true);
      socket.onclose = () => {
        setIsConnected(false);
        reconnectTimeout = window.setTimeout(connect, 3000);
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
          return updated.length > 50 ? updated.slice(1) : updated;
        });
      };
    };
    connect();
    return () => { if (socket) socket.close(); clearTimeout(reconnectTimeout); };
  }, []);

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
      console.error("Erro IA:", error);
    } finally {
      setIsTyping(false);
    }
  };

  const handleApproveAction = async (tag: string, value: number) => {
    try {
      await axios.post('http://localhost:8000/api/action/approve', { tag, value });
      setMessages(prev => [...prev, { role: 'assistant', content: `✅ Comando executado: ${tag} -> ${value}.` }]);
    } catch (error) { alert("Falha ao executar ação."); }
  };

  return (
    <div className="flex h-screen bg-slate-50 font-sans overflow-hidden relative">
      <div className="w-2/3 flex flex-col p-6 space-y-6 overflow-y-auto">
        <header className="flex justify-between items-center">
          <div>
            <h1 className="text-2xl font-bold text-slate-800 flex items-center gap-2">
              <Activity className="text-blue-600" /> SCADA Agent
            </h1>
            <p className="text-slate-500">Monitoramento Industrial</p>
          </div>
          <div className="flex items-center gap-3">
             <div className={`flex items-center gap-2 px-3 py-1 rounded-full text-xs font-bold ${isConnected ? 'bg-green-100 text-green-700' : 'bg-red-100 text-red-700'}`}>
              <div className={`w-2 h-2 rounded-full ${isConnected ? 'bg-green-500 animate-pulse' : 'bg-red-500'}`} />
              {isConnected ? 'ONLINE' : 'OFFLINE'}
            </div>
            <button onClick={() => setShowConfigModal(true)} className="p-2 text-slate-400 hover:text-blue-600 hover:bg-blue-50 rounded-lg transition-colors">
              <Settings size={20} />
            </button>
          </div>
        </header>

        <div className="flex space-x-4 border-b border-slate-200">
          <button onClick={() => setView('dashboard')} className={`pb-3 flex items-center gap-2 text-sm font-medium ${view === 'dashboard' ? 'border-b-2 border-blue-600 text-blue-600' : 'text-slate-500'}`}>
            <LayoutDashboard size={18} /> Dashboard IA
          </button>
          <button onClick={() => setView('scada')} className={`pb-3 flex items-center gap-2 text-sm font-medium ${view === 'scada' ? 'border-b-2 border-blue-600 text-blue-600' : 'text-slate-500'}`}>
            <Globe size={18} /> SCADA-LTS
          </button>
        </div>

        <div className="flex-1 flex flex-col min-h-0">
          {view === 'dashboard' ? (
            <div className="h-full overflow-y-auto pr-2">
              <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-6 pt-4">
                {pointDetails.length > 0 ? (
                  pointDetails.map((point, index) => {
                    const style = getSensorStyle(point.name, point.unit);
                    return (
                      <IndustrialSensorCard 
                        key={point.name}
                        label={point.friendly_name || point.name}
                        value={data?.values[point.name] || 0} 
                        unit={style.unit} 
                        icon={style.icon} 
                        color={style.color}
                        stroke={style.stroke}
                        history={history}
                        minLimit={point.min_val}
                        maxLimit={point.max_val}
                        
                        isDragging={draggedIndex === index}
                        onDragStart={() => handleDragStart(index)}
                        onDragOver={handleDragOver}
                        onDrop={() => handleDrop(index)}
                      />
                    );
                  })
                ) : (
                  <div className="col-span-full flex flex-col items-center justify-center py-20 text-slate-400">
                    <Activity size={48} className="mb-4 opacity-20" />
                    <p>Nenhum sensor configurado.</p>
                    <button onClick={() => setShowConfigModal(true)} className="mt-4 text-blue-600 font-bold hover:underline">Configurar agora</button>
                  </div>
                )}
              </div>
            </div>
          ) : (
            <div className="flex-1 bg-white rounded-2xl shadow-sm border border-slate-200 overflow-hidden flex flex-col mt-4">
              <iframe src={scadaUrl} className="w-full h-full border-0" title="SCADA-LTS" />
            </div>
          )}
        </div>
      </div>

      <div className="w-1/3 bg-white border-l border-slate-200 flex flex-col shadow-xl">
        <div className="p-4 border-b border-slate-100 flex items-center space-x-3">
          <div className="bg-blue-600 p-2 rounded-lg"><MessageSquare className="text-white" size={20} /></div>
          <div><h2 className="font-bold text-slate-800">Assistente IA</h2><p className="text-xs text-slate-400">Gemini 2.5 Flash</p></div>
        </div>
        <div className="flex-1 overflow-y-auto p-4 space-y-4">
          {messages.map((msg, idx) => (
            <div key={idx} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
              <div className={`max-w-[85%] p-3 rounded-2xl ${msg.role === 'user' ? 'bg-blue-600 text-white rounded-br-none' : 'bg-slate-100 text-slate-800 rounded-bl-none border border-slate-200'}`}>
                <p className="text-sm whitespace-pre-wrap">{msg.content}</p>
                {msg.tool_request && (
                  <div className="mt-3 bg-white p-3 rounded-xl border border-slate-200 shadow-sm text-slate-800">
                    <p className="text-xs font-bold text-slate-400 mb-2 flex items-center gap-1"><AlertCircle size={12} /> AÇÃO</p>
                    <p className="text-sm font-semibold mb-3">Definir <span className="text-blue-600">{msg.tool_request.args.tag}</span> para <span className="text-blue-600">{msg.tool_request.args.value}</span>?</p>
                    <div className="flex gap-2">
                      <button onClick={() => handleApproveAction(msg.tool_request!.args.tag, msg.tool_request!.args.value)} className="flex-1 bg-green-500 text-white text-xs py-2 rounded-lg font-bold flex justify-center gap-1"><CheckCircle2 size={14}/> APROVAR</button>
                      <button className="flex-1 bg-slate-100 text-slate-500 text-xs py-2 rounded-lg font-bold">RECUSAR</button>
                    </div>
                  </div>
                )}
              </div>
            </div>
          ))}
          {isTyping && <div className="flex justify-start"><div className="bg-slate-100 p-3 rounded-2xl rounded-bl-none animate-pulse text-slate-400 text-xs">Pensando...</div></div>}
          <div ref={chatEndRef} />
        </div>
        <div className="p-4 border-t border-slate-100 relative">
          <input type="text" value={input} onChange={(e) => setInput(e.target.value)} onKeyPress={(e) => e.key === 'Enter' && handleSendMessage()} placeholder="Pergunte ao sistema..." className="w-full bg-slate-50 border border-slate-200 rounded-xl py-3 pl-4 pr-12 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500" />
          <button onClick={handleSendMessage} className="absolute right-6 top-6 text-blue-600"><Send size={18} /></button>
        </div>
      </div>

      {showConfigModal && (
        <div className="absolute inset-0 z-50 bg-slate-900/50 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-white w-full max-w-2xl rounded-2xl shadow-2xl overflow-hidden flex flex-col max-h-[90vh]">
            <div className="p-4 border-b border-slate-100 flex justify-between items-center bg-slate-50">
              <h2 className="text-lg font-bold text-slate-800 flex items-center gap-2">
                <Settings className="text-blue-600" size={20} /> Configuração de Sensores
              </h2>
              <button onClick={() => setShowConfigModal(false)} className="text-slate-400 hover:text-slate-600"><X size={24} /></button>
            </div>
            
            <div className="p-6 overflow-y-auto">
              <div className="bg-blue-50 p-4 rounded-xl border border-blue-100 mb-6">
                <h3 className="text-sm font-bold text-blue-800 mb-3 flex items-center gap-1"><Plus size={16}/> Adicionar Novo Ponto</h3>
                <div className="grid grid-cols-2 gap-3 mb-3">
                  <input placeholder="ID Interno (ex: pt3)" className="p-2 text-sm border rounded" value={newPoint.name} onChange={e => setNewPoint({...newPoint, name: e.target.value})} />
                  <input placeholder="XID SCADA (ex: DP_123)" className="p-2 text-sm border rounded" value={newPoint.xid} onChange={e => setNewPoint({...newPoint, xid: e.target.value})} />
                  <input placeholder="Nome Amigável" className="p-2 text-sm border rounded" value={newPoint.friendly_name} onChange={e => setNewPoint({...newPoint, friendly_name: e.target.value})} />
                  <input placeholder="Unidade (ex: bar)" className="p-2 text-sm border rounded" value={newPoint.unit} onChange={e => setNewPoint({...newPoint, unit: e.target.value})} />
                  <div className="flex gap-2">
                    <input type="number" placeholder="Min" className="p-2 text-sm border rounded w-full" value={newPoint.min_val} onChange={e => setNewPoint({...newPoint, min_val: parseFloat(e.target.value)})} />
                    <input type="number" placeholder="Max" className="p-2 text-sm border rounded w-full" value={newPoint.max_val} onChange={e => setNewPoint({...newPoint, max_val: parseFloat(e.target.value)})} />
                  </div>
                </div>
                <button onClick={handleAddPoint} className="w-full bg-blue-600 text-white py-2 rounded-lg font-bold hover:bg-blue-700 text-sm">Adicionar Ponto</button>
              </div>

              <h3 className="text-sm font-bold text-slate-500 uppercase tracking-wider mb-3">Sensores Ativos</h3>
              <div className="space-y-2">
                {pointDetails.map(pt => (
                  <div key={pt.name} className="flex justify-between items-center p-3 bg-slate-50 rounded-lg border border-slate-100 group">
                    <div>
                      <div className="font-bold text-slate-800 text-sm">{pt.friendly_name} <span className="text-slate-400 font-mono text-xs">({pt.name})</span></div>
                      <div className="text-xs text-slate-500 font-mono">{pt.xid} • {pt.unit || 's/ un'} • Range: {pt.min_val}-{pt.max_val}</div>
                    </div>
                    <button onClick={() => handleDeletePoint(pt.name)} className="text-slate-300 hover:text-red-500 p-2"><Trash2 size={18} /></button>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default App;