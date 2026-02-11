# 🤖 SCADA-LTS Agent Integration

Este projeto integra um sistema SCADA-LTS com um agente inteligente (Claude ou Gemini), permitindo análise em tempo real de dados de sensores, controle assistido por IA e uma interface web moderna.

## 🚀 Novidades na v1.2

A aplicação evoluiu de um script CLI para uma plataforma Full-Stack:
*   **🌐 Dashboard Web:** Interface em React com gráficos em tempo real.
*   **🧠 Agente Híbrido:** Chat integrado que entende o contexto do processo.
*   **🔌 Proxy Inteligente:** Acesso ao SCADA-LTS sem problemas de CORS ou bloqueios de Iframe.
*   **🛡️ Segurança Reforçada:** Travas operacionais e aprovação humana obrigatória para comandos de escrita.

---

## 📦 Instalação e Configuração

### Pré-requisitos
Este projeto utiliza **[uv](https://github.com/astral-sh/uv)** para gerenciamento de dependências Python.

> **🆕 Guia para Iniciantes**
> Se você está instalando em uma máquina nova (Windows ou Linux), siga nosso:
> 📖 [**Guia de Instalação Detalhado**](docs/INSTALL_GUIDE.md)

### Configuração Rápida
1.  **Instale o uv**: `curl -LsSf https://astral.sh/uv/install.sh | sh`
2.  **Configure o .env**:
    ```bash
    cp .env.example .env
    # Edite com suas credenciais do SCADA e Chaves de API (Gemini/Claude)
    ```

---

## 🛠️ Como Executar

O sistema é composto por dois módulos principais que devem rodar simultaneamente:

### 1. Backend (API & Proxy)
O servidor FastAPI gerencia a comunicação com o SCADA, o coletor de dados e o agente IA.
```bash
uv run uvicorn src.server:app --reload --host 0.0.0.0 --port 8000
```

### 2. Frontend (Interface Web)
A interface React para monitoramento e chat.
```bash
cd frontend
npm install
npm run dev
```
Acesse em: `http://localhost:5173`

> **Nota:** Você também pode rodar o modo CLI clássico usando `uv run main.py`.

---

## 🧠 Capacidades do Agente

O agente detecta automaticamente o provedor (`GEMINI_API_KEY` ou `ANTHROPIC_API_KEY`) e oferece:
*   **Monitoramento Ativo:** Analisa tendências e avisa sobre anomalias.
*   **Comandos de Voz/Texto:** "Qual a pressão atual?" ou "Ajuste a vazão para 50%".
*   **Segurança (Human-in-the-Loop):** Comandos de escrita exigem confirmação explícita do operador no Dashboard.

---

## 📁 Estrutura do Projeto

*   `src/server.py`: Servidor Backend FastAPI (API, WebSockets e Proxy).
*   `frontend/`: Aplicação React + Vite + Tailwind.
*   `src/llm_agent.py`: Lógica do Agente (Tool Calling e Prompts).
*   `src/scada_client.py`: Integração com API REST do SCADA-LTS.
*   `main.py`: Interface de linha de comando (CLI).
*   `docs/`: Documentação técnica e manuais.

---

## 🛠️ Ferramentas de Diagnóstico

*   `test_read_write.py`: Script para testar leitura/escrita rápida em pontos do SCADA.
*   `PROPOSTA_EVOLUCAO_V2.md`: Detalhes sobre o roadmap e arquitetura futura.

---
*Desenvolvido para integração avançada de sistemas industriais e IA.*
