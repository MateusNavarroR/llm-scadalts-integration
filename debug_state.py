import sys
import os
from pathlib import Path

# Adiciona diretório atual ao path para importar modulos
sys.path.append(os.getcwd())

from src.point_manager import PointManager
from src.config import PointsConfig

def debug():
    print("--- DEBUGGING POINT LOADING ---")
    
    # 1. Verifica arquivo
    p = Path("points.json")
    if p.exists():
        print(f"✅ points.json encontrado ({p.stat().st_size} bytes)")
        print(f"Conteúdo: {p.read_text()}")
    else:
        print("❌ points.json NÃO encontrado")
        return

    # 2. Testa PointManager
    try:
        pm = PointManager()
        points = pm.get_all()
        print(f"\n✅ PointManager carregou {len(points)} pontos:")
        for pt in points:
            print(f"   - {pt.name} (XID: {pt.xid})")
            
        # Verifica especificamente o PT3
        pt3 = pm.get_by_name("PT3")
        if pt3:
            print(f"\n✅ PT3 encontrado na memória do Manager!")
        else:
            print(f"\n❌ PT3 NÃO encontrado na memória (mas estava no arquivo?)")
            
    except Exception as e:
        print(f"\n❌ Erro ao instanciar PointManager: {e}")

if __name__ == "__main__":
    debug()
