"""
Configurações centralizadas do projeto SCADA Agent
"""
import os
from dataclasses import dataclass, field
from typing import Dict

@dataclass
class ScadaConfig:
    """Configurações de conexão com SCADA-LTS"""
    base_url: str = "http://localhost:8080/Scada-LTS"
    username: str = "Lenhs"
    password: str = "123456"
    timeout: int = 5
    
    @property
    def login_url(self) -> str:
        return f"{self.base_url}/api/auth/{self.username}/{self.password}"
    
    def get_read_url(self, xid: str) -> str:
        return f"{self.base_url}/api/point_value/getValue/{xid}"
    
    def get_write_url(self, xid: str, data_type: int, value: float) -> str:
        return f"{self.base_url}/api/point_value/setValue/{xid}/{data_type}/{value}"


@dataclass
class PointsConfig:
    """Configuração dos pontos de dados (XIDs)"""
    # Mapeamento: nome amigável -> XID
    points: Dict[str, str] = field(default_factory=lambda: {
        "cv": "DP_851894",           # Válvula de controle
        "freq1": "DP_693642",        # Frequência inversor 1
        "freq2": "DP_XXXXXX",        # Frequência inversor 2 (AJUSTAR!)
        "pt1": "DP_155700",          # Pressão transmissor 1
        "pt2": "DP_719779",          # Pressão transmissor 2
        "ft1": "DP_041666",          # Vazão
    })
    
    # Tipos de dados para escrita
    data_types: Dict[str, int] = field(default_factory=lambda: {
        "binary": 1,
        "multistate": 2,
        "numeric": 3,
        "alphanumeric": 4,
    })
    
    def get_xid(self, name: str) -> str:
        """Retorna XID pelo nome amigável"""
        return self.points.get(name, name)  # Retorna o próprio nome se não encontrar


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
    model: str = "claude-sonnet-4-20250514"
    max_tokens: int = 1024
    
    # Prompt do sistema para o agente
    system_prompt: str = """Você é um assistente especializado em sistemas SCADA e automação industrial.
Você está conectado a um sistema SCADA-LTS que monitora uma planta com:
- Bomba com inversor de frequência (controlável)
- Válvula de controle (CV)
- Sensores de pressão (PT1, PT2)
- Medidor de vazão (FT1)

Suas responsabilidades:
1. Analisar dados dos sensores em tempo real
2. Identificar anomalias ou tendências preocupantes
3. Sugerir ajustes operacionais quando apropriado
4. Explicar o comportamento do sistema de forma clara
5. Alertar sobre possíveis problemas

Ao receber dados, analise-os considerando:
- Relações entre pressão e vazão
- Comportamento esperado vs observado
- Tendências ao longo do tempo
- Limites operacionais seguros

Seja conciso mas informativo. Use unidades SI quando aplicável."""

    def __post_init__(self):
        # Tenta carregar API key do ambiente se não fornecida
        if not self.api_key:
            self.api_key = os.environ.get("ANTHROPIC_API_KEY", "")


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
        
        # Override com variáveis de ambiente se existirem
        if url := os.environ.get("SCADA_BASE_URL"):
            config.scada.base_url = url
        if user := os.environ.get("SCADA_USER"):
            config.scada.username = user
        if pwd := os.environ.get("SCADA_PASSWORD"):
            config.scada.password = pwd
        if key := os.environ.get("ANTHROPIC_API_KEY"):
            config.llm.api_key = key
            
        return config


# Instância global de configuração (pode ser sobrescrita)
config = AppConfig.from_env()
