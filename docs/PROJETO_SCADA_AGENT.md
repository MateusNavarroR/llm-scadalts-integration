# 🤖 SCADA-LTS Agent - Documentação do Projeto

## Visão Geral

Este projeto integra um sistema SCADA-LTS com um agente inteligente baseado em LLM (Google Gemini ou Anthropic Claude), permitindo análise em tempo real de dados de sensores, diagnósticos automatizados e interação conversacional com o sistema via terminal.

---

## 📋 Índice

1. [Arquitetura do Sistema](#arquitetura-do-sistema)
2. [Estrutura do Projeto](#estrutura-do-projeto)
3. [Configuração](#configuração)
4. [Uso](#uso)
5. [Referências da API SCADA-LTS](#referências-da-api-scada-lts)

---

## 🏗️ Arquitetura do Sistema

```
┌─────────────────────────────────────────────────────────────────┐
│                        APLICAÇÃO PRINCIPAL                       │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐       │
│  │              │    │              │    │              │       │
│  │ ScadaClient  │───►│DataCollector │───►│  LLMAgent    │       │
│  │              │    │              │    │              │       │
│  └──────┬───────┘    └──────┬───────┘    └──────┬───────┘       │
│         │                   │                   │               │
│         ▼                   ▼                   ▼               │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐       │
│  │  SCADA-LTS   │    │   Buffer/    │    │   LLM API    │       │
│  │    API       │    │   Histórico  │    │(Gemini/Claude)│      │
│  └──────────────┘    └──────────────┘    └──────────────┘       │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### Fluxo de Dados

1. **Aquisição**: `ScadaClient` conecta ao SCADA-LTS via API REST.
2. **Coleta**: `DataCollector` armazena leituras em buffer temporal circular.
3. **Análise**: `LLMAgent` recebe dados formatados e responde consultas usando prompts de engenharia especializados.
4. **Interação**: Usuário interage via terminal com comandos ou linguagem natural.

---

## 📁 Estrutura do Projeto

```
scada_agent_project/
├── docs/
│   └── PROJETO_SCADA_AGENT.md    # Este documento
├── src/
│   ├── __init__.py
│   ├── scada_client.py           # Cliente de comunicação SCADA-LTS
│   ├── data_collector.py         # Coletor de dados com buffer
│   ├── llm_agent.py              # Agente inteligente (Gemini/Claude)
│   └── config.py                 # Configurações centralizadas e validação
├── pyproject.toml                # Dependências (gerenciado pelo uv)
├── main.py                       # Ponto de entrada da aplicação
├── debug_gemini.py               # Diagnóstico de modelos Gemini
├── test_read_write.py            # Teste manual de sensores
└── .env.example                  # Template de variáveis de ambiente
```

---

## ⚙️ Configuração

### Variáveis de Ambiente (`.env`)

A configuração é feita exclusivamente via variáveis de ambiente para segurança e flexibilidade.

```env
# SCADA-LTS
SCADA_BASE_URL=http://localhost:8080/Scada-LTS
SCADA_USER=admin
SCADA_PASSWORD=sua_senha_segura

# LLM (Escolha um)
GEMINI_API_KEY=AIzaSy...       # Para Google Gemini
# ANTHROPIC_API_KEY=sk-ant...  # Para Claude

# Pontos de Dados (Mapeamento XID)
POINT_CV=DP_123456
POINT_FREQ1=DP_789012
POINT_PT1=DP_345678
POINT_PT2=DP_901234
POINT_FT1=DP_567890
```

### Pontos de Dados (XIDs)

O sistema espera 5 pontos principais por padrão, mas você pode adicionar outros no `.env` prefixando com `POINT_`.

| Variável Config | Descrição |
|-----------------|-----------|
| `POINT_CV` | Posição da válvula de controle (%) |
| `POINT_FREQ1` | Frequência do inversor (Hz) |
| `POINT_PT1` | Pressão Montante |
| `POINT_PT2` | Pressão Jusante |
| `POINT_FT1` | Vazão (Fluxo) |

---

## 🚀 Uso

### Instalação (via uv)

```bash
# Instalar uv (se necessário)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Configurar ambiente
cp .env.example .env
# Edite o .env com seus dados!
```

### Execução

```bash
# Modo interativo (terminal)
uv run main.py

# Apenas coleta de dados (sem agente)
uv run main.py --collect-only

# Teste de conexão e leitura
uv run main.py --test-connection
```

### Comandos do Agente

Durante a execução interativa:

| Comando | Descrição |
|---------|-----------|
| `status` | Mostra leituras atuais dos sensores (bruto) |
| `historico` | Exibe últimas N leituras |
| `analise` | Solicita análise técnica detalhada do agente |
| `diagnostico <sintoma>` | Solicita diagnóstico específico |
| `exportar` | Salva dados em Excel |
| `sair` | Encerra a aplicação |

Ou faça perguntas em linguagem natural:
- "Qual a vazão atual?"
- "Analise a eficiência da bomba considerando a pressão atual."

---

## 📚 Referências da API SCADA-LTS

### Leitura de Ponto

```http
GET /Scada-LTS/api/point_value/getValue/{xid}
```

**Resposta:**
```json
{
  "value": "25.5",
  "ts": 1699876543000,
  "annotation": null
}
```

### Escrita de Ponto

```http
POST /Scada-LTS/api/point_value/setValue/{xid}/{dataType}/{value}
```

**Tipos de dados (dataType):**
| Código | Tipo |
|--------|------|
| 1 | Binary |
| 2 | Multistate |
| 3 | Numeric |
| 4 | Alphanumeric |

---

## 🔧 Troubleshooting

### Erro 404 (Models not found)
Verifique se a versão da biblioteca `google-generativeai` está atualizada (`>=0.7.0`) e se sua chave tem acesso ao modelo configurado (`gemini-2.5-flash`). Use `uv run debug_gemini.py` para listar seus modelos disponíveis.

### Erro de Conexão SCADA
1. Verifique se o servidor está rodando.
2. Confirme URL e porta no `.env`.
3. Teste login manualmente no navegador.
4. Rode `uv run test_read_write.py` para isolar o problema.

---

*Última atualização: Fevereiro 2026*