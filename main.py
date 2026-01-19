#!/usr/bin/env python3
"""
SCADA Agent - Ponto de entrada principal

Aplicação que integra SCADA-LTS com agente inteligente Claude.
"""
import sys
import os
import argparse
import logging
from datetime import datetime

# Adiciona src ao path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src import (
    AppConfig,
    ScadaClient,
    DataCollector,
    create_agent,
)

# Configuração de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('scada_agent.log')
    ]
)
logger = logging.getLogger(__name__)


def print_banner():
    """Imprime banner da aplicação"""
    banner = """
╔═══════════════════════════════════════════════════════════╗
║                    🤖 SCADA AGENT v0.1                    ║
║          Integração SCADA-LTS + Agente Inteligente        ║
╚═══════════════════════════════════════════════════════════╝
    """
    print(banner)


def print_help():
    """Imprime comandos disponíveis"""
    help_text = """
📋 Comandos disponíveis:
  status      - Mostra leituras atuais dos sensores
  historico   - Exibe últimas leituras do buffer
  stats       - Mostra estatísticas dos dados
  analise     - Solicita análise do agente
  diagnostico - Solicita diagnóstico de problema
  exportar    - Salva dados em Excel
  limpar      - Limpa histórico de conversação
  ajuda       - Mostra esta mensagem
  sair        - Encerra a aplicação

💬 Ou digite qualquer pergunta em linguagem natural!
"""
    print(help_text)


def test_connection(config: AppConfig) -> bool:
    """Testa conexão com SCADA"""
    print("\n🔍 Testando conexão com SCADA-LTS...")
    
    client = ScadaClient(config.scada, config.points)
    result = client.test_connection()
    
    if result["connected"]:
        print(f"✅ Conectado a {result['url']}")
        print("\n📊 Status dos pontos:")
        for name, info in result["points_readable"].items():
            if info["ok"]:
                print(f"  ✅ {name} ({info['xid']}): {info['value']:.3f}")
            else:
                print(f"  ❌ {name} ({info['xid']}): {info.get('error', 'Erro')}")
        return True
    else:
        print(f"❌ Falha na conexão: {result['errors']}")
        return False


def run_collect_only(config: AppConfig, duration: int = 60):
    """Executa apenas coleta de dados (sem agente)"""
    print(f"\n📡 Modo coleta: coletando dados por {duration} segundos...")
    
    client = ScadaClient(config.scada, config.points)
    if not client.connect():
        print(f"❌ Erro: {client.last_error}")
        return
    
    collector = DataCollector(client, config.collector)
    
    # Callback para mostrar dados
    def on_data(snapshot):
        vals = ", ".join(f"{k}={v:.2f}" for k, v in snapshot.values.items())
        print(f"[{snapshot.timestamp.strftime('%H:%M:%S')}] {vals}")
    
    collector.on_data(on_data)
    collector.start()
    
    try:
        import time
        time.sleep(duration)
    except KeyboardInterrupt:
        print("\n⚠️ Interrompido pelo usuário")
    finally:
        collector.stop()
        
        # Exporta dados
        if collector.buffer_size > 0:
            filename = f"coleta_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
            collector.export_to_excel(filename)
            print(f"💾 Dados salvos em {filename}")
        
        client.disconnect()


