"""
Coletor de dados do SCADA com buffer circular e threading
"""
import threading
import time
import logging
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional, Callable
import pandas as pd

from .scada_client import ScadaClient, PointValue
from .config import CollectorConfig

logger = logging.getLogger(__name__)


@dataclass
class DataSnapshot:
    """Snapshot de todos os pontos em um instante"""
    timestamp: datetime
    values: Dict[str, float]
    raw_points: Dict[str, PointValue] = field(default_factory=dict)
    
    def to_dict(self) -> Dict:
        """Converte para dicionário simples"""
        result = {"timestamp": self.timestamp}
        result.update(self.values)
        return result
    
    def __repr__(self):
        vals = ", ".join(f"{k}={v:.2f}" for k, v in self.values.items())
        return f"Snapshot({self.timestamp.strftime('%H:%M:%S')}: {vals})"


class DataCollector:
    """
    Coletor de dados do SCADA com buffer circular.
    
    Coleta dados periodicamente em background e mantém histórico
    configurável para análise.
    
    Uso:
        collector = DataCollector(client, config)
        collector.start()
        # ... trabalhar ...
        snapshot = collector.get_latest()
        history = collector.get_history(last_n=60)
        collector.stop()
    """
    
    def __init__(
        self,
        client: ScadaClient,
        config: CollectorConfig = None,
        points_to_collect: List[str] = None
    ):
        self.client = client
        self.config = config or CollectorConfig()
        
        # Pontos a coletar (nomes amigáveis ou XIDs)
        self.points_to_collect = points_to_collect or list(client.points.points.keys())
        
        # Buffer circular thread-safe
        self._buffer: deque = deque(maxlen=self.config.max_buffer_size)
        self._buffer_lock = threading.Lock()
        
        # Controle de threading
        self._running = False
        self._thread: Optional[threading.Thread] = None
        
        # Callbacks para eventos
        self._on_data_callbacks: List[Callable[[DataSnapshot], None]] = []
        self._on_error_callbacks: List[Callable[[str], None]] = []
        
        # Estatísticas
        self._samples_collected = 0
        self._errors_count = 0
        self._start_time: Optional[datetime] = None
    
    @property
    def is_running(self) -> bool:
        return self._running
    
    @property
    def buffer_size(self) -> int:
        with self._buffer_lock:
            return len(self._buffer)
    
    def on_data(self, callback: Callable[[DataSnapshot], None]):
        """Registra callback chamado a cada coleta"""
        self._on_data_callbacks.append(callback)
    
    def on_error(self, callback: Callable[[str], None]):
        """Registra callback chamado em erros"""
        self._on_error_callbacks.append(callback)
    
    def start(self):
        """Inicia coleta em background"""
        if self._running:
            logger.warning("Coletor já está rodando")
            return
        
        self._running = True
        self._start_time = datetime.now()
        self._thread = threading.Thread(target=self._collection_loop, daemon=True)
        self._thread.start()
        logger.info(f"Coletor iniciado. Taxa: {self.config.sample_rate_hz}Hz, Buffer: {self.config.buffer_size_seconds}s")
    
    def stop(self):
        """Para a coleta"""
        self._running = False
        if self._thread:
            self._thread.join(timeout=2.0)
            self._thread = None
        logger.info(f"Coletor parado. Total coletado: {self._samples_collected} amostras")
    
    def _collection_loop(self):
        """Loop principal de coleta (roda em thread separada)"""
        while self._running:
            try:
                snapshot = self._collect_once()
                if snapshot:
                    self._add_to_buffer(snapshot)
                    self._samples_collected += 1
                    
                    # Notifica callbacks
                    for callback in self._on_data_callbacks:
                        try:
                            callback(snapshot)
                        except Exception as e:
                            logger.error(f"Erro em callback: {e}")
                
                time.sleep(self.config.sample_interval)
                
            except Exception as e:
                self._errors_count += 1
                error_msg = f"Erro na coleta: {e}"
                logger.error(error_msg)
                
                for callback in self._on_error_callbacks:
                    try:
                        callback(error_msg)
                    except:
                        pass
                
                time.sleep(1.0)  # Espera um pouco antes de tentar novamente
    
    def _collect_once(self) -> Optional[DataSnapshot]:
        """Coleta uma amostra de todos os pontos"""
        readings = self.client.read_multiple(self.points_to_collect)
        
        values = {}
        raw_points = {}
        
        for name, point in readings.items():
            if point is not None:
                values[name] = point.value
                raw_points[name] = point
            else:
                values[name] = float('nan')  # Marca como NaN se falhou
        
        return DataSnapshot(
            timestamp=datetime.now(),
            values=values,
            raw_points=raw_points
        )
    
    def _add_to_buffer(self, snapshot: DataSnapshot):
        """Adiciona snapshot ao buffer (thread-safe)"""
        with self._buffer_lock:
            self._buffer.append(snapshot)
    
    def get_latest(self) -> Optional[DataSnapshot]:
        """Retorna a leitura mais recente"""
        with self._buffer_lock:
            if self._buffer:
                return self._buffer[-1]
        return None
    
    def get_history(self, last_n: int = None, last_seconds: float = None) -> List[DataSnapshot]:
        """
        Retorna histórico de leituras.
        
        Args:
            last_n: Número de amostras mais recentes
            last_seconds: Últimos N segundos de dados
            
        Returns:
            Lista de snapshots (mais antigo primeiro)
        """
        with self._buffer_lock:
            data = list(self._buffer)
        
        if not data:
            return []
        
        if last_seconds is not None:
            cutoff = datetime.now().timestamp() - last_seconds
            data = [s for s in data if s.timestamp.timestamp() >= cutoff]
        
        if last_n is not None:
            data = data[-last_n:]
        
        return data
    
    def get_dataframe(self, last_n: int = None, last_seconds: float = None) -> pd.DataFrame:
        """Retorna histórico como DataFrame pandas"""
        history = self.get_history(last_n=last_n, last_seconds=last_seconds)
        
        if not history:
            return pd.DataFrame()
        
        records = [s.to_dict() for s in history]
        df = pd.DataFrame(records)
        df.set_index('timestamp', inplace=True)
        return df
    
    def get_statistics(self, point_name: str = None) -> Dict:
        """
        Calcula estatísticas do buffer atual.
        
        Args:
            point_name: Nome do ponto específico, ou None para todos
            
        Returns:
            Dicionário com estatísticas
        """
        df = self.get_dataframe()
        
        if df.empty:
            return {"error": "Sem dados no buffer"}
        
        if point_name:
            if point_name not in df.columns:
                return {"error": f"Ponto {point_name} não encontrado"}
            series = df[point_name].dropna()
            return {
                "point": point_name,
                "count": len(series),
                "mean": series.mean(),
                "std": series.std(),
                "min": series.min(),
                "max": series.max(),
                "current": series.iloc[-1] if len(series) > 0 else None,
                "trend": self._calculate_trend(series)
            }
        else:
            # Estatísticas de todos os pontos
            stats = {}
            for col in df.columns:
                series = df[col].dropna()
                if len(series) > 0:
                    stats[col] = {
                        "mean": series.mean(),
                        "std": series.std(),
                        "min": series.min(),
                        "max": series.max(),
                        "current": series.iloc[-1]
                    }
            return stats
    
    def _calculate_trend(self, series: pd.Series) -> str:
        """Calcula tendência simples (subindo/descendo/estável)"""
        if len(series) < 5:
            return "insuficiente"
        
        recent = series.iloc[-5:].mean()
        older = series.iloc[-10:-5].mean() if len(series) >= 10 else series.iloc[:5].mean()
        
        diff_pct = (recent - older) / (older + 1e-10) * 100
        
        if diff_pct > 5:
            return "subindo"
        elif diff_pct < -5:
            return "descendo"
        else:
            return "estável"
    
    def export_to_excel(self, filename: str = "scada_data.xlsx") -> str:
        """Exporta dados do buffer para Excel"""
        df = self.get_dataframe()
        if df.empty:
            raise ValueError("Sem dados para exportar")
        
        df.to_excel(filename)
        logger.info(f"Dados exportados para {filename}")
        return filename
    
    def clear_buffer(self):
        """Limpa o buffer de dados"""
        with self._buffer_lock:
            self._buffer.clear()
        logger.info("Buffer limpo")
    
    def update_points_list(self, new_points: List[str]):
        """Atualiza a lista de pontos a serem coletados (Hot Reload)"""
        old_count = len(self.points_to_collect)
        self.points_to_collect = new_points
        # Opcional: Limpar buffer se a estrutura mudar drasticamente, 
        # mas manter dados antigos pode ser útil.
        logger.info(f"Coletor atualizado: {old_count} -> {len(new_points)} pontos")

    def get_status(self) -> Dict:
        """Retorna status do coletor"""
        return {
            "running": self._running,
            "samples_collected": self._samples_collected,
            "errors_count": self._errors_count,
            "buffer_size": self.buffer_size,
            "buffer_max": self.config.max_buffer_size,
            "sample_rate_hz": self.config.sample_rate_hz,
            "uptime_seconds": (datetime.now() - self._start_time).total_seconds() if self._start_time else 0,
            "points": self.points_to_collect
        }
    
    def format_current_readings(self) -> str:
        """Formata leituras atuais como string legível"""
        snapshot = self.get_latest()
        if not snapshot:
            return "Sem dados disponíveis"
        
        lines = [f"📊 Leituras em {snapshot.timestamp.strftime('%H:%M:%S')}:"]
        for name, value in snapshot.values.items():
            if pd.notna(value):
                lines.append(f"  • {name}: {value:.3f}")
            else:
                lines.append(f"  • {name}: ERRO")
        
        return "\n".join(lines)
