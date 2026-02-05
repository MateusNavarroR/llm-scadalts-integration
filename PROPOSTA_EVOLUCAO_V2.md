# 📄 Proposta de Evolução: SCADA Agent v2.0 (Status: MVP Implementado)

Este documento detalha a evolução do sistema para a **Interface Web (React + FastAPI)**. A arquitetura foi definida e o MVP já está funcional, integrando Chat, Dashboard e Proxy SCADA.

---

## ✅ Funcionalidades Implementadas (v1.2)

### 1. Interface Web Moderna (React)
Optamos pela arquitetura **React + Vite** (em vez de Streamlit) para maior flexibilidade e desempenho.
- **Dashboard**: Visualização de KPIs (Pressão, Vazão, etc.) e gráficos em tempo real via WebSocket.
- **Chat Integrado**: Interface conversacional com o Agente IA na mesma tela.
- **Embedded SCADA**: O SCADA-LTS legado é renderizado dentro de um Iframe, permitindo operação híbrida.

### 2. Backend & Proxy (FastAPI)
O backend foi migrado para FastAPI para suportar WebSocket e servir como Proxy Reverso.
- **Proxy Inteligente**: Resolve problemas de CORS, `X-Frame-Options` e Cookies, permitindo que o SCADA antigo funcione dentro da aplicação moderna.
- **WebSocket**: Streaming de dados de sensores com latência < 1s.

### 3. Agente Ativo (Capacidade de Escrita)
O agente interage com o processo via **Tool Calling** (Gemini).
*   **Segurança:** Toda ação sugerida pela IA exige aprovação explícita na interface ("Aprovar/Recusar").
*   **Travas:** Limites operacionais configurados no backend.

---

## 📅 3. Cronograma Atualizado

| Fase | Status | Descrição Técnica |
| :--- | :--- | :--- |
| **Fase 1** | ✅ Concluído | **Esqueleto React + FastAPI**: Configuração do projeto, WebSocket e coleta de dados. |
| **Fase 2** | ✅ Concluído | **Proxy SCADA**: Implementação do bypass de headers e cookies para embutir o SCADA-LTS. |
| **Fase 3** | 🚧 Em Progresso | **Refinamento UX**: Melhoria no feedback visual de ações e tratamento de erros de conexão. |
| **Fase 4** | 📅 Planejado | **Persistência & Auth**: Login de usuário no Dashboard e histórico de chat persistente (Banco de Dados). |

---

## ❓ Questões Resolvidas

1.  **Arquitetura:** Definida como **React + FastAPI**. O Streamlit foi descartado para permitir o embedding seguro do SCADA via Iframe e maior controle de layout.
2.  **Escrita Direta:** Mantida a política de **Human-in-the-Loop**. Nenhuma escrita crítica ocorre sem clique de aprovação.
3.  **Persistência:** Por enquanto, o histórico é volátil (memória). Próximo passo é integrar SQLite/PostgreSQL.

---
*Documento atualizado: Fevereiro 2026*
