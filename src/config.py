"""
Configurações centralizadas do projeto SCADA Agent
"""
import os
import sys
from dataclasses import dataclass, field
from typing import Dict

@dataclass
class ScadaConfig:
    """Configurações de conexão com SCADA-LTS"""
    base_url: str = ""
    username: str = ""
    password: str = ""
    timeout: int = 5
    
    @property
    def login_url(self) -> str:
        return f"{self.base_url}/api/auth/{self.username}/{self.password}"
    
    def get_read_url(self, xid: str) -> str:
        return f"{self.base_url}/api/point_value/getValue/{xid}"
    
    def get_write_url(self, xid: str, data_type: int, value: float) -> str:
        return f"{self.base_url}/api/point_value/setValue/{xid}/{data_type}/{value}"

    def validate(self):
        """Verifica se a configuração mínima existe"""
        missing = []
        if not self.base_url: missing.append("SCADA_BASE_URL")
        if not self.username: missing.append("SCADA_USER")
        if not self.password: missing.append("SCADA_PASSWORD")
        
        if missing:
            print(f"❌ ERRO CRÍTICO: Configurações obrigatórias ausentes no .env: {', '.join(missing)}")
            print("   Por favor, configure o arquivo .env baseando-se no .env.example")
            sys.exit(1)


@dataclass
class PointsConfig:
    """Configuração dos pontos de dados (XIDs)"""
    # Mapeamento: nome amigável -> XID
    # Agora carrega vazio por padrão, preenchido via env
    points: Dict[str, str] = field(default_factory=dict)
    
    # Tipos de dados para escrita
    data_types: Dict[str, int] = field(default_factory=lambda: {
        "binary": 1,
        "multistate": 2,
        "numeric": 3,
        "alphanumeric": 4,
    })
    
    def get_xid(self, name: str) -> str:
        """Retorna XID pelo nome amigável"""
        return self.points.get(name, name)


@dataclass
class CollectorConfig:
    """Configurações do coletor de dados"""
    sample_rate_hz: float = 1.0  # Taxa de amostragem
    buffer_size_seconds: int = 300  # 5 minutos de histórico
    
    @property
    def sample_interval(self) -> float:
        return 1.0 / self.sample_rate_hz
    
    @property
    def max_buffer_size(self) -> int:
        return int(self.buffer_size_seconds * self.sample_rate_hz)


@dataclass
class LLMConfig:
    """Configurações do agente LLM"""
    api_key: str = ""
    provider: str = ""  # "anthropic" ou "gemini"
    model: str = ""     # Definido automaticamente ou via env
    max_tokens: int = 4096
    
    # Prompt do sistema para o agente (Conciso e Direto)
    system_prompt: str = """Você é um Engenheiro de Automação Sênior analisando um sistema SCADA.

DIRETRIZ: SEJA EXTREMAMENTE CONCISO E DENSO EM INFORMAÇÃO.
- NÃO repita a lista de valores brutos (o operador já viu isso no painel).
- NÃO explique o óbvio (ex: "800MHz é alto"). Apenas aponte a anomalia.
- FOCUE SOMENTE NA CORRELAÇÃO e no DIAGNÓSTICO.

ESTILO (SEM MARKDOWN):
- Use apenas texto puro e hifens para listas.
- Respostas curtas, estilo "Log Operacional".

CONTEXTO:
- Atuadores: Bomba (Freq) e Válvula (CV).
- Sensores: Pressão (PT1/PT2) e Vazão (FT1).

AO RESPONDER:
1. STATUS: Uma linha (NORMAL / ALERTA / CRÍTICO).
2. ANÁLISE: Pontos principais relacionando as variáveis (ex: "Sem vazão apesar do comando da bomba").
3. AÇÃO: O que verificar fisicamente (ex: "Checar acoplamento da bomba").

Se os dados estiverem normais, responda em no máximo 3 linhas."""

    def __post_init__(self):
        # Tenta carregar API keys do ambiente
        anthropic_key = os.environ.get("ANTHROPIC_API_KEY", "")
        gemini_key = os.environ.get("GEMINI_API_KEY", "")
        
        # 1. Prioridade: Chave manual (passada no construtor)
        if self.api_key:
            pass # Mantém o que veio
            
        # 2. Prioridade: Chave Gemini no Env
        elif gemini_key:
            self.api_key = gemini_key
            self.provider = "gemini"
            
        # 3. Prioridade: Chave Anthropic no Env
        elif anthropic_key:
            self.api_key = anthropic_key
            self.provider = "anthropic"
            
        # CORREÇÃO DE SEGURANÇA: Garante o provedor correto baseado no formato da chave
        if self.api_key and self.api_key.startswith("AIza"):
            self.provider = "gemini"
        elif self.api_key and self.api_key.startswith("sk-ant"):
            self.provider = "anthropic"

        # Define modelo padrão se ainda não definido
        if not self.model and self.provider:
            if self.provider == "gemini":
                # Modelo que validamos no debug_gemini.py
                self.model = "gemini-2.5-flash"
            else:
                self.model = "claude-sonnet-4-20250514"


@dataclass
class AppConfig:
    """Configuração geral da aplicação"""
    scada: ScadaConfig = field(default_factory=ScadaConfig)
    points: PointsConfig = field(default_factory=PointsConfig)
    collector: CollectorConfig = field(default_factory=CollectorConfig)
    llm: LLMConfig = field(default_factory=LLMConfig)
    
    @classmethod
    def from_env(cls) -> "AppConfig":
        """Carrega configurações do ambiente"""
        config = cls()
        
        # 1. SCADA Config
        config.scada.base_url = os.environ.get("SCADA_BASE_URL", "http://localhost:8080/Scada-LTS")
        config.scada.username = os.environ.get("SCADA_USER", "")
        config.scada.password = os.environ.get("SCADA_PASSWORD", "")
        
        # Valida credenciais críticas
        config.scada.validate()
        
        # 2. Points Config (Carregamento Dinâmico)
        # Procura por todas as variáveis que começam com POINT_
        env_points = {}
        
        # Pontos padrão conhecidos (fallback ou obrigatórios)
        known_points = {
            "cv": os.environ.get("POINT_CV", "DP_453792"),
            "freq1": os.environ.get("POINT_FREQ1", "DP_721172"),
            "pt1": os.environ.get("POINT_PT1", "DP_602726"),
            "pt2": os.environ.get("POINT_PT2", "DP_220578"),
            "ft1": os.environ.get("POINT_FT1", "DP_805576"),
        }
        
        # Adiciona pontos extras do env (POINT_BOMBA2=DP_999)
        for key, value in os.environ.items():
            if key.startswith("POINT_") and key not in ["POINT_CV", "POINT_FREQ1", "POINT_PT1", "POINT_PT2", "POINT_FT1"]:
                # Converte POINT_NOME_EXTRA -> nome_extra
                name = key[6:].lower()
                known_points[name] = value
                
        config.points.points = known_points
        
        return config


# Instância global
config = AppConfig.from_env()