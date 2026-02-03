# 📄 Proposta de Evolução: SCADA Agent v2.0

Este documento detalha o planejamento para as próximas duas grandes funcionalidades do sistema: a **Interface de Chat (Web UI)** e a **Capacidade de Escrita (Atuadores)**.

---

## 🏗️ 1. Interface de Chat (Web UI)

O objetivo é migrar da CLI atual para uma interface baseada em navegador que combine o chat conversacional com visualização de dados industrial.

### 1.1 Stack Tecnológica Sugerida
*   **Framework:** [Streamlit](https://streamlit.io/)
*   **Justificativa:** 
    *   Permite criar dashboards e chats em Python puro.
    *   Integração nativa com bibliotecas de gráficos (Plotly/Altair) para mostrar tendências dos sensores.
    *   Gerenciamento de estado de chat simplificado (`st.chat_message`).

### 1.2 Componentes da Interface
1.  **Sidebar de Monitoramento:**
    *   Status de conexão com o SCADA-LTS (Ping em tempo real).
    *   Indicadores numéricos dos 5 sensores principais.
    *   Seletor de Provedor (Gemini/Claude).
2.  **Janela de Chat:**
    *   Histórico de mensagens com suporte a Markdown (respostas da IA).
    *   **Gráficos On-demand:** Quando a IA analisar uma tendência, o sistema deve renderizar um gráfico de linha do buffer de dados logo abaixo da explicação.
3.  **Controles de Sessão:**
    *   Botão para limpar histórico.
    *   Botão para exportar o log da conversa em PDF/Texto.

---

## 🤖 2. Agente Ativo (Capacidade de Escrita)

Atualmente o agente é apenas um observador. A v2.0 permitirá que ele sugira e execute mudanças no processo.

### 2.1 Mecanismo: Tool Calling (Function Calling)
Em vez de apenas gerar texto, o modelo (Gemini/Claude) será configurado com "Ferramentas" (funções Python).
*   **Função `write_scada_point(tag, value)`:** A IA decide qual tag e qual valor enviar.
*   **O fluxo técnico:**
    1.  IA identifica intenção: *"Vou abrir a válvula para 50%"*.
    2.  IA gera uma chamada de função: `{"function": "write_scada_point", "args": {"tag": "cv", "value": 50.0}}`.
    3.  O sistema Python intercepta essa chamada.

### 2.2 Segurança: Human-in-the-Loop
Para evitar que a IA tome decisões perigosas sozinha, implementaremos um **Portão de Aprovação**:
*   A chamada de escrita fica em estado **PENDENTE**.
*   Na UI do chat, aparece um card: `"A IA deseja alterar CV para 50.0. Confirmar?"`.
*   A escrita no SCADA só ocorre após o clique físico do operador no botão **[APROVAR]**.

### 2.3 Travas de Segurança (Interlocks)
Configuração de limites rígidos no código (`src/config.py`):
*   **Safety Limits:** Ex: `freq1` nunca pode receber valor > 60.0 ou < 0.0.
*   **Blacklist:** Tags que a IA nunca pode tocar (ex: reset de alarmes críticos).

---

## 📅 3. Cronograma de Implementação

| Fase | Atividade | Descrição Técnica |
| :--- | :--- | :--- |
| **Fase 1** | **Esqueleto Streamlit** | Criar `app.py`, integrar o `DataCollector` e criar o loop de chat. |
| **Fase 2** | **Visualização Rica** | Implementar renderização de gráficos baseada nas respostas da IA. |
| **Fase 3** | **Ferramentas de Escrita** | Implementar `Function Calling` e a lógica de `Aprovação Pendente`. |
| **Fase 4** | **Hardening de Segurança** | Adicionar os filtros de limites e testes de estresse de segurança. |

---

## ❓ Pontos para Discussão

1.  **Streamlit vs FastAPI/React:** O Streamlit é mais rápido para prototipar, mas o React permite interfaces muito mais customizadas. Qual sua preferência para este estágio?
2.  **Escrita Direta:** Existe algum ponto que você gostaria que a IA escrevesse **sem** pedir autorização (ex: registrar um log no SCADA)?
3.  **Persistência:** O histórico do chat deve ser salvo em banco de dados ou pode ser perdido ao fechar o navegador?

---
*Documento gerado para análise técnica previa à implementação.*
