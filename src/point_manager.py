import json
import logging
from pathlib import Path
from typing import List, Optional
from .config import PointDetail, PointsConfig, config as app_config

logger = logging.getLogger(__name__)

class PointManager:
    """
    Gerencia a persistência dos pontos de dados (sensores/atuadores).
    
    Responsabilidades:
    - Carregar/Salvar em arquivo JSON (points.json).
    - Migrar configurações legadas do .env se o JSON não existir.
    - Fornecer API para adicionar/editar/remover pontos.
    """
    
    def __init__(self, storage_file: str = "points.json"):
        self.storage_path = Path(storage_file)
        self.points: List[PointDetail] = []
        self._load()
        
    def _load(self):
        """Carrega pontos do disco ou migra do env"""
        if self.storage_path.exists():
            try:
                with open(self.storage_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.points = [PointDetail.from_dict(item) for item in data.get("points", [])]
                logger.info(f"Carregados {len(self.points)} pontos de {self.storage_path}")
            except Exception as e:
                logger.error(f"Erro ao ler {self.storage_path}: {e}. Usando configuração do .env.")
                self._migrate_from_env()
        else:
            logger.info("points.json não encontrado. Migrando do .env...")
            self._migrate_from_env()
            self.save() # Cria o arquivo pela primeira vez
            
    def _migrate_from_env(self):
        """Cria lista de pontos baseada no .env atual (legado)"""
        # Acessa o dicionário simples {nome: xid} do config global carregado pelo env
        env_points = app_config.points.points
        
        self.points = []
        for name, xid in env_points.items():
            # Tenta inferir unidade e friendly_name básico
            unit = ""
            friendly = name.title()
            
            # Heurística simples de unidade (similar ao frontend)
            n_lower = name.lower()
            if "temp" in n_lower or "t_" in n_lower: unit = "°C"
            elif "press" in n_lower or "pt" in n_lower: unit = "bar"
            elif "vaz" in n_lower or "ft" in n_lower: unit = "m³/h"
            elif "freq" in n_lower or "hz" in n_lower: unit = "Hz"
            elif "cv" in n_lower or "perc" in n_lower: unit = "%"
            
            self.points.append(PointDetail(
                name=name,
                xid=xid,
                friendly_name=friendly,
                unit=unit
            ))
            
    def save(self):
        """Salva estado atual no disco"""
        data = {
            "version": 1,
            "points": [p.to_dict() for p in self.points]
        }
        try:
            with open(self.storage_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            logger.info("Configuração de pontos salva com sucesso.")
        except Exception as e:
            logger.error(f"Erro ao salvar points.json: {e}")

    def get_all(self) -> List[PointDetail]:
        return self.points
    
    def get_by_name(self, name: str) -> Optional[PointDetail]:
        for p in self.points:
            if p.name == name:
                return p
        return None

    def add_point(self, point: PointDetail) -> bool:
        """Adiciona um novo ponto. Retorna False se nome já existir."""
        if self.get_by_name(point.name):
            return False
        self.points.append(point)
        self.save()
        return True

    def update_point(self, name: str, updates: dict) -> bool:
        """Atualiza um ponto existente"""
        point = self.get_by_name(name)
        if not point:
            return False
        
        # Atualiza campos
        if "friendly_name" in updates: point.friendly_name = updates["friendly_name"]
        if "unit" in updates: point.unit = updates["unit"]
        if "xid" in updates: point.xid = updates["xid"]
        if "min_val" in updates: point.min_val = float(updates["min_val"])
        if "max_val" in updates: point.max_val = float(updates["max_val"])
        
        self.save()
        return True

    def delete_point(self, name: str) -> bool:
        """Remove um ponto"""
        initial_len = len(self.points)
        self.points = [p for p in self.points if p.name != name]
        if len(self.points) < initial_len:
            self.save()
            return True
        return False

    def reorder_points(self, new_order: List[str]) -> bool:
        """
        Reordena a lista de pontos com base em uma lista de nomes.
        Pontos não listados são mantidos no final.
        """
        if not new_order:
            return False
            
        # Cria um mapa para acesso rápido
        point_map = {p.name: p for p in self.points}
        new_list = []
        
        # Adiciona na ordem solicitada
        for name in new_order:
            if name in point_map:
                new_list.append(point_map.pop(name))
        
        # Adiciona o que sobrou (para não perder dados)
        for remaining_point in point_map.values():
            new_list.append(remaining_point)
            
        self.points = new_list
        self.save()
        return True
