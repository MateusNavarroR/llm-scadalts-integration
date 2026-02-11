"""
Configurações centralizadas do projeto SCADA Agent
"""
import os
import sys
from dataclasses import dataclass, field
from typing import Dict, List, Optional
from dotenv import load_dotenv

# Garante que o .env seja carregado antes de qualquer classe ser instanciada
load_dotenv(override=True)

@dataclass
class ScadaConfig:
    """Configurações de conexão com SCADA-LTS"""
    base_url: str = ""
    dashboard_url: str = ""  # URL para acesso via navegador (iframe)
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
class PointDetail:
    """Configuração detalhada de um ponto"""
    name: str          # Nome interno (ex: pt1)
    xid: str           # ID no SCADA (ex: DP_123)
    friendly_name: str # Nome para exibição (ex: Pressão Caldeira)
    unit: str = ""     # Unidade (bar, °C, etc)
    min_val: float = 0.0
    max_val: float = 100.0
    safe_min: float = None # Para validação de segurança
    safe_max: float = None
    
    def to_dict(self):
        return {
            "name": self.name,
            "xid": self.xid,
            "friendly_name": self.friendly_name,
            "unit": self.unit,
            "min_val": self.min_val,
            "max_val": self.max_val,
            "safe_min": self.safe_min,
            "safe_max": self.safe_max
        }
    
    @classmethod
    def from_dict(cls, data: dict):
        return cls(**data)


@dataclass
class PointsConfig:
    """Configuração dos pontos de dados (XIDs)"""
    # Lista de objetos PointDetail
    points_list: List[PointDetail] = field(default_factory=list)
    
    # Mantém compatibilidade com código antigo que espera dict {name: xid}
    @property
    def points(self) -> Dict[str, str]:
        return {p.name: p.xid for p in self.points_list}
    
    def get_point(self, name: str) -> Optional[PointDetail]:
        for p in self.points_list:
            if p.name == name:
                return p
        return None
    
    def get_xid(self, name: str) -> str:
        """Retorna XID pelo nome amigável"""
        p = self.get_point(name)
        return p.xid if p else name
    
    # Tipos de dados para escrita
    data_types: Dict[str, int] = field(default_factory=lambda: {
        "binary": 1,
        "multistate": 2,
        "numeric": 3,
        "alphanumeric": 4,
    })


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
class SafetyConfig:
    """Configurações de segurança para escrita"""
    # Limites operacionais: {tag_name: (min_val, max_val)}
    safe_ranges: Dict[str, tuple] = field(default_factory=dict)
    
    # Tags que nunca podem ser escritas pela IA
    blacklist: List[str] = field(default_factory=list)

    def is_safe(self, tag: str, value: float) -> tuple[bool, str]:
        """Verifica se a escrita é segura"""
        if tag in self.blacklist:
            return False, f"Tag '{tag}' está na blacklist e não pode ser alterada."
            
        if tag in self.safe_ranges:
            min_val, max_val = self.safe_ranges[tag]
            if not (min_val <= value <= max_val):
                return False, f"Valor {value} para '{tag}' fora dos limites seguros ({min_val}-{max_val})."
                
        return True, "OK"


@dataclass
class LLMConfig:
    """Configurações do agente LLM"""
    api_key: str = ""
    provider: str = ""  # "anthropic" ou "gemini"
    model: str = ""     # Definido automaticamente ou via env
    max_tokens: int = 4096
    
    # Prompt do sistema para o agente (Mentor Técnico com Markdown)
    system_prompt: str = """Você é um Mentor de Automação Industrial. Sua missão é explicar a física do processo SCADA de forma didática e técnica.

DIRETRIZES:
- Use Markdown para melhorar a legibilidade (negrito para termos técnicos, listas para passos).
- Mantenha respostas de tamanho médio (um parágrafo de análise técnica + recomendações).
- Foque na relação física entre os componentes (ex: como a Bomba afeta a Pressão e Vazão).

ESTRUTURA DA RESPOSTA:

### STATUS: [NORMAL/ALERTA/CRITICO]

**ANÁLISE DO PROCESSO**
Explique o comportamento físico observado. Mostre como as ações nos atuadores (Bomba/Válvula) estão impactando os sensores. Seja específico sobre correlações hidráulicas.

**RECOMENDAÇÃO**
Sugira o próximo passo operacional ou uma lição técnica para o aluno."""

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
    safety: SafetyConfig = field(default_factory=SafetyConfig)
    
    @classmethod
    def from_env(cls) -> "AppConfig":
        """Carrega configurações do ambiente"""
        config = cls()
        
        # 1. SCADA Config
        config.scada.base_url = os.environ.get("SCADA_BASE_URL", "http://localhost:8080/Scada-LTS")
        # Define URL do dashboard (pode ser diferente da API interna se estiver em container)
        config.scada.dashboard_url = os.environ.get("SCADA_DASHBOARD_URL", config.scada.base_url)
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
                
        # Converte o dicionário simples known_points em lista de PointDetail
        for name, xid in known_points.items():
            # Tenta inferir unidade básica para preencher o objeto inicial
            unit = ""
            if "temp" in name or "t_" in name: unit = "°C"
            elif "press" in name or "pt" in name: unit = "bar"
            elif "vaz" in name or "ft" in name: unit = "m³/h"
            elif "freq" in name or "hz" in name: unit = "Hz"
            elif "cv" in name or "perc" in name: unit = "%"
            
            config.points.points_list.append(PointDetail(
                name=name,
                xid=xid,
                friendly_name=name.title(), # Usa o próprio nome como friendly inicial
                unit=unit
            ))

        # 3. Safety Config (Travas de Segurança)
        # Por enquanto hardcoded, mas poderia vir de arquivo/env
        config.safety.safe_ranges = {
            "freq1": (0.0, 60.0), # Inversor 0-60Hz
            "cv": (0.0, 100.0),   # Válvula 0-100%
        }
        config.safety.blacklist = ["reset_critico", "master_stop"]
        
        return config


# Instância global
config = AppConfig.from_env()