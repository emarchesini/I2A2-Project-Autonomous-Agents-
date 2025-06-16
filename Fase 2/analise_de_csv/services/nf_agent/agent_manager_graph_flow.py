# agent_manager.py
import asyncio
from autogen_agentchat.agents import AssistantAgent, UserProxyAgent
from autogen_agentchat.base import TaskResult
from autogen_agentchat.conditions import TextMentionTermination, MaxMessageTermination
from autogen_agentchat.teams import DiGraphBuilder, GraphFlow
from autogen_ext.models.ollama import OllamaChatCompletionClient
from autogen_ext.tools.mcp import StdioServerParams, mcp_server_tools
from typing import AsyncGenerator, Dict, Any, Callable, Optional
import logging
import json
from config import (
    OLLAMA_HOST, OLLAMA_MODEL, OLLAMA_FUNCTION_CALLING, OLLAMA_JSON_OUTPUT, OLLAMA_VISION,
    FILESYSTEM_MOUNT_PATH, FILESYSTEM_CONTAINER_PATH, 
    POSTGRES_URL, POSTGRES_DATABASE, POSTGRES_SCHEMA, 
    MAX_MESSAGES, MCP_FILESYSTEM_IMAGE, MCP_POSTGRES_IMAGE,
    OLLAMA2_HOST, OLLAMA2_MODEL, OLLAMA2_FUNCTION_CALLING, OLLAMA2_JSON_OUTPUT, OLLAMA2_VISION
)
from autogen_core.logging import LLMCallEvent
from autogen_core import CancellationToken
from autogen_agentchat.ui import Console
from autogen_agentchat.messages import HandoffMessage, TextMessage

logger = logging.getLogger(__name__)

class InteractiveUserProxy(UserProxyAgent):
    """Enhanced UserProxy that can request input during execution"""
    
    def __init__(self, name: str, input_callback: Optional[Callable] = None, **kwargs):
        super().__init__(name, **kwargs)
        self.input_callback = input_callback
        self.pending_input = None
        self.input_event = None
    
    async def get_human_input(self, prompt: str) -> str:
        """Get input from human via callback mechanism"""
        if self.input_callback:
            # Signal that we need input
            self.pending_input = prompt
            self.input_event = asyncio.Event()
            
            # Notify the callback that input is needed
            await self.input_callback({
                "type": "input_request",
                "prompt": prompt,
                "agent": self.name
            })
            
            # Wait for input to be provided
            await self.input_event.wait()
            
            # Return the provided input
            result = self.pending_input
            self.pending_input = None
            self.input_event = None
            return result
        else:
            # Nunca tente input() em ambiente web!
            raise RuntimeError("User input requested but no callback is set (web mode)")
    
    def provide_input(self, user_input: str):
        """Provide input from external source"""
        if self.input_event:
            self.pending_input = user_input
            self.input_event.set()

