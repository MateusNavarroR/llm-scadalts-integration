"Agente LLM para análise inteligente de dados SCADA"
import logging
from typing import List, Dict, Optional, Any, Union
from dataclasses import dataclass, field
from datetime import datetime

from .config import LLMConfig, config as app_config
from .data_collector import DataCollector, DataSnapshot

logger = logging.getLogger(__name__)


@dataclass
class Message:
    """Representa uma mensagem na conversação"""
    role: str  # "user" ou "assistant"
    content: str
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class ToolRequest:
    """Representa uma intenção do agente de usar uma ferramenta"""
    tool_name: str
    arguments: Dict[str, Any]
    thought: str = ""  # O raciocínio do agente antes de chamar a ferramenta


def write_scada_point(tag: str, value: float):
    """
    Altera o valor de um ponto no sistema SCADA (Escrita).
    Use para ajustar setpoints, abrir/fechar válvulas ou ligar/desligar equipamentos.
    
    Args:
        tag: Nome da tag (ex: 'cv', 'freq1', 'bomba').
        value: Novo valor numérico para o ponto.
    """
    pass


class LLMAgent:
    """
    Agente inteligente que usa LLM (Claude ou Gemini) para análise de dados SCADA.
    
    Uso:
        agent = LLMAgent(config, collector)
        response = agent.ask("Qual a situação atual do sistema?")
        response = agent.analyze_current_state()
    """
    
    def __init__(
        self,
        config: LLMConfig,
        collector: DataCollector = None
    ):
        self.config = config
        self.collector = collector
        self.conversation_history: List[Message] = []
        self._client = None
        self._gemini_model = None
        
        # Verifica bibliotecas disponíveis
        self._anthropic_available = False
        self._gemini_available = False
        self._check_dependencies()
    
    def _check_dependencies(self):
        """Verifica quais bibliotecas de LLM estão instaladas"""
        try:
            import anthropic
            self._anthropic_available = True
        except ImportError:
            pass
            
        try:
            import google.generativeai as genai
            self._gemini_available = True
        except ImportError:
            pass
            
        if self.config.provider == "anthropic" and not self._anthropic_available:
            logger.warning("Provedor configurado como 'anthropic', mas biblioteca não encontrada.")
        elif self.config.provider == "gemini" and not self._gemini_available:
            logger.warning("Provedor configurado como 'gemini', mas biblioteca 'google-generativeai' não encontrada.")
    
    def _get_anthropic_client(self):
        """Obtém ou cria cliente Anthropic"""
        if not self._anthropic_available:
            raise RuntimeError("Biblioteca 'anthropic' não disponível. Instale com: pip install anthropic")
        
        if not self.config.api_key:
            raise ValueError("API key não configurada para Anthropic.")
        
        if self._client is None:
            import anthropic
            self._client = anthropic.Anthropic(api_key=self.config.api_key)
        
        return self._client

    def _get_gemini_model(self):
        """Obtém ou configura modelo Gemini"""
        if not self._gemini_available:
            raise RuntimeError("Biblioteca 'google-generativeai' não disponível. Instale com: pip install google-generativeai")
        
        if not self.config.api_key:
            raise ValueError("API key não configurada para Gemini.")
            
        if self._gemini_model is None:
            import google.generativeai as genai
            genai.configure(api_key=self.config.api_key)
            
            # Configuração do modelo
            generation_config = {
                "temperature": 0.7,
                "top_p": 0.95,
                "top_k": 40,
                "max_output_tokens": self.config.max_tokens,
            }
            
            # Ferramentas disponíveis
            tools = [write_scada_point]
            
            self._gemini_model = genai.GenerativeModel(
                model_name=self.config.model,
                generation_config=generation_config,
                system_instruction=self.config.system_prompt,
                tools=tools
            )
            
        return self._gemini_model
    
    def _build_context(self) -> str:
        """Constrói contexto com dados atuais do SCADA"""
        if not self.collector:
            return "Sistema SCADA não conectado."
        
        parts = []
        
        # Leitura atual
        snapshot = self.collector.get_latest()
        if snapshot:
            parts.append("=== LEITURA ATUAL ===")
            parts.append(f"Timestamp: {snapshot.timestamp.strftime('%Y-%m-%d %H:%M:%S')}")
            for name, value in snapshot.values.items():
                parts.append(f"  {name}: {value:.3f}")
        
        # Estatísticas recentes
        stats = self.collector.get_statistics()
        if stats and "error" not in stats:
            parts.append("\n=== ESTATÍSTICAS (últimos 5 min) ===")
            for name, s in stats.items():
                parts.append(f"  {name}: média={s['mean']:.2f}, min={s['min']:.2f}, max={s['max']:.2f}")
        
        # Status do coletor
        status = self.collector.get_status()
        parts.append(f"\n=== STATUS DO COLETOR ===")
        parts.append(f"  Amostras coletadas: {status['samples_collected']}")
        parts.append(f"  Erros: {status['errors_count']}")
        parts.append(f"  Buffer: {status['buffer_size']}/{status['buffer_max']}")
        
        return "\n".join(parts)
    
    def _format_messages_for_anthropic(self) -> List[Dict[str, str]]:
        """Formata histórico para Anthropic"""
        return [
            {"role": msg.role, "content": msg.content}
            for msg in self.conversation_history[-10:]
        ]

    def _format_history_for_gemini(self) -> List[Dict[str, Any]]:
        """Formata histórico para Gemini"""
        gemini_history = []
        for msg in self.conversation_history[-10:]:
            role = "user" if msg.role == "user" else "model"
            gemini_history.append({
                "role": role,
                "parts": [msg.content]
            })
        return gemini_history
    
    def ask(self, question: str, include_context: bool = True) -> Union[str, ToolRequest]:
        """
        Faz uma pergunta ao agente.
        
        Args:
            question: Pergunta do usuário
            include_context: Se True, inclui dados atuais do SCADA
            
        Returns:
            Resposta do agente (texto) ou ToolRequest (intenção de ação)
        """
        # Monta a mensagem do usuário com contexto
        if include_context and self.collector:
            context = self._build_context()
            full_question = f"""Dados atuais do SCADA:
{context}

Pergunta do operador: {question}"""
        else:
            full_question = question
        
        # Adiciona mensagem do usuário ao histórico interno (sempre role 'user')
        self.conversation_history.append(Message(role="user", content=full_question))
        
        try:
            if self.config.provider == "gemini":
                return self._ask_gemini(full_question)
            else:
                return self._ask_anthropic()
                
        except Exception as e:
            error_msg = f"Erro ao consultar LLM ({self.config.provider}): {str(e)}"
            logger.error(error_msg)
            return error_msg

    def _ask_anthropic(self) -> str:
        # TODO: Implementar suporte a tools no Anthropic
        client = self._get_anthropic_client()
        
        response = client.messages.create(
            model=self.config.model,
            max_tokens=self.config.max_tokens,
            system=self.config.system_prompt,
            messages=self._format_messages_for_anthropic()
        )
        
        assistant_message = response.content[0].text
        self.conversation_history.append(Message(role="assistant", content=assistant_message))
        return assistant_message

    def _ask_gemini(self, current_prompt: str) -> Union[str, ToolRequest]:
        model = self._get_gemini_model()
        previous_history = self._format_history_for_gemini()[:-1] 
        
        chat = model.start_chat(history=previous_history)
        response = chat.send_message(current_prompt)
        
        # Processa resposta
        text_content = ""
        tool_request = None
        
        # Verifica as partes da resposta
        if hasattr(response, 'parts'):
            for part in response.parts:
                # Extrai texto
                if part.text:
                    text_content += part.text
                
                # Extrai chamada de função
                if part.function_call:
                    tool_request = ToolRequest(
                        tool_name=part.function_call.name,
                        arguments=dict(part.function_call.args),
                        thought=text_content.strip()
                    )
        
        # Se houve erro ou não tem parts (caso raro no SDK novo)
        if not text_content and not tool_request:
             text_content = response.text

        # Registra no histórico
        if tool_request:
            # Salva representação da ação no histórico
            log_content = f"{text_content}\n[INTENÇÃO DE AÇÃO: {tool_request.tool_name} {tool_request.arguments}]"
            self.conversation_history.append(Message(role="assistant", content=log_content))
            return tool_request
        else:
            self.conversation_history.append(Message(role="assistant", content=text_content))
            return text_content
    
    def analyze_current_state(self) -> str:
        """Solicita análise completa do estado atual"""
        response = self.ask(
            "Analise o estado atual do sistema. "
            "Identifique quaisquer anomalias, tendências ou pontos de atenção. "
            "Seja conciso mas completo."
        )
        # Se retornar ToolRequest (improvável para análise), converte para string
        if isinstance(response, ToolRequest):
            return f"O agente tentou executar uma ação durante a análise: {response.tool_name}"
        return response
    
    def diagnose_issue(self, symptom: str) -> str:
        """Solicita diagnóstico de um problema específico"""
        response = self.ask(
            f"O operador reportou o seguinte sintoma: {symptom}. "
            "Com base nos dados atuais, quais são as possíveis causas? "
            "Sugira ações de verificação ou correção."
        )
        if isinstance(response, ToolRequest):
             return f"O agente sugeriu uma ação corretiva: {response.tool_name} {response.arguments}"
        return response
    
    def suggest_optimization(self) -> str:
        """Solicita sugestões de otimização"""
        response = self.ask(
            "Com base no comportamento recente do sistema, "
            "existem oportunidades de otimização operacional? "
            "Considere eficiência energética, estabilidade e desgaste de equipamentos."
        )
        if isinstance(response, ToolRequest):
            return f"Sugestão de otimização automática: {response.tool_name} {response.arguments}"
        return response
    
    def explain_behavior(self, observation: str) -> str:
        """Solicita explicação de um comportamento observado"""
        response = self.ask(
            f"O operador observou: {observation}. "
            "Explique por que isso pode estar acontecendo, "
            "considerando a física do processo e os dados disponíveis."
        )
        if isinstance(response, ToolRequest):
             return f"O agente tentou reagir a observação: {response.tool_name}"
        return response
    
    def clear_history(self):
        """Limpa histórico de conversação"""
        self.conversation_history.clear()
        logger.info("Histórico de conversação limpo")
    
    def get_history_summary(self) -> str:
        """Retorna resumo do histórico de conversação"""
        if not self.conversation_history:
            return "Nenhuma conversação ainda."
        
        lines = [f"Total de mensagens: {len(self.conversation_history)}"]
        for msg in self.conversation_history[-5:]:
            preview = msg.content[:100] + "..." if len(msg.content) > 100 else msg.content
            lines.append(f"[{msg.role}] {preview}")
        
        return "\n".join(lines)


