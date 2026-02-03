#!/usr/bin/env python3
"""
Script de teste para validação de Leitura e Escrita no SCADA-LTS.
Usa as configurações do .env e src/config.py
"""
import sys
import os
import time
from src.config import AppConfig
from src.scada_client import ScadaClient

def main():
    # Carrega configurações
    config = AppConfig.from_env()
    print(f"🔧 Configuração carregada.")
    print(f"Target SCADA: {config.scada.base_url}")
    
    client = ScadaClient(config.scada, config.points)
    
    print("\n1️⃣  Testando CONEXÃO...")
    if not client.connect():
        print(f"❌ Falha ao conectar: {client.last_error}")
        return
    print("✅ Conectado com sucesso.")

    print("\n2️⃣  Testando LEITURA (Todos os pontos)...")
    results = client.read_all_configured()
    pontos_validos = []
    
    for nome, ponto in results.items():
        if ponto:
            print(f"   🔹 {nome:<10} | Valor: {ponto.value:<10} | XID: {ponto.xid}")
            pontos_validos.append(nome)
        else:
            print(f"   🔸 {nome:<10} | Erro na leitura")

    if not pontos_validos:
        print("❌ Nenhum ponto válido encontrado para teste de escrita.")
        return

    print("\n3️⃣  Testando ESCRITA...")
    print("⚠️  AVISO: Isso irá alterar valores no SCADA/PLC.")
    
    target = input(f"Digite o nome do ponto para teste de escrita ({', '.join(pontos_validos)}): ").strip()
    
    if target not in pontos_validos:
        print("❌ Ponto inválido ou não lido corretamente.")
        return

    try:
        val_atual = results[target].value
        novo_valor = float(input(f"Valor atual de '{target}' é {val_atual}. Digite o novo valor: "))
        
        print(f"⏳ Escrevendo {novo_valor} em '{target}'...")
        if client.write_point(target, novo_valor):
            print("✅ Comando de escrita enviado.")
            
            print("⏳ Aguardando 2 segundos para atualização...")
            time.sleep(2)
            
            check_point = client.read_point(target)
            if check_point:
                print(f"🔍 Leitura de confirmação: {check_point.value}")
                if abs(check_point.value - novo_valor) < 0.1:
                    print("🎉 SUCESSO: Valor confirmado!")
                else:
                    print("⚠️  AVISO: Valor lido diferente do escrito (pode ser delay ou lógica do PLC reescrevendo).")
            else:
                print("❌ Falha ao reler o ponto.")
        else:
            print(f"❌ Falha na escrita: {client.last_error}")

    except ValueError:
        print("❌ Valor inválido.")

    client.disconnect()

if __name__ == "__main__":
    main()
