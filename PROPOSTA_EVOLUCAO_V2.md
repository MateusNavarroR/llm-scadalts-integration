# 📄 Proposta de Evolução: SCADA Agent v2.0

Este documento detalha o planejamento para a próxima grande funcionalidade do sistema: a **Interface de Chat (Web UI)**. A capacidade de escrita e o agente ativo foram implementados na v1.1.

---

## ✅ Funcionalidades Recém-Implementadas (v1.1)

### 1. Agente Ativo (Capacidade de Escrita)
O agente agora possui capacidade de interagir com o processo via **Tool Calling**.
*   **Mecanismo:** O modelo (Gemini) utiliza a ferramenta `write_scada_point(tag, value)`.
*   **Segurança (Human-in-the-Loop):** Implementado no `main.py`. Toda ação sugerida pela IA exige confirmação manual do operador `[s/N]`.
*   **Travas de Segurança:** Integrado ao `src/config.py` com limites operacionais (ex: freq 0-60Hz) e blacklist de tags sensíveis.

---

## 🏗️ 2. Interface de Chat (Web UI)

O objetivo é migrar da CLI atual para uma interface baseada em navegador que combine o chat conversacional com visualização de dados industrial.

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
