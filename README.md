# 🤖 SCADA-LTS Agent Integration

Este projeto integra um sistema SCADA-LTS com um agente inteligente (Claude ou Gemini), permitindo análise em tempo real de dados de sensores e interação conversacional.

## 🚀 Uso com uv (Recomendado)

Este projeto utiliza **[uv](https://github.com/astral-sh/uv)** para gerenciamento rápido e moderno de dependências.

### Instalação

1.  **Instale o uv** (se necessário):
    ```bash
    curl -LsSf https://astral.sh/uv/install.sh | sh
    ```

2.  **Configure o ambiente**:
    Copie o arquivo de exemplo e edite com suas credenciais. **É obrigatório configurar as variáveis para rodar o projeto.**
    ```bash
    cp .env.example .env
    nano .env  # ou use seu editor favorito
    ```
    
    No `.env`, você precisará definir:
    *   URL e credenciais do SCADA-LTS.
    *   Sua chave de API (`GEMINI_API_KEY` ou `ANTHROPIC_API_KEY`).
    *   Os XIDs dos pontos de dados (sensores) que deseja monitorar.

### Execução

O `uv` gerencia automaticamente o ambiente virtual. Basta rodar:

```bash
# Iniciar o agente interativo
uv run main.py

# Apenas coletar dados (sem IA)
uv run main.py --collect-only

# Testar conexão com SCADA
uv run main.py --test-connection
```

## 🧠 Modelos Suportados

O sistema detecta automaticamente qual provedor usar com base na chave presente no `.env`:

*   **Google Gemini**: `gemini-2.5-flash` (Padrão, rápido e eficiente).
*   **Anthropic Claude**: `claude-sonnet-4-20250514`.

## 🛠️ Ferramentas de Diagnóstico

*   `test_read_write.py`: Script para testar leitura e escrita em pontos específicos sem usar a IA.
*   `discover_points.py`: Tenta descobrir automaticamente os XIDs disponíveis no seu SCADA (depende da versão da API).
*   `debug_gemini.py`: Testa sua chave do Gemini e lista os modelos disponíveis para sua conta.

## 📖 Documentação Completa

Para detalhes profundos sobre arquitetura, configuração de pontos e endpoints, consulte a documentação em:
[docs/PROJETO_SCADA_AGENT.md](docs/PROJETO_SCADA_AGENT.md)