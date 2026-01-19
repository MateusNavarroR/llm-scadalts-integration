# 🤖 SCADA-LTS Agent - Documentação do Projeto

## Visão Geral

Este projeto integra um sistema SCADA-LTS com um agente inteligente baseado em LLM (Claude), permitindo análise em tempo real de dados de sensores, diagnósticos automatizados e interação conversacional com o sistema.

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
│  │  SCADA-LTS   │    │   Buffer/    │    │   Claude     │       │
│  │    API       │    │   Histórico  │    │    API       │       │
│  └──────────────┘    └──────────────┘    └──────────────┘       │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### Fluxo de Dados

1. **Aquisição**: `ScadaClient` conecta ao SCADA-LTS via API REST
2. **Coleta**: `DataCollector` armazena leituras em buffer temporal
3. **Análise**: `LLMAgent` recebe dados formatados e responde consultas
4. **Interação**: Usuário interage via terminal (futuro: GUI)

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
│   ├── llm_agent.py              # Agente inteligente (Claude)
│   └── config.py                 # Configurações centralizadas
├── tests/
│   └── test_integration.py       # Testes de integração
├── main.py                       # Ponto de entrada da aplicação
├── requirements.txt              # Dependências Python
└── .env.example                  # Exemplo de variáveis de ambiente
```

---

## 🧩 Componentes

### 1. ScadaClient (`scada_client.py`)

Responsável pela comunicação direta com a API do SCADA-LTS.

**Funcionalidades:**
- Autenticação e gerenciamento de sessão
- Leitura de pontos (sensores)
- Escrita de pontos (atuadores)
- Tratamento de erros e reconexão

**Endpoints utilizados:**
| Operação | Endpoint |
|----------|----------|
| Login | `GET /api/auth/{user}/{password}` |
| Leitura | `GET /api/point_value/getValue/{xid}` |
| Escrita | `POST /api/point_value/setValue/{xid}/{type}/{value}` |

### 2. DataCollector (`data_collector.py`)

Gerencia a coleta periódica e armazenamento de dados.

**Funcionalidades:**
- Coleta em background (thread separada)
- Buffer circular com histórico configurável
- Estatísticas (média, min, max, tendência)
- Export para DataFrame/Excel

### 3. LLMAgent (`llm_agent.py`)

Interface com o modelo Claude para análise inteligente.

**Funcionalidades:**
- Formatação de contexto com dados do SCADA
- Histórico de conversação
- Prompts especializados para análise de processo
- Diagnóstico e recomendações

---

## ⚙️ Configuração

### Variáveis de Ambiente

Criar arquivo `.env` na raiz do projeto:

```env
# SCADA-LTS
SCADA_BASE_URL=http://localhost:8080/Scada-LTS
SCADA_USER=Lenhs
SCADA_PASSWORD=123456

# Anthropic API
ANTHROPIC_API_KEY=sua_chave_aqui

# Configurações de Coleta
SAMPLE_RATE_HZ=1.0
BUFFER_SIZE_SECONDS=300
```

### Pontos de Dados (XIDs)

| Variável | XID | Descrição |
|----------|-----|-----------|
| CV (Válvula) | DP_851894 | Posição da válvula de controle |
| Frequência | DP_693642 | Frequência do inversor |
| PT1 | DP_155700 | Pressão transmissor 1 |
| PT2 | DP_719779 | Pressão transmissor 2 |
| FT1 | DP_041666 | Vazão (medidor de fluxo) |

---

## 🚀 Uso

### Instalação

```bash
# Clonar/criar projeto
cd scada_agent_project

# Criar ambiente virtual
python -m venv venv
source venv/bin/activate  # Linux/Mac
# ou: venv\Scripts\activate  # Windows

# Instalar dependências
pip install -r requirements.txt

# Configurar variáveis de ambiente
cp .env.example .env
# Editar .env com suas configurações
```

### Execução

```bash
# Modo interativo (terminal)
python main.py

# Apenas coleta de dados (sem agente)
python main.py --collect-only

# Teste de conexão
python main.py --test-connection
```

### Comandos do Agente

Durante a execução interativa:

| Comando | Descrição |
|---------|-----------|
| `status` | Mostra leituras atuais dos sensores |
| `historico` | Exibe últimas N leituras |
| `analise` | Solicita análise do agente |
| `exportar` | Salva dados em Excel |
| `sair` | Encerra a aplicação |

Ou faça perguntas em linguagem natural:
- "Qual a vazão atual?"
- "A pressão está estável?"
- "O que pode estar causando essa queda de pressão?"

---

## 🗺️ Roadmap

### Fase 1: Backend Básico ✅ (Atual)
- [x] Cliente SCADA-LTS
- [x] Coletor de dados
- [x] Integração básica com Claude
- [x] Interface de terminal

### Fase 2: Melhorias do Agente
- [ ] Prompts especializados para diagnóstico
- [ ] Detecção de anomalias
- [ ] Histórico de conversação persistente
- [ ] Ações automatizadas (com confirmação)

### Fase 3: Interface Gráfica
- [ ] Dashboard com gráficos em tempo real
- [ ] Chat integrado
- [ ] Alertas visuais
- [ ] Configuração via GUI

### Fase 4: Recursos Avançados
- [ ] Banco de dados para histórico longo
- [ ] Múltiplos agentes especializados
- [ ] Integração com alarmes do SCADA
- [ ] API REST própria

---

## 📚 Referências da API SCADA-LTS

### Autenticação

```http
GET /Scada-LTS/api/auth/{username}/{password}
```

Retorna cookie de sessão para requisições subsequentes.

### Leitura de Ponto

```http
GET /Scada-LTS/api/point_value/getValue/{xid}
```

**Resposta:**
```json
{
  "value": "25.5",
  "ts": 1699876543000,
  "status": "OK"
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

### Erro de conexão com SCADA-LTS

1. Verificar se o servidor está rodando
2. Confirmar URL e porta
3. Testar login manualmente no navegador
4. Verificar firewall

### Erro na API do Claude

1. Verificar se a chave API está configurada
2. Confirmar saldo/limites da conta
3. Verificar conectividade com internet

### Dados inconsistentes

1. Verificar XIDs dos pontos
2. Confirmar tipos de dados
3. Verificar se sensores estão online no SCADA

---

## 📝 Notas de Desenvolvimento

- **Thread Safety**: O `DataCollector` usa locks para acesso thread-safe ao buffer
- **Reconexão**: O `ScadaClient` tenta reconectar automaticamente em caso de falha
- **Rate Limiting**: Respeitar limites da API do Claude (verificar plano)
- **Logging**: Usar módulo `logging` para debug e auditoria

---

## 👥 Contribuição

Este é um projeto em desenvolvimento. Sugestões e melhorias são bem-vindas!

---

*Última atualização: Janeiro 2026*
