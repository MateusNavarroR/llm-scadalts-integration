"""
Agente LLM para análise inteligente de dados SCADA
"""
import logging
from typing import List, Dict, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime

from .config import LLMConfig
from .data_collector import DataCollector, DataSnapshot

logger = logging.getLogger(__name__)


@dataclass
class Message:
    """Representa uma mensagem na conversação"""
    role: str  # "user" ou "assistant"
    content: str
    timestamp: datetime = field(default_factory=datetime.now)


class LLMAgent:
    """
    Agente inteligente que usa Claude para análise de dados SCADA.
    
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
        
        # Verifica se a biblioteca anthropic está disponível
        self._anthropic_available = self._check_anthropic()
    
    def _check_anthropic(self) -> bool:
        """Verifica se a biblioteca anthropic está instalada"""
        try:
            import anthropic
            return True
        except ImportError:
            logger.warning("Biblioteca 'anthropic' não instalada. Instale com: pip install anthropic")
            return False
    
    def _get_client(self):
        """Obtém ou cria cliente Anthropic"""
        if not self._anthropic_available:
            raise RuntimeError("Biblioteca 'anthropic' não disponível")
        
        if not self.config.api_key:
            raise ValueError("API key não configurada. Defina ANTHROPIC_API_KEY ou configure manualmente.")
        
        if self._client is None:
            import anthropic
            self._client = anthropic.Anthropic(api_key=self.config.api_key)
        
        return self._client
    
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
    
    def _format_messages_for_api(self) -> List[Dict[str, str]]:
        """Formata histórico de conversação para a API"""
        return [
            {"role": msg.role, "content": msg.content}
            for msg in self.conversation_history[-10:]  # Últimas 10 mensagens
        ]
    
    def ask(self, question: str, include_context: bool = True) -> str:
        """
        Faz uma pergunta ao agente.
        
        Args:
            question: Pergunta do usuário
            include_context: Se True, inclui dados atuais do SCADA
            
        Returns:
            Resposta do agente
        """
        # Monta a mensagem do usuário
        if include_context and self.collector:
            context = self._build_context()
            full_question = f"""Dados atuais do SCADA:
{context}

Pergunta do operador: {question}"""
        else:
            full_question = question
        
        # Adiciona ao histórico
        self.conversation_history.append(Message(role="user", content=full_question))
        
        try:
            client = self._get_client()
            
            response = client.messages.create(
                model=self.config.model,
                max_tokens=self.config.max_tokens,
                system=self.config.system_prompt,
                messages=self._format_messages_for_api()
            )
            
            assistant_message = response.content[0].text
            
            # Adiciona resposta ao histórico
            self.conversation_history.append(Message(role="assistant", content=assistant_message))
            
            return assistant_message
            
        except Exception as e:
            error_msg = f"Erro ao consultar LLM: {str(e)}"
            logger.error(error_msg)
            return error_msg
    
    def analyze_current_state(self) -> str:
        """Solicita análise completa do estado atual"""
        return self.ask(
            "Analise o estado atual do sistema. "
            "Identifique quaisquer anomalias, tendências ou pontos de atenção. "
            "Seja conciso mas completo."
        )
    
    def diagnose_issue(self, symptom: str) -> str:
        """Solicita diagnóstico de um problema específico"""
        return self.ask(
            f"O operador reportou o seguinte sintoma: {symptom}. "
            "Com base nos dados atuais, quais são as possíveis causas? "
            "Sugira ações de verificação ou correção."
        )
    
    def suggest_optimization(self) -> str:
        """Solicita sugestões de otimização"""
        return self.ask(
            "Com base no comportamento recente do sistema, "
            "existem oportunidades de otimização operacional? "
            "Considere eficiência energética, estabilidade e desgaste de equipamentos."
        )
    
    def explain_behavior(self, observation: str) -> str:
        """Solicita explicação de um comportamento observado"""
        return self.ask(
            f"O operador observou: {observation}. "
            "Explique por que isso pode estar acontecendo, "
            "considerando a física do processo e os dados disponíveis."
        )
    
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
        self._anthropic_available = True  # Finge que está disponível
    
    def ask(self, question: str, include_context: bool = True) -> str:
        """Retorna resposta simulada"""
        question_lower = question.lower()
        
        # Adiciona ao histórico
        self.conversation_history.append(Message(role="user", content=question))
        
        # Gera resposta baseada em palavras-chave
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
        return "[MOCK] Esta é uma resposta simulada. Configure a API key do Anthropic para respostas reais do Claude."


def create_agent(
    api_key: str = None,
    collector: DataCollector = None,
    use_mock: bool = False
) -> LLMAgent:
    """
    Factory function para criar agente.
    
    Args:
        api_key: Chave da API Anthropic
        collector: Coletor de dados SCADA
        use_mock: Se True, usa agente mock (sem API)
        
    Returns:
        LLMAgent ou MockLLMAgent
    """
    if use_mock or not api_key:
        logger.info("Usando agente mock (sem API key)")
        return MockLLMAgent(collector)
    
    config = LLMConfig(api_key=api_key)
    return LLMAgent(config, collector)
