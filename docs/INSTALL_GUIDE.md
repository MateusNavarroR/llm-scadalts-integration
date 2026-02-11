# 📖 Guia de Instalação Completo (Windows & Linux)

Este guia cobre a instalação do **SCADA-LTS Agent** partindo do zero, assumindo que sua máquina ainda não possui as ferramentas de desenvolvimento necessárias (Python, Node.js, uv, etc).

---

## 🐧 Instalação no Linux (Ubuntu/Debian)

### 1. Pré-requisitos do Sistema
Primeiro, atualize seu sistema e instale o pacote básico do Python e utilitários.

```bash
sudo apt update && sudo apt upgrade -y
sudo apt install -y python3 python3-pip python3-venv curl git
```

### 2. Instalar Node.js (para o Frontend)
O Node.js disponível nos repositórios padrão pode ser antigo. Recomendamos usar a versão LTS atual.

```bash
# Baixa e instala o NodeSource setup script (Versão 20 LTS recomendada)
curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -

# Instala o Node.js (o npm vem junto)
sudo apt install -y nodejs

# Verifique as versões instaladas
node -v
npm -v
```

### 3. Instalar o Gerenciador de Projetos (uv)
Este projeto usa o **uv** para gerenciar dependências Python de forma extremamente rápida. Se você não o tem, instale-o com o comando oficial:

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh

# Após instalar, talvez seja necessário reiniciar o terminal ou rodar:
source $HOME/.cargo/env  # (Se o instalador sugerir)
```

### 4. Configurar o Projeto

1.  **Clone o repositório** (ou baixe e extraia o ZIP):
    ```bash
    git clone https://github.com/seu-usuario/llm-scadalts-integration.git
    cd llm-scadalts-integration
    ```

2.  **Configurar o Backend (Python)**:
    O `uv` criará o ambiente virtual e baixará tudo automaticamente.
    ```bash
    # Cria o venv e instala dependências
    uv sync
    ```

3.  **Configurar o Frontend (React)**:
    ```bash
    cd frontend
    npm install
    cd ..
    ```

4.  **Variáveis de Ambiente**:
    ```bash
    cp .env.example .env
    # Edite o arquivo .env com suas configurações
    nano .env
    ```

---

## 🪟 Instalação no Windows

### 1. Instalar Python
1.  Acesse [python.org/downloads](https://www.python.org/downloads/).
2.  Baixe a versão mais recente (3.11 ou superior).
3.  **IMPORTANTE:** Na tela de instalação, marque a caixa **"Add python.exe to PATH"**.
4.  Clique em "Install Now".

### 2. Instalar Node.js
1.  Acesse [nodejs.org](https://nodejs.org/).
2.  Baixe a versão **LTS** (Recomendada para a maioria dos usuários).
3.  Execute o instalador e siga os passos (Next, Next, Install).

Obs: se ainda sim obter erro de permissão ao tentar usar o comando npm no terminal, execute o seguinte comando no terminal

```powershell
Set-ExecutionPolicy RemotedSigned -Scope CurrentUser
```

e reinicie o terminal

### 3. Instalar o Gerenciador (uv)
Abra o **PowerShell** (como Administrador, de preferência) e execute:

```powershell
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

*Nota: Se o comando acima falhar por políticas de segurança, você pode instalar via pip (o gerenciador padrão do Python):*
```powershell
pip install uv
```

### 4. Configurar o Projeto

1.  **Baixe o Projeto**:
    *   Se tiver `git`: `git clone ...`
    *   Se não, baixe o ZIP do GitHub, extraia e abra a pasta no terminal (PowerShell ou CMD).

2.  **Configurar Backend**:
    Na pasta raiz do projeto:
    ```powershell
    uv sync
    ```

3.  **Configurar Frontend**:
    ```powershell
    cd frontend
    npm install
    cd ..
    ```

4.  **Configurar Ambiente**:
    *   Copie o arquivo `.env.example` e renomeie para `.env`.
    *   Abra o `.env` no Bloco de Notas ou VS Code e preencha as configurações.

---

## 🚀 Como Rodar o Sistema

Você precisará de **dois terminais** abertos.

### Terminal 1: Backend (API & Agente)
Este terminal roda o servidor Python.

```bash
# Linux/Mac
uv run uvicorn src.server:app --reload --host 0.0.0.0 --port 8000

# Windows (PowerShell)
uv run uvicorn src.server:app --reload --host 0.0.0.0 --port 8000
```
*Se tudo der certo, você verá logs indicando que o servidor está rodando na porta 8000.*

### Terminal 2: Frontend (Interface Web)
Este terminal roda a interface gráfica.

```bash
cd frontend
npm run dev
```
*O terminal mostrará um link, geralmente `http://localhost:5173`. Acesse esse link no seu navegador.*

---

## ❓ Solução de Problemas Comuns

**Erro: "uv não é reconhecido..."**
*   **Causa:** O `uv` foi instalado mas não está no seu PATH (caminho do sistema).
*   **Solução:** Reinicie o terminal/computador. Se persistir, tente rodar usando `python -m uv ...` se instalou via pip.

**Erro: "npm command not found"**
*   **Causa:** Node.js não foi instalado corretamente ou o terminal não foi reiniciado.
*   **Solução:** Reinstale o Node.js e garanta que reiniciou o terminal.

**O Backend conecta, mas o Frontend dá erro de rede**
*   Verifique se o backend está rodando na porta 8000.
*   Verifique se o frontend está configurado para apontar para `http://localhost:8000` (normalmente automático pelo proxy do Vite).

**Erro de Permissão no Linux**
*   Se tiver erros de "Permission denied" ao rodar `npm install`, evite usar `sudo`. Em vez disso, corrija as permissões da sua pasta home ou use um gerenciador de versão como o NVM.
