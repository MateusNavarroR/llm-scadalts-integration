#!/usr/bin/env python3
"""
Demonstração do SCADA Agent sem conexão real com SCADA.

Este script demonstra como usar os componentes do sistema
usando dados simulados, útil para testar a integração com Claude
antes de conectar ao SCADA real.
"""
import sys
import os
import time
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.config import AppConfig, LLMConfig
from src.llm_agent import LLMAgent, MockLLMAgent


def demo_mock_agent():
    """Demonstra uso do agente mock (sem API)"""
    print("=" * 50)
    print("🎭 DEMO: Agente Mock (sem API key)")
    print("=" * 50)
    
    agent = MockLLMAgent()
    
    perguntas = [
        "Qual o status atual do sistema?",
        "Está tendo algum problema com a pressão?",
        "A vazão está estável?",
    ]
    
    for pergunta in perguntas:
        print(f"\n👤 Pergunta: {pergunta}")
        resposta = agent.ask(pergunta)
        print(f"🤖 Resposta: {resposta}")
        time.sleep(0.5)


def demo_real_agent():
    """Demonstra uso do agente real (com API key)"""
    print("\n" + "=" * 50)
    print("🤖 DEMO: Agente Claude Real")
    print("=" * 50)
    
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    
    if not api_key:
        print("⚠️ ANTHROPIC_API_KEY não configurada.")
        print("   Configure a variável de ambiente para testar com Claude real.")
        print("   export ANTHROPIC_API_KEY='sua_chave_aqui'")
        return
    
    config = LLMConfig(api_key=api_key)
    agent = LLMAgent(config, collector=None)
    
    # Sistema prompt customizado para demo
    config.system_prompt = """Você é um assistente de demonstração.
Responda de forma breve e amigável. Este é apenas um teste de integração."""
    
    print("\n✅ Agente configurado com Claude!")
    
    pergunta = "Olá! Pode confirmar que está funcionando? Responda em uma linha."
    print(f"\n👤 Pergunta: {pergunta}")
    
    try:
        resposta = agent.ask(pergunta, include_context=False)
        print(f"🤖 Resposta: {resposta}")
        print("\n✅ Integração com Claude funcionando!")
    except Exception as e:
        print(f"❌ Erro: {e}")


def demo_data_formatting():
    """Demonstra formatação de dados para o agente"""
    print("\n" + "=" * 50)
    print("📊 DEMO: Formatação de Dados SCADA")
    print("=" * 50)
    
    # Simula dados que viriam do coletor
    dados_simulados = {
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "valores": {
            "pt1": 2.45,
            "pt2": 1.82,
            "ft1": 12.5,
            "freq1": 45.0,
            "cv": 30.0,
        },
        "estatisticas": {
            "pt1": {"media": 2.43, "min": 2.38, "max": 2.51},
            "ft1": {"media": 12.3, "min": 11.8, "max": 13.1},
        }
    }
    
    # Formata como contexto para o agente
    contexto = f"""=== LEITURA ATUAL ===
Timestamp: {dados_simulados['timestamp']}
"""
    for nome, valor in dados_simulados['valores'].items():
        contexto += f"  {nome}: {valor:.3f}\n"
    
    contexto += "\n=== ESTATÍSTICAS ===\n"
    for nome, stats in dados_simulados['estatisticas'].items():
        contexto += f"  {nome}: média={stats['media']:.2f}, min={stats['min']:.2f}, max={stats['max']:.2f}\n"
    
    print("Contexto formatado para enviar ao agente:")
    print("-" * 40)
    print(contexto)
    print("-" * 40)
    
    print("\n💡 Este contexto seria anexado à pergunta do usuário")
    print("   antes de enviar para o Claude analisar.")


def main():
    print("""
╔═══════════════════════════════════════════════════════════╗
║           🧪 SCADA Agent - Script de Demonstração         ║
╚═══════════════════════════════════════════════════════════╝
    """)
    
    # Demo 1: Agente Mock
    demo_mock_agent()
    
    # Demo 2: Formatação de dados
    demo_data_formatting()
    
    # Demo 3: Agente Real (se API key disponível)
    demo_real_agent()
    
    print("\n" + "=" * 50)
    print("✅ Demonstração concluída!")
    print("=" * 50)
    print("""
Próximos passos:
1. Configure ANTHROPIC_API_KEY para usar Claude real
2. Ajuste os XIDs em src/config.py para seu SCADA
3. Execute: python main.py --test-connection
4. Execute: python main.py (modo interativo)
    """)


if __name__ == "__main__":
    main()