class AgentManagerGraphFlow:
    """Manager class for handling autogen agents and their interactions using GraphFlow"""
    
    def __init__(self):
        self.team = None
        self.model_client = None
        self.model_client2 = None  # Novo model client
        self.initialized = False
        self.user_proxy = None
        self.current_task_id = None
        self.input_callback = None
        self.log_callback = None  # Callback para logs
        self.chat_enabled = True
        self.total_tokens = 0  # Initialize token counter
        
    async def initialize(self):
        """Initialize the agent team and tools"""
        try:
            # MCP Server parameters - using externalized configurations
            filesystem_mcp_server_params = StdioServerParams(
                command="docker", 
                args=["run", "-i", "--rm", "--mount",
                      f"type=bind,src={FILESYSTEM_MOUNT_PATH},dst={FILESYSTEM_CONTAINER_PATH}",
                      MCP_FILESYSTEM_IMAGE,
                      FILESYSTEM_CONTAINER_PATH]
            )

            postgres_mcp_server_params = StdioServerParams(
                command="docker", 
                args=["run", "-i", "--rm", "--add-host=host.docker.internal:host-gateway", 
                      MCP_POSTGRES_IMAGE, POSTGRES_URL]
            )

            # Create model client - using externalized configurations
            self.model_client = OllamaChatCompletionClient(
                model=OLLAMA_MODEL,
                host=OLLAMA_HOST,
                model_info={
                    "function_calling": OLLAMA_FUNCTION_CALLING,
                    "json_output": OLLAMA_JSON_OUTPUT,
                    "vision": OLLAMA_VISION,
                    "family": "unknown"
                },
                options={}
            )
            self.model_client2 = OllamaChatCompletionClient(
                model=OLLAMA2_MODEL,
                host=OLLAMA2_HOST,
                model_info={
                    "function_calling": OLLAMA2_FUNCTION_CALLING,
                    "json_output": OLLAMA2_JSON_OUTPUT,
                    "vision": OLLAMA2_VISION,
                    "family": "unknown"
                },
                options={}
            )

            print("OLLAMA HOSTS")
            print(OLLAMA2_HOST,OLLAMA_HOST)
            print("OLLAMA models")
            print(OLLAMA2_MODEL,OLLAMA_MODEL)
            
            
            postgres_tools = await mcp_server_tools(postgres_mcp_server_params)
            

            # Create interactive user proxy
            self.user_proxy = InteractiveUserProxy(
                name="user_proxy",
                input_callback=self._handle_input_request,
                description="Representa o usuário e inicia as conversas com pedidos"
            )

            # Create agents
            pg_agent = AssistantAgent(
                name="pg_agent",
                model_client=self.model_client,
                tools=postgres_tools,
                description="Agente responsável pela recuperação de dados e metadados em bancos de dados",
                system_message="""
                1. Identidade e Função Exclusiva:
                Você é um assistente especializado, designado exclusivamente como pg_agent. Seu objetivo primário e único é interagir com o banco de dados PostgreSQL da empresa para recuperar informações.
                2. Formato de Entrada Obrigatório:
                Você DEVE processar mensagens que sigam ESTRITAMENTE o formato: {agent:"pg_agent",tarefa:"uma tarefa qualquer"}.
                Qualquer solicitação que não siga este formato DEVE ser ignorada.
                Você NÃO DEVE criar novas tarefas. A criação de tarefas é uma função EXCLUSIVA do agente main_agent.
                3. Capacidades e Uso de Ferramentas (Diretrizes Estritas):
                Você possui acesso e DEVE UTILIZAR OBRIGATORIAMENTE ferramentas específicas para:
                Executar queries SQL: Traduza demandas do usuário em linguagem natural para consultas SQL e execute-as no banco de dados.
                Consultar o schema do banco de dados: Para entender a estrutura das tabelas, nomes de colunas e tipos de dados.
                Retornar resultados: TODOS os resultados solicitados DEVEM ser obtidos e apresentados DIRETAMENTE por meio de uma chamada bem-sucedida à sua ferramenta de consulta ao banco.
                4. Escopo e Banco de Dados Padrão:
                Sua atuação está RESTRITA à recuperação de informações do banco de dados.
                Quando o banco de dados ou esquema não for explicitamente mencionado, DEVE SEMPRE consultar o banco de dados notasfiscais e o esquema public.
                5. Processamento de Demandas e Dicionário de Dados:
                Tradução SQL: Você DEVE traduzir as demandas do usuário para a sintaxe SQL precisa.
                Metadados: Se o usuário solicitar metadados (como nomes de colunas, tipos de dados), você DEVE consultar o schema do banco de dados para fornecer essas informações.
                Dicionário de Dados: O Dicionário de Dados fornecido abaixo é sua fonte de verdade para a estrutura do banco. CONSULTE-O SEMPRE para garantir a precisão das queries, nomes de tabelas e colunas, e compreensão dos dados.
                
                campos da tabela notasfiscais:
                chave_acesso (VARCHAR, 44) - Chave de acesso única da nota fiscal (PK)
                modelo (VARCHAR, 100) - Modelo da nota fiscal
                serie_nf (VARCHAR, 10) - Série da nota fiscal
                numero_nf (VARCHAR, 20) - Número da nota fiscal
                natureza_operacao (VARCHAR, 255) - Descrição da natureza da operação
                data_emissao (DATE) - Data de emissão da nota fiscal
                evento_mais_recente (VARCHAR, 255) - Último evento registrado
                data_hora_evento_mais_recente (TIMESTAMP) - Data e hora do último evento
                cpf_cnpj_emitente (VARCHAR, 20) - CPF ou CNPJ do emitente
                razao_social_emitente (VARCHAR, 255) - Razão social do emitente
                inscricao_estadual_emitente (VARCHAR, 20) - Inscrição estadual do emitente
                uf_emitente (CHAR, 2) - UF do emitente
                municipio_emitente (VARCHAR, 100) - Município do emitente
                cnpj_destinatario (VARCHAR, 20) - CNPJ do destinatário
                nome_destinatario (VARCHAR, 255) - Nome/razão social do destinatário
                uf_destinatario (CHAR, 2) - UF do destinatário
                indicador_ie_destinatario (VARCHAR, 50) - Indicador de IE do destinatário
                destino_operacao (VARCHAR, 100) - Tipo de destino da operação
                consumidor_final (VARCHAR, 50) - Indicador se é consumidor final
                presenca_comprador (VARCHAR, 100) - Indicador de presença do comprador
                valor_nota_fiscal (DECIMAL, 15,2) - Valor total da nota fiscal
                
                campos da tabela itensnotafiscal:
                id_item_nf (SERIAL) - ID único do item (PK)
                chave_acesso_nf (VARCHAR, 44) - Chave de acesso da nota fiscal (FK para notasfiscais)
                modelo (VARCHAR, 100)
                serie_nf (VARCHAR, 10)
                numero_nf (VARCHAR, 20)
                natureza_operacao (VARCHAR, 255)
                data_emissao (DATE)
                cpf_cnpj_emitente (VARCHAR, 20)
                razao_social_emitente (VARCHAR, 255)
                inscricao_estadual_emitente (VARCHAR, 20)
                uf_emitente (CHAR, 2)
                municipio_emitente (VARCHAR, 100)
                cnpj_destinatario (VARCHAR, 20)
                nome_destinatario (VARCHAR, 255)
                uf_destinatario (CHAR, 2)
                indicador_ie_destinatario (VARCHAR, 50)
                destino_operacao (VARCHAR, 100)
                consumidor_final (VARCHAR, 50)
                presenca_comprador (VARCHAR, 100)
                numero_produto (INT) - Número sequencial do produto na nota
                descricao_produto (VARCHAR, 500) - Descrição do produto/serviço
                codigo_ncm_sh (VARCHAR, 20) - Código NCM/SH do produto
                ncm_sh_tipo_produto (VARCHAR, 255) - Descrição do tipo de produto conforme NCM/SH
                cfop (VARCHAR, 10) - Código Fiscal de Operações e Prestações
                quantidade (DECIMAL, 15,4) - Quantidade do produto
                unidade (VARCHAR, 20) - Unidade de medida
                valor_unitario (DECIMAL, 15,4) - Valor unitário do produto
                valor_total (DECIMAL, 15,2) - Valor total do item
                Relacionamentos: itensnotafiscal.chave_acesso_nf é FK para notasfiscais.chave_acesso.
                6. Comportamento em Caso de Sucesso:
                Se a tarefa for BEM SUCEDIDA (query executada, resultados obtidos via ferramenta), você DEVE retornar a seguinte mensagem de confirmação, seguida pelos resultados:
                "tarefa {agent:"pg_agent", tarefa:"[a tarefa original solicitada]"} concluída."
                Exemplo: tarefa {agent:"pg_agent", tarefa:"listar as 5 notas fiscais mais recentes"} concluída. [Resultado da consulta SQL]
                7. Comportamento em Caso de Falha/Incapacidade:
                Se você NÃO PUDER atender à demanda (ex: query inválida, erro na ferramenta, informação não existe no banco, demanda fora de escopo do DB), você DEVE retornar uma mensagem clara de erro, explicando o motivo da falha.
                NÃO tente adivinhar respostas ou criar dados inexistentes.
                NÃO responda a perguntas que não possam ser resolvidas através de uma consulta ao banco de dados notasfiscais.public.
                Formato para falha:
                "Não foi possível concluir a tarefa {agent:"pg_agent", tarefa:"[a tarefa original solicitada]"}. Motivo: [Explicação clara e concisa da falha]."
                Exemplo: Não foi possível concluir a tarefa {agent:"pg_agent", tarefa:"listar notas fiscais de 2025"}. Motivo: A data solicitada está fora do período de dados disponível no banco de dados.
                Exemplo: Não foi possível concluir a tarefa {agent:"pg_agent", tarefa:"me conte uma piada"}. Motivo: Minha função está restrita a consultas ao banco de dados PostgreSQL.
                """
            )

            main_agent = AssistantAgent(
                "main",
                model_client=self.model_client2,
                description="Responsável por coordenar as atividades dos demais agentes. é o agente que inicia o  fluxo",
                system_message="""
                1. Identidade e Função Exclusiva:
                Você é o único e exclusivo agente main_agent. Sua responsabilidade primária e exclusiva é receber enunciados com tarefas complexas, decompor-las em subtarefas atômicas e delegar-las à sua equipe especializada de agentes. VOCÊ NUNCA POSSUI CAPACIDADE DE EXECUTAR TAREFAS POR SI MESMO; SEU PAPEL É EXCLUSIVAMENTE DE ORQUESTRAÇÃO.
                2. Equipe de Agentes e Suas Funções Exclusivas:
                Sua equipe é composta por agentes com funções estritamente definidas e exclusivas. Você DEVE selecionar o agente mais adequado para cada subtarefa:
                sumarize: Agente exclusivamente responsável por gerar resumos, consolidações ou sínteses de informações. caso não haja mençao em contrário, ele deve ser o agente final do fluxo de trabalho.
                pg_agent: Agente exclusivamente responsável por interagir com o banco de dados PostgreSQL de notas fiscais (executar queries SQL, consultar o schema do banco, recuperar dados, etc.).
                3. Diretrizes para o Fluxo de Trabalho (Regras Inegociáveis):
                1. Decomposição e Delegação (NÃO Execução):
                Sua única ação permitida é decompor a tarefa principal em subtarefas e delegá-las.
                VOCÊ NUNCA DEVE EXECUTAR NENHUMA TAREFA DIRETAMENTE. Sua saída DEVE ser sempre a lista de subtarefas no formato especificado.
                NÃO tente responder a perguntas ou gerar conteúdo que seria responsabilidade de um agente especializado.
                2. Monitoramento e Adaptação:
                Após a delegação, você DEVE monitorar o progresso de cada subtarefa recebendo o feedback dos agentes.
                Em caso de falha, erro, ou necessidade de replanejamento, você DEVE reavaliar a situação e propor uma nova sequência de subtarefas ou uma abordagem alternativa em colaboração com seus agentes, sempre visando a conclusão da tarefa original.
                3. Tratamento de Ambiguidade/Incompletude:
                NÃO tente adivinhar ou prosseguir com informações insuficientes. A clareza é primordial.
                4. Formato de Saída Obrigatório para Subtarefas:
                Cada subtarefa delegada DEVE OBRIGATORIAMENTE seguir o formato EXATO:
                {agent:"[nome_do_agente_mais_adequado]",tarefa:"[descrição_clara_e_concisa_da_tarefa_para_o_agente]"}
                Não inclua texto adicional ou explicações antes ou depois deste formato ao listar as subtarefas.
                5. Condição de Término Absoluta (TERMINATE):
                Você SÓ DEVE emitir a palavra TERMINATE (e apenas essa palavra, sem pontuação ou texto extra) quando TODAS as subtarefas necessárias para a conclusão da tarefa principal foram confirmadamente finalizadas pelos agentes responsáveis.
                """,
            )

            summarize_agent = AssistantAgent(
                "summarize",
                model_client=self.model_client2,
                description="agente de sumarização de conteúdo. Deve ser o o agente final do fluxo de trabalho",
                system_message="""Voce é um agente especializado em sumarizar e resumir conteúdo para o usuário. 
                Tarefas de sumarização designadas a voce devem contar ter o formato de mensagem :
                    {agent:"sumarize",tarefa:"uma tarefa qualquer"}.
                Não crie novas tarefas. Só quem pode fazer isso é o agente main
                Se a tarefa foi bem sucedida avise que ela foi concluida com  a mensagem "tarefa {agent:"sumarize" tarefa:"uma tarefa qualquer"} concluida".
                """,
            )

            try:
                builder = DiGraphBuilder()
                builder.add_node("main", main_agent)
                builder.add_node("pg", pg_agent)
                builder.add_node("summarize", summarize_agent)
                builder.add_node("user", self.user_proxy)

                # Define edges
                builder.add_edge("user", "main")
                builder.add_edge("main", "pg")
                builder.add_edge("main", "summarize")
                builder.add_edge("pg", "summarize")
                builder.add_edge("summarize", "user")

                # Create team
                self.team = GraphFlow(
                    builder.build(),
                    model_client=self.model_client2,
                    termination_condition=termination,
                    allow_repeated_speaker=True
                )
            except Exception as e:
                logger.error(f"Error creating team: {e}")
                raise

            self.initialized = True
            logger.info("Agent manager initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize agent manager: {e}")
            raise

    async def _handle_input_request(self, request_data: Dict[str, Any]):
        """Handle input request from user proxy"""
        if self.input_callback:
            await self.input_callback(request_data)

    def set_input_callback(self, callback: Callable):
        """Set callback for handling input requests"""
        self.input_callback = callback

    def provide_user_input(self, user_input: str):
        """Provide user input to the waiting user proxy"""
        if self.user_proxy:
            self.user_proxy.provide_input(user_input)

    def set_log_callback(self, callback):
        """Define o callback para logs"""
        self.log_callback = callback

    def log(self, message):
        """Registra uma mensagem de log usando o callback se disponível"""
        if self.log_callback:
            self.log_callback(message)
        logger.info(message)

    async def run_task(self, task: str, task_id: str = None):
        """Run a task with the agent team"""
        self.current_task_id = task_id
        
        if not self.initialized or not self.team:
            logger.error("Tentativa de executar task com manager não inicializado.")
            await self.restart_team()
            if not self.initialized or not self.team:
                raise RuntimeError("Manager não pôde ser inicializado.")
        
        logger.info(f"Executando tarefa: {task[:100]}...")
        
        try:
            # Executar sem handler de token tracking - será extraído dos logs depois
            task_result = await self.team.run(task=task)
            
            logger.info(f"Tarefa executada com sucesso!")
            
            # Return result with the conversation for token extraction
            return {
                "result": task_result,
                "messages": task_result if isinstance(task_result, list) else [task_result],
            }
            
        except Exception as e:
            logger.error(f"Erro na execução da task: {e}")
            raise

    async def run_task_stream(self, task: str, task_id: str = None) -> AsyncGenerator[Dict[str, Any], None]:
        """Run a task and stream the results"""
        # Verificação mais robusta da inicialização
        if not self.initialized or not self.team:
            logger.warning(f"Agent manager not properly initialized (initialized={self.initialized}, has_team={self.team is not None})")
            # Tentar reinicializar automaticamente
            try:
                await self.initialize()
                logger.info("Agent manager reinicializado automaticamente para stream")
            except Exception as e:
                logger.error(f"Falha na reinicialização automática: {e}")
                raise RuntimeError("Agent manager not initialized and automatic initialization failed")
        
        self.current_task_id = task_id
        
        try:
            async for message in self.team.run_stream(task=task):
                # Convert message to dict format for JSON serialization
                message_dict = {
                    "type": "message",
                    "source": getattr(message, 'source', 'unknown'),
                    "content": getattr(message, 'content', str(message)),
                    "timestamp": asyncio.get_event_loop().time()
                }
                yield message_dict
                
        except Exception as e:
            logger.error(f"Error streaming task: {e}")
            yield {
                "type": "error",
                "message": str(e),
                "timestamp": asyncio.get_event_loop().time()
            }
        finally:
            self.current_task_id = None

    async def restart_team(self):
        """Reinicia o time de agentes do Autogen de forma robusta."""
        try:
            logger.info("Iniciando restart do team de agentes...")
            
            # Resetar estado interno primeiro
            self.current_task_id = None
            self.total_tokens = 0
            
            # Limpar callbacks
            if self.input_callback:
                self.input_callback = None
            if self.log_callback:
                self.log_callback = None
            
            # Reset do team se existir
            if self.team:
                try:
                    logger.info("Executando reset do team...")
                    await self.team.reset()
                    logger.info("Reset do team concluído")
                except Exception as e:
                    logger.warning(f"Erro no reset do team, ignorando e reinicializando: {e}")
                    # Limpar referências aos agentes apenas se reset falhou
                    self.team = None
                    self.user_proxy = None
                    
                    # Marcar como não inicializado apenas se reset falhou
                    self.initialized = False
                    
                    # Aguardar um momento para garantir limpeza
                    await asyncio.sleep(0.1)
                    
                    # Reinicializar completamente
                    logger.info("Reinicializando team de agentes...")
                    await self.initialize()
            
            logger.info("Restart do team de agentes concluído com sucesso")
            
        except Exception as e:
            logger.error(f"Erro durante restart do team: {e}")
            # Apenas em caso de erro total, marcar como não inicializado e reinicializar
            self.initialized = False
            try:
                await self.initialize()
                logger.info("Reinicialização de recuperação bem-sucedida")
            except Exception as recovery_error:
                logger.error(f"Falha na reinicialização de recuperação: {recovery_error}")
                raise

    async def cleanup(self):
        # Libere recursos se necessário
        pass 