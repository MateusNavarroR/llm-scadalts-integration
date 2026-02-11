from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect, Request
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from typing import Dict, Any, Optional, List
from pydantic import BaseModel
import logging
import os
import asyncio
import json
import httpx
from pathlib import Path
from dotenv import load_dotenv

# Carrega .env usando caminho absoluto da raiz do projeto
BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env", override=True)

from src import AppConfig, ScadaClient, DataCollector, create_agent, PointsConfig
from src.llm_agent import LLMAgent, ToolRequest
from src.point_manager import PointManager, PointDetail

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

class PointCreateRequest(BaseModel):
    name: str
    xid: str
    friendly_name: str
    unit: str = ""
    min_val: float = 0.0
    max_val: float = 100.0

class PointReorderRequest(BaseModel):
    points: List[str]

# Estado Global (Singleton)
class SystemState:
    config: AppConfig = None
    client: ScadaClient = None
    collector: DataCollector = None
    agent: LLMAgent = None
    point_manager: PointManager = None

state = SystemState()

def refresh_system_config():
    """Atualiza componentes do sistema com a nova configuração de pontos"""
    if not state.point_manager or not state.client:
        return

    # Reconstrói o PointsConfig a partir do gerenciador
    points_list = state.point_manager.get_all()
    new_points_config = PointsConfig(points_list=points_list)
    
    # Atualiza Cliente SCADA
    state.client.update_config(new_points_config)
    
    # Atualiza Config Global (para referência)
    if state.config:
        state.config.points = new_points_config
        
    # Atualiza o Coletor de Dados (Hot Reload)
    if state.collector:
        state.collector.update_points_list(list(new_points_config.points.keys()))
        
    logger.info("Configuração do sistema atualizada (Hot Reload)")

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

    # 0. Inicializa Gerenciador de Pontos (Persistência)
    state.point_manager = PointManager()
    
    # Sobrescreve a config inicial com o que está no JSON (se houver)
    # Isso garante que edições salvas persistam sobre o .env
    current_points = state.point_manager.get_all()
    if current_points:
        state.config.points = PointsConfig(points_list=current_points)

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
    return {"message": "SCADA Agent API Running", "version": "1.2.0"}

@app.get("/api/status")
async def get_status():
    """Status do sistema"""
    # URL Base do SCADA real
    base_url = state.config.scada.base_url if state.config else ""
    
    # Para o Dashboard (Iframe), SEMPRE usamos o proxy local.
    # Isso resolve problemas de CORS, Mixed Content (HTTP/HTTPS) e X-Frame-Options.
    # O frontend vai carregar o iframe apontando para http://localhost:8000/Scada-LTS/
    dash_url = "http://localhost:8000/Scada-LTS/"
    
    return {
        "scada_connected": state.client.connected if state.client else False,
        "scada_url": base_url,
        "scada_dashboard_url": dash_url,
        "provider": state.config.llm.provider if state.config else "unknown",
        "collector": state.collector.get_status() if state.collector else {}
    }

@app.get("/api/config")
async def get_config():
    """Retorna configuração detalhada dos sensores disponíveis"""
    if not state.point_manager:
        return {"points": {}}
    
    # Retorna lista rica para o frontend novo e dict simples para compatibilidade
    points_list = state.point_manager.get_all()
    points_dict = {p.name: p.xid for p in points_list} # Compatibilidade
    
    return {
        "points": points_dict,
        "details": [p.to_dict() for p in points_list] # Nova estrutura rica
    }

@app.post("/api/points")
async def add_point(point: PointCreateRequest):
    """Adiciona um novo ponto de dados"""
    new_point = PointDetail(
        name=point.name,
        xid=point.xid,
        friendly_name=point.friendly_name,
        unit=point.unit,
        min_val=point.min_val,
        max_val=point.max_val
    )
    
    if state.point_manager.add_point(new_point):
        refresh_system_config()
        return {"status": "success", "message": f"Ponto {point.name} adicionado."}
    else:
        raise HTTPException(status_code=400, detail="Ponto com esse nome já existe.")

