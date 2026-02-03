from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from typing import Dict, Any, Optional
from pydantic import BaseModel
import logging
import os
import asyncio
import json
from pathlib import Path
from dotenv import load_dotenv

# Carrega .env usando caminho absoluto da raiz do projeto
BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

from src import AppConfig, ScadaClient, DataCollector, create_agent
from src.llm_agent import LLMAgent, ToolRequest

# Configuração de Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("api_server")

# Modelos Pydantic para API
class ChatRequest(BaseModel):
    message: str

class ChatResponse(BaseModel):
    response: str
    tool_request: Optional[Dict[str, Any]] = None

class ActionRequest(BaseModel):
    tag: str
    value: float

# Estado Global (Singleton)
class SystemState:
    config: AppConfig = None
    client: ScadaClient = None
    collector: DataCollector = None
    agent: LLMAgent = None

state = SystemState()

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Gerencia o ciclo de vida da aplicação.
    Executa na inicialização e no encerramento.
    """
    # --- INICIALIZAÇÃO ---
    logger.info("🚀 Inicializando servidor SCADA Agent...")
    try:
        state.config = AppConfig.from_env()
    except SystemExit:
        logger.error("❌ Falha ao carregar configurações.")
        raise RuntimeError("Configuração inválida")

    # 1. Conecta ao SCADA
    state.client = ScadaClient(state.config.scada, state.config.points)
    if state.client.connect():
        logger.info(f"✅ Conectado ao SCADA: {state.config.scada.base_url}")
    else:
        logger.warning(f"⚠️ Falha ao conectar no SCADA: {state.client.last_error}")

    # 2. Inicia Coletor
    state.collector = DataCollector(state.client, state.config.collector)
    state.collector.start()
    logger.info("📡 Coletor de dados iniciado")

    # 3. Inicia Agente IA
    api_key = state.config.llm.api_key
    use_mock = not api_key
    state.agent = create_agent(api_key=api_key, collector=state.collector, use_mock=use_mock)
    logger.info(f"🤖 Agente IA iniciado (Mock: {use_mock})")
    
    yield
    
    # --- ENCERRAMENTO ---
    logger.info("🛑 Encerrando servidor...")
    if state.collector:
        state.collector.stop()
    if state.client:
        state.client.disconnect()

# Criação do App FastAPI
app = FastAPI(title="SCADA Agent API", lifespan=lifespan)

# Configuração de CORS (Permite acesso do React)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Em produção, restringir para o domínio do frontend
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    return {"message": "SCADA Agent API Running", "version": "1.1.0"}

@app.get("/api/status")
async def get_status():
    """Status do sistema"""
    return {
        "scada_connected": state.client.connected if state.client else False,
        "scada_url": state.config.scada.base_url if state.config else "",
        "provider": state.config.llm.provider if state.config else "unknown",
        "collector": state.collector.get_status() if state.collector else {}
    }

@app.websocket("/ws/data")
async def websocket_endpoint(websocket: WebSocket):
    """
    WebSocket para envio de dados em tempo real.
    Envia snapshot dos sensores a cada 1s.
    """
    await websocket.accept()
    try:
        while True:
            if state.collector:
                snapshot = state.collector.get_latest()
                if snapshot:
                    data = {
                        "timestamp": snapshot.timestamp.isoformat(),
                        "values": snapshot.values
                    }
                    await websocket.send_json(data)
            
            # Aguarda 1s antes do próximo envio
            await asyncio.sleep(1)
            
    except WebSocketDisconnect:
        logger.info("Cliente desconectado do WebSocket")
    except Exception as e:
        logger.error(f"Erro no WebSocket: {e}")

@app.post("/api/chat", response_model=ChatResponse)
async def chat_endpoint(request: ChatRequest):
    """
    Processa mensagem do chat via LLM Agent.
    """
    if not state.agent:
        raise HTTPException(status_code=503, detail="Agent not initialized")
    
    try:
        # Envia pergunta ao agente (ele já busca contexto do coletor internamente)
        response = state.agent.ask(request.message)
        
        # Formata resposta
        result = {"response": "", "tool_request": None}
        
        if isinstance(response, ToolRequest):
            # Agente quer executar uma ação
            result["tool_request"] = {
                "tool": response.tool_name,
                "args": response.arguments,
                "thought": response.thought
            }
            # A "resposta" de texto é o pensamento do agente
            result["response"] = response.thought 
        else:
            # Resposta puramente textual
            result["response"] = str(response)
            
        return result
        
    except Exception as e:
        logger.error(f"Erro no chat: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/action/approve")
async def approve_action(action: ActionRequest):
    """
    Executa uma ação aprovada pelo operador.
    """
    if not state.client:
        raise HTTPException(status_code=503, detail="SCADA client not initialized")
        
    # 1. Validação de Segurança (Dupla checagem)
    is_safe, reason = state.config.safety.is_safe(action.tag, action.value)
    if not is_safe:
        raise HTTPException(status_code=400, detail=f"Blocked by Safety: {reason}")
    
    # 2. Execução
    success = state.client.write_point(action.tag, action.value)
    
    if success:
        logger.info(f"✅ Ação executada via API: {action.tag} -> {action.value}")
        return {"status": "success", "message": f"Written {action.value} to {action.tag}"}
    else:
        logger.error(f"❌ Falha ao escrever {action.tag}")
        raise HTTPException(status_code=502, detail=f"Failed to write to SCADA: {state.client.last_error}")