class MockLLMAgent(LLMAgent):
    """
    Versão mock do agente para testes sem API key.
    Retorna respostas simuladas baseadas em padrões simples.
    """
    
    def __init__(self, collector: DataCollector = None):
        # Inicializa com config vazia
        super().__init__(LLMConfig(), collector)
        self._anthropic_available = True 
        self._gemini_available = True
    
    def ask(self, question: str, include_context: bool = True) -> Union[str, ToolRequest]:
        """Retorna resposta simulada"""
        question_lower = question.lower()
        
        # Adiciona ao histórico
        self.conversation_history.append(Message(role="user", content=question))
        
        # SIMULAÇÃO DE TOOL CALL
        if "ligar" in question_lower or "abrir" in question_lower or "ajustar" in question_lower or "mudar" in question_lower:
            # Simula uma intenção de escrita se o usuário usar verbos de ação
            import re
            # Tenta extrair um número
            val_match = re.search(r'(\d+)', question)
            val = float(val_match.group(1)) if val_match else 50.0
            
            tag = "cv" if "valvula" in question_lower or "válvula" in question_lower else "freq1"
            
            tool_req = ToolRequest(
                tool_name="write_scada_point",
                arguments={"tag": tag, "value": val},
                thought=f"[MOCK] Entendi que você quer alterar {tag} para {val}."
            )
            
            self.conversation_history.append(Message(
                role="assistant", 
                content=f"{tool_req.thought}\n[TOOL: {tool_req.tool_name}]"
            ))
            return tool_req

        # Gera resposta baseada em palavras-chave (texto normal)
        if "status" in question_lower or "atual" in question_lower:
            response = self._mock_status_response()
        elif "problema" in question_lower or "erro" in question_lower:
            response = self._mock_diagnostic_response()
        elif "pressão" in question_lower:
            response = self._mock_pressure_response()
        elif "vazão" in question_lower:
            response = self._mock_flow_response()
        else:
            response = self._mock_generic_response()
        
        self.conversation_history.append(Message(role="assistant", content=response))
        return response
    
    def _mock_status_response(self) -> str:
        if self.collector:
            snapshot = self.collector.get_latest()
            if snapshot:
                return f"""[MOCK] Análise do estado atual:

Os sensores mostram operação dentro dos parâmetros normais.
- Vazão (ft1): {snapshot.values.get('ft1', 0):.2f} - OK
- Pressões: PT1={snapshot.values.get('pt1', 0):.2f}, PT2={snapshot.values.get('pt2', 0):.2f}
- Diferencial de pressão: {snapshot.values.get('pt2', 0) - snapshot.values.get('pt1', 0):.2f}

Nenhuma anomalia detectada no momento."""
        
        return "[MOCK] Sistema operando normalmente. Conecte ao SCADA para dados reais."
    
    def _mock_diagnostic_response(self) -> str:
        return """[MOCK] Diagnóstico:

Possíveis causas para problemas típicos:
1. Queda de pressão: Verificar vazamentos ou obstruções
2. Vazão instável: Checar frequência do inversor e válvula
3. Ruído nos sensores: Verificar conexões e aterramento

Recomendo verificar os logs do SCADA para mais detalhes."""
    
    def _mock_pressure_response(self) -> str:
        return "[MOCK] A pressão no sistema depende da vazão e das perdas de carga. Monitore PT1 e PT2 para análise completa."
    
    def _mock_flow_response(self) -> str:
        return "[MOCK] A vazão é controlada principalmente pela frequência do inversor e posição da válvula CV."
    
    def _mock_generic_response(self) -> str:
        return "[MOCK] Esta é uma resposta simulada. Configure a API key do Anthropic ou Gemini para respostas reais."


def create_agent(
    api_key: str = None,
    collector: DataCollector = None,
    use_mock: bool = False
) -> LLMAgent:
    """
    Factory function para criar agente.
    
    Args:
        api_key: Chave da API (Anthropic ou Gemini)
        collector: Coletor de dados SCADA
        use_mock: Se True, usa agente mock (sem API)
        
    Returns:
        LLMAgent ou MockLLMAgent
    """
    if use_mock:
        logger.info("Usando agente mock (solicitado explicitamente)")
        return MockLLMAgent(collector)
        
    if not api_key:
        # Tenta pegar da config global
        from .config import config
        api_key = config.llm.api_key
        
    if not api_key:
        logger.info("Usando agente mock (sem API key encontrada)")
        return MockLLMAgent(collector)
    
    # Se chegamos aqui, temos uma API key. A classe LLMAgent vai decidir
    # qual provedor usar baseada na configuração.
    # Note que passamos a key via config object na inicialização da classe
    config_obj = LLMConfig(api_key=api_key)
    
    return LLMAgent(config_obj, collector)