@app.post("/api/points/reorder")
async def reorder_points(request: PointReorderRequest):
    """Reordena a lista de pontos"""
    if state.point_manager.reorder_points(request.points):
        refresh_system_config()
        return {"status": "success", "message": "Pontos reordenados."}
    else:
        raise HTTPException(status_code=400, detail="Falha ao reordenar.")

@app.delete("/api/points/{name}")
async def delete_point(name: str):
    """Remove um ponto de dados"""
    if state.point_manager.delete_point(name):
        refresh_system_config()
        return {"status": "success", "message": f"Ponto {name} removido."}
    else:
        raise HTTPException(status_code=404, detail="Ponto não encontrado.")

from starlette.background import BackgroundTask

@app.api_route("/Scada-LTS/{path_name:path}", methods=["GET", "POST", "PUT", "DELETE", "HEAD", "OPTIONS"])
async def proxy_scada(path_name: str, request: Request):
    """
    Reverse Proxy para o SCADA-LTS.
    Remove headers de segurança (X-Frame-Options) para permitir iframe.
    Também reescreve redirects para manter o usuário no proxy.
    """
    if not state.config:
        raise HTTPException(status_code=503, detail="Config not loaded")
        
    # URL Base do SCADA real (ex: http://localhost:8080/Scada-LTS)
    base_url = state.config.scada.base_url.rstrip('/')
    
    # Target URL construction
    target_url = f"{base_url}/{path_name}"
    
    # Copia headers do request original (exceto host)
    req_headers = dict(request.headers)
    req_headers.pop("host", None)
    req_headers.pop("content-length", None)
    
    # --- FIX 403 Forbidden (CSRF/CORS) ---
    # Força Origin e Referer para o próprio domínio do SCADA.
    # Isso impede que o SCADA rejeite requisições vindas do proxy/frontend.
    req_headers["origin"] = base_url
    req_headers["referer"] = target_url
    
    # Cria cliente sem context manager para persistir durante o stream
    client = httpx.AsyncClient(follow_redirects=False)
    
    try:
        body = await request.body()
        
        rp_req = client.build_request(
            request.method,
            target_url,
            headers=req_headers,
            content=body,
            params=request.query_params,
            cookies=request.cookies,
            timeout=30.0
        )
        
        rp_resp = await client.send(rp_req, stream=True)
        
        # Headers proibidos ou que devem ser ignorados
        excluded_headers = {
            "content-encoding", 
            "content-length", 
            "transfer-encoding", 
            "connection", 
            "x-frame-options", 
            "content-security-policy"
        }
        
        # Proxy base URL
        proxy_base = "http://localhost:8000/Scada-LTS"

        # Cria a resposta inicial
        response = StreamingResponse(
            rp_resp.aiter_raw(),
            status_code=rp_resp.status_code,
            background=BackgroundTask(client.aclose)
        )
        
        # Copia e processa headers preservando múltiplos valores (ex: Set-Cookie)
        for key, value in rp_resp.headers.multi_items():
            if key.lower() in excluded_headers:
                continue
            
            # Rewrite Location header
            if key.lower() == "location":
                if base_url in value:
                    value = value.replace(base_url, proxy_base)
                    logger.info(f"🔄 Redirect reescrito: {value}")
            
            # Adiciona ao header da resposta
            response.headers.append(key, value)
        
        return response
        
    except httpx.RequestError as exc:
        logger.error(f"Proxy Error: {exc}")
        await client.aclose()
        raise HTTPException(status_code=502, detail=f"Proxy error: {str(exc)}")
    except Exception as e:
        logger.error(f"Unexpected Proxy Error: {e}")
        await client.aclose()
        raise HTTPException(status_code=500, detail=str(e))

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
                    # Sanitiza valores NaN para None (JSON null) para evitar erro no Frontend
                    clean_values = {
                        k: (v if v == v else None) # v != v é o check mais rápido para NaN em Python
                        for k, v in snapshot.values.items()
                    }
                    
                    data = {
                        "timestamp": snapshot.timestamp.isoformat(),
                        "values": clean_values
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
