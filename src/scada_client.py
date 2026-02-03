"""
Cliente de comunicação com SCADA-LTS via API REST
"""
import requests
import logging
from typing import Optional, Dict, Any
from dataclasses import dataclass
from datetime import datetime

from .config import ScadaConfig, PointsConfig

logger = logging.getLogger(__name__)


@dataclass
class PointValue:
    """Representa um valor lido de um ponto SCADA"""
    xid: str
    value: float
    timestamp: datetime
    raw_response: Dict[str, Any] = None
    
    def __repr__(self):
        return f"PointValue({self.xid}={self.value:.3f} @ {self.timestamp.strftime('%H:%M:%S')})"


class ScadaClient:
    """
    Cliente para comunicação com SCADA-LTS via API REST.
    
    Uso:
        client = ScadaClient(config)
        if client.connect():
            value = client.read_point("DP_155700")
            client.write_point("DP_693642", 45.0)
    """
    
    def __init__(self, scada_config: ScadaConfig, points_config: PointsConfig = None):
        self.config = scada_config
        self.points = points_config or PointsConfig()
        self.session: Optional[requests.Session] = None
        self.connected = False
        self._last_error: Optional[str] = None
    
    @property
    def last_error(self) -> Optional[str]:
        return self._last_error
    
    def connect(self) -> bool:
        """
        Estabelece conexão com o SCADA-LTS.
        Retorna True se conectado com sucesso.
        """
        try:
            self.session = requests.Session()
            response = self.session.get(
                self.config.login_url,
                timeout=self.config.timeout
            )
            
            if response.status_code == 200:
                self.connected = True
                self._last_error = None
                logger.info(f"Conectado ao SCADA-LTS em {self.config.base_url}")
                return True
            else:
                self._last_error = f"Login falhou com status {response.status_code}"
                logger.error(self._last_error)
                return False
                
        except requests.exceptions.ConnectionError:
            self._last_error = f"Não foi possível conectar a {self.config.base_url}"
            logger.error(self._last_error)
            return False
        except requests.exceptions.Timeout:
            self._last_error = "Timeout ao conectar"
            logger.error(self._last_error)
            return False
        except Exception as e:
            self._last_error = f"Erro inesperado: {str(e)}"
            logger.error(self._last_error)
            return False
    
    def disconnect(self):
        """Encerra a sessão"""
        if self.session:
            self.session.close()
        self.session = None
        self.connected = False
        logger.info("Desconectado do SCADA-LTS")
    
    def _ensure_connected(self) -> bool:
        """Garante que está conectado, tentando reconectar se necessário"""
        if not self.connected or not self.session:
            logger.warning("Não conectado. Tentando reconectar...")
            return self.connect()
        return True
    
    def read_point(self, xid_or_name: str) -> Optional[PointValue]:
        """
        Lê o valor de um ponto do SCADA.
        
        Args:
            xid_or_name: XID do ponto (ex: "DP_155700") ou nome amigável (ex: "pt1")
            
        Returns:
            PointValue com o valor lido, ou None se falhar
        """
        if not self._ensure_connected():
            return None
        
        # Resolve nome amigável para XID se necessário
        xid = self.points.get_xid(xid_or_name)
        url = self.config.get_read_url(xid)
        
        try:
            response = self.session.get(url, timeout=self.config.timeout)
            
            if response.status_code == 200:
                data = response.json()
                # Garante que None seja tratado como 0
                raw_value = data.get("value")
                value = float(raw_value) if raw_value is not None else 0.0
                
                return PointValue(
                    xid=xid,
                    value=value,
                    timestamp=datetime.now(),
                    raw_response=data
                )
            else:
                self._last_error = f"Erro ao ler {xid}: status {response.status_code}"
                logger.warning(self._last_error)
                return None
                
        except ValueError as e:
            # Captura o início da resposta para debug (provavelmente HTML de erro)
            preview = response.text[:200].replace('\n', ' ')
            self._last_error = f"Erro ao converter valor de {xid}: {e}. Resposta bruta: {preview}..."
            logger.warning(self._last_error)
            return None
        except requests.exceptions.RequestException as e:
            self._last_error = f"Erro de requisição ao ler {xid}: {e}"
            logger.warning(self._last_error)
            self.connected = False  # Marca como desconectado para tentar reconectar
            return None
    
    def write_point(self, xid_or_name: str, value: float, data_type: int = 3) -> bool:
        """
        Escreve um valor em um ponto do SCADA.
        
        Args:
            xid_or_name: XID do ponto ou nome amigável
            value: Valor a ser escrito
            data_type: Tipo de dado (padrão: 3 = numérico)
            
        Returns:
            True se escrito com sucesso
        """
        if not self._ensure_connected():
            return False
        
        xid = self.points.get_xid(xid_or_name)
        url = self.config.get_write_url(xid, data_type, value)
        
        try:
            response = self.session.post(url, timeout=self.config.timeout)
            
            if response.status_code == 200:
                logger.info(f"Escrito {xid} = {value}")
                return True
            else:
                self._last_error = f"Erro ao escrever {xid}: status {response.status_code}"
                logger.warning(self._last_error)
                return False
                
        except requests.exceptions.RequestException as e:
            self._last_error = f"Erro de requisição ao escrever {xid}: {e}"
            logger.warning(self._last_error)
            self.connected = False
            return False
    
    def read_multiple(self, xids_or_names: list) -> Dict[str, Optional[PointValue]]:
        """
        Lê múltiplos pontos de uma vez.
        
        Args:
            xids_or_names: Lista de XIDs ou nomes amigáveis
            
        Returns:
            Dicionário {nome: PointValue ou None}
        """
        results = {}
        for name in xids_or_names:
            results[name] = self.read_point(name)
        return results
    
    def read_all_configured(self) -> Dict[str, Optional[PointValue]]:
        """Lê todos os pontos configurados"""
        return self.read_multiple(list(self.points.points.keys()))
    
    def test_connection(self) -> Dict[str, Any]:
        """
        Testa a conexão e retorna diagnóstico.
        
        Returns:
            Dicionário com status de cada componente
        """
        result = {
            "url": self.config.base_url,
            "connected": False,
            "login_ok": False,
            "points_readable": {},
            "errors": []
        }
        
        # Testa conexão
        if self.connect():
            result["connected"] = True
            result["login_ok"] = True
            
            # Testa leitura de cada ponto
            for name, xid in self.points.points.items():
                point = self.read_point(xid)
                if point:
                    result["points_readable"][name] = {
                        "xid": xid,
                        "value": point.value,
                        "ok": True
                    }
                else:
                    result["points_readable"][name] = {
                        "xid": xid,
                        "ok": False,
                        "error": self._last_error
                    }
                    result["errors"].append(f"{name}: {self._last_error}")
        else:
            result["errors"].append(self._last_error)
        
        return result


# Função auxiliar para uso rápido
def create_client(
    base_url: str = "",
    username: str = "",
    password: str = ""
) -> ScadaClient:
    """Cria um cliente SCADA com configurações básicas"""
    config = ScadaConfig(base_url=base_url, username=username, password=password)
    return ScadaClient(config)