def run_interactive(config: AppConfig):
    """Executa modo interativo com agente"""
    print_banner()
    
    # Conecta ao SCADA
    print("🔌 Conectando ao SCADA-LTS...")
    client = ScadaClient(config.scada, config.points)
    
    if not client.connect():
        print(f"⚠️ Não foi possível conectar ao SCADA: {client.last_error}")
        print("   Continuando em modo offline (sem dados em tempo real)")
        collector = None
    else:
        print("✅ Conectado!")
        collector = DataCollector(client, config.collector)
        collector.start()
        print(f"📡 Coletor iniciado ({config.collector.sample_rate_hz}Hz)")
    
    # Cria agente
    api_key = config.llm.api_key
    use_mock = not api_key
    
    if use_mock:
        print("\n⚠️ API key não configurada. Usando modo MOCK (respostas simuladas)")
        print("   Configure ANTHROPIC_API_KEY para usar Claude real.\n")
    else:
        print("✅ Agente Claude configurado\n")
    
    agent = create_agent(api_key=api_key, collector=collector, use_mock=use_mock)
    
    print_help()
    
    # Loop principal
    try:
        while True:
            try:
                user_input = input("\n🧑 Você: ").strip()
            except EOFError:
                break
            
            if not user_input:
                continue
            
            command = user_input.lower()
            
            # Comandos especiais
            if command in ["sair", "exit", "quit", "q"]:
                print("👋 Encerrando...")
                break
            
            elif command in ["ajuda", "help", "?"]:
                print_help()
            
            elif command == "status":
                if collector:
                    print(collector.format_current_readings())
                else:
                    print("⚠️ Coletor não disponível")
            
            elif command == "historico":
                if collector:
                    history = collector.get_history(last_n=10)
                    if history:
                        print("\n📜 Últimas 10 leituras:")
                        for s in history:
                            vals = ", ".join(f"{k}={v:.2f}" for k, v in s.values.items())
                            print(f"  [{s.timestamp.strftime('%H:%M:%S')}] {vals}")
                    else:
                        print("⚠️ Buffer vazio")
                else:
                    print("⚠️ Coletor não disponível")
            
            elif command == "stats":
                if collector:
                    stats = collector.get_statistics()
                    print("\n📈 Estatísticas:")
                    for name, s in stats.items():
                        print(f"  {name}: média={s['mean']:.2f}, min={s['min']:.2f}, max={s['max']:.2f}")
                else:
                    print("⚠️ Coletor não disponível")
            
            elif command == "analise":
                print("\n🤖 Agente: Analisando...")
                response = agent.analyze_current_state()
                print(f"\n🤖 Agente: {response}")
            
            elif command.startswith("diagnostico"):
                sintoma = user_input[11:].strip() if len(user_input) > 11 else ""
                if not sintoma:
                    sintoma = input("   Descreva o sintoma/problema: ").strip()
                print("\n🤖 Agente: Analisando problema...")
                response = agent.diagnose_issue(sintoma)
                print(f"\n🤖 Agente: {response}")
            
            elif command == "exportar":
                if collector and collector.buffer_size > 0:
                    filename = f"scada_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
                    collector.export_to_excel(filename)
                    print(f"💾 Dados exportados para {filename}")
                else:
                    print("⚠️ Sem dados para exportar")
            
            elif command == "limpar":
                agent.clear_history()
                print("🧹 Histórico de conversação limpo")
            
            else:
                # Trata como pergunta para o agente
                print("\n🤖 Agente: Pensando...")
                response = agent.ask(user_input)
                print(f"\n🤖 Agente: {response}")
    
    except KeyboardInterrupt:
        print("\n\n⚠️ Interrompido pelo usuário")
    
    finally:
        # Cleanup
        if collector:
            collector.stop()
        if client.connected:
            client.disconnect()
        print("✅ Encerrado com sucesso")


def main():
    """Função principal"""
    parser = argparse.ArgumentParser(
        description="SCADA Agent - Integração SCADA-LTS com Agente Inteligente"
    )
    parser.add_argument(
        "--test-connection", "-t",
        action="store_true",
        help="Testa conexão com SCADA e sai"
    )
    parser.add_argument(
        "--collect-only", "-c",
        action="store_true",
        help="Apenas coleta dados (sem agente interativo)"
    )
    parser.add_argument(
        "--duration", "-d",
        type=int,
        default=60,
        help="Duração da coleta em segundos (para --collect-only)"
    )
    parser.add_argument(
        "--scada-url",
        type=str,
        default=None,
        help="URL do SCADA-LTS (ex: http://localhost:8080/Scada-LTS)"
    )
    parser.add_argument(
        "--api-key",
        type=str,
        default=None,
        help="Chave da API Anthropic (ou use ANTHROPIC_API_KEY)"
    )
    
    args = parser.parse_args()
    
    # Carrega configuração
    config = AppConfig.from_env()
    
    # Override com argumentos de linha de comando
    if args.scada_url:
        config.scada.base_url = args.scada_url
    if args.api_key:
        config.llm.api_key = args.api_key
    
    # Executa modo apropriado
    if args.test_connection:
        success = test_connection(config)
        sys.exit(0 if success else 1)
    
    elif args.collect_only:
        run_collect_only(config, args.duration)
    
    else:
        run_interactive(config)


if __name__ == "__main__":
    main()
