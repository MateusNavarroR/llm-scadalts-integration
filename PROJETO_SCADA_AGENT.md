# 🤖 SCADA-LTS Agent - Documentação do Projeto

## Visão Geral

Este projeto integra um sistema SCADA-LTS com um agente inteligente baseado em LLM (Claude/Gemini), permitindo análise em tempo real de dados de sensores, diagnósticos automatizados e interação conversacional com o sistema através de uma interface web moderna.

---

## 📋 Índice

1. [Arquitetura do Sistema](#arquitetura-do-sistema)
2. [Estrutura do Projeto](#estrutura-do-projeto)
3. [Componentes](#componentes)
4. [Configuração](#configuração)
5. [Uso](#uso)
6. [Roadmap](#roadmap)
7. [Referências da API SCADA-LTS](#referências-da-api-scada-lts)

---

## 🏗️ Arquitetura do Sistema

```
┌───────────────────────────┐      ┌──────────────────────────────┐
│      Frontend (React)     │      │      Backend (FastAPI)       │
│                           │      │                              │
│  ┌─────────┐  ┌────────┐  │      │  ┌──────────┐  ┌──────────┐  │
│  │ Dashboard│  │  Chat  │◄─ API ─┼─►│ LLMAgent │  │ API/WS   │  │
│  └─────────┘  └────────┘  │      │  └────┬─────┘  └────┬─────┘  │
│       ▲            ▲      │      │       │             │        │
│       │            │      │      │       ▼             ▼        │
│  ┌────┴────────────┴───┐  │      │  ┌──────────┐  ┌──────────┐  │
│  │    SCADA Iframe     │◄──Proxy─┼──┤DataCollec│  │ScadaClient│  │
│  └─────────────────────┘  │      │  └──────────┘  └────┬─────┘  │
└───────────────────────────┘      └─────────────────────┼────────┘
                                                         │
                                                         ▼
                                                ┌────────────────┐
                                                │   SCADA-LTS    │
                                                └────────────────┘
```

### Fluxo de Dados

1. **Monitoramento IA**: `ScadaClient` coleta dados -> `DataCollector` armazena -> `LLMAgent` analisa -> Frontend exibe via WebSocket.
2. **Controle IA**: Usuário solicita no Chat -> `LLMAgent` processa -> Solicita aprovação -> `ScadaClient` escreve no SCADA.
3. **Visualização SCADA**: Frontend carrega Iframe -> Backend Proxy reescreve headers/cookies -> SCADA-LTS (Bypass de restrições de segurança/CORS).

---

## 📁 Estrutura do Projeto

```
scada_agent_project/
├── docs/                 # Documentação
├── frontend/             # Interface React + Vite
│   ├── src/
│   │   ├── App.tsx       # Dashboard e Chat
│   │   └── ...
├── src/
│   ├── server.py         # Servidor FastAPI e Proxy SCADA
│   ├── scada_client.py   # Cliente API SCADA-LTS
│   ├── data_collector.py # Coletor e Buffer de dados
│   ├── llm_agent.py      # Agente Inteligente (Gemini/Claude)
│   └── config.py         # Configurações
├── main.py               # Launcher (CLI legado)
└── .env                  # Configurações de ambiente
```

---

## 🧩 Componentes

### 1. Backend Server (`server.py`)

Núcleo da aplicação que expõe a API REST, WebSocket e o Proxy Reverso.

**Funcionalidades:**
- **API REST**: Endpoints para chat, status e aprovação de ações.
- **WebSocket**: Streaming de dados em tempo real para o Dashboard.
- **Proxy Reverso Inteligente**:
    - Intercepta requisições para o SCADA-LTS.
    - Reescreve headers `Location` e `Referer` para manter navegação fluida.
    - Remove headers de segurança (`X-Frame-Options`, `Content-Security-Policy`) que impediriam o uso em Iframe.
    - Gerencia `Set-Cookie` múltiplos para manutenção de sessão.
    - Mascara origem de requisições WebSocket/XHR para evitar bloqueios CSRF/CORS (Erro 403).

### 2. Interface Web (Frontend)

Dashboard desenvolvido em React para operação unificada.

**Funcionalidades:**
- Visualização de KPIs e gráficos em tempo real.
- Chat integrado com o Agente IA.
- Iframe embutido para acesso direto às telas nativas do SCADA-LTS.
- Sistema de aprovação de ações críticas sugeridas pela IA.

### 3. ScadaClient & DataCollector

Camada de baixo nível para comunicação e persistência temporária de dados.

- **ScadaClient**: Abstrai a API REST do SCADA (Login, Read, Write).
- **DataCollector**: Mantém buffer circular dos últimos minutos para contexto da IA.

### 4. LLMAgent

Cérebro da operação.

- Suporta Google Gemini (com Tool Calling) e Anthropic Claude.
- Analisa tendências e diagnostica anomalias.
- Pode sugerir ações de controle (escrita de setpoints), sujeitas à aprovação humana.

---

## ⚙️ Configuração

### Variáveis de Ambiente (`.env`)

```env
# SCADA-LTS
SCADA_BASE_URL=http://localhost:8080/Scada-LTS
SCADA_DASHBOARD_URL=http://localhost:8000/Scada-LTS/  # URL via Proxy
SCADA_USER=admin
SCADA_PASSWORD=admin

# LLM Provider (Escolha um)
GEMINI_API_KEY=AIza...
# ANTHROPIC_API_KEY=sk-ant...

# Segurança
SAFE_MODE=true
```

---

## 🚀 Uso

### 1. Iniciar Backend (Python)

```bash
# Na raiz do projeto
source .venv/bin/activate
uvicorn src.server:app --reload --host 0.0.0.0 --port 8000
```

### 2. Iniciar Frontend (React)

```bash
# Em outro terminal, na pasta frontend/
npm run dev
```

Acesse o dashboard em: `http://localhost:5173`

---

## 🗺️ Roadmap

### Fase 1: Backend Básico ✅ (Concluído)
- [x] Cliente SCADA-LTS e Coletor.
- [x] Agente LLM básico.

### Fase 2: Agente Ativo ✅ (Concluído)
- [x] Tool Calling (Escrita no SCADA).
- [x] Travas de Segurança (Safety Config).

### Fase 3: Interface Gráfica (Web) 🚧 (Em Progresso)
- [x] Dashboard React.
- [x] Proxy Reverso para SCADA (Bypass Iframe/CORS).
- [x] Integração Chat + WebSocket.
- [ ] Autenticação de Usuário no Dashboard.

### Fase 4: Recursos Avançados (Planejado)
- [ ] Banco de dados persistente.
- [ ] Dashboards customizáveis pelo usuário.
- [ ] Integração com sistema de Alarmes.

---

## 📚 Referências

### Endpoint do Proxy

O acesso ao SCADA via proxy deve ser feito através de:
`http://localhost:8000/Scada-LTS/...`

Isso garante que todos os recursos (imagens, scripts, XHR) passem pelo tratamento de headers do nosso servidor.

---

*Última atualização: Fevereiro 2026*
