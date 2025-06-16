
import asyncio
from autogen_agentchat.agents import AssistantAgent,UserProxyAgent
from autogen_agentchat.base import TaskResult
from autogen_agentchat.conditions import ExternalTermination, TextMentionTermination
from autogen_agentchat.teams import RoundRobinGroupChat
from autogen_agentchat.ui import Console
from autogen_core import CancellationToken
from autogen_ext.models.ollama import OllamaChatCompletionClient
from autogen_ext.tools.mcp import StdioServerParams, mcp_server_tools
from autogen_agentchat.ui import Console
from autogen_agentchat.conditions import MaxMessageTermination, TextMentionTermination
from autogen_agentchat.teams import SelectorGroupChat
import logging

from autogen_core import TRACE_LOGGER_NAME

logging.basicConfig(level=logging.WARNING)
logger = logging.getLogger(TRACE_LOGGER_NAME)
logger.addHandler(logging.StreamHandler())
logger.setLevel(logging.DEBUG)



postgres_mcp_server_params = StdioServerParams(
        command="docker", args=[ "run", "-i", "--rm", "--add-host=host.docker.internal:host-gateway", "mcp/postgres", "postgresql://pguser:teste123@host.docker.internal:55432/rnp"]
)

filesystem_mcp_server_params = StdioServerParams(
        command="docker", args=[ "run","-i","--rm","--mount",
                                 "type=bind,src=/home/enzo/dev/autogen/fs,dst=/data",
                                 "mcp/filesystem",
                                 "/data"]
)

anon_mcp_server_params = StdioServerParams(
        command="python", args=[ "tools/simple_anon_mcp.py"]
)


# Create an OpenAI model client.
model_client = OllamaChatCompletionClient(
    #model="qwen2.5:72b-instruct-q3_K_S",
    #model="llama3.3:70b-instruct-q3_K_M",
    #model="qwq:32b-q4_K_M",
    model="mistral-small3.1:24b-instruct-2503-q8_0",
    #host="192.168.0.126:11434",
    host="192.168.0.120:11434",
    model_info={"function_calling":True,"json_output":True,"vision":False,"family":"unknown"},
    options= {
    #"seed": random.randint(0, 1000000)
  })




# Use `asyncio.run(...)` when running in a script.
async def main() -> None:

    filesystem_tools = await mcp_server_tools(filesystem_mcp_server_params)
    anon_tools = await mcp_server_tools(anon_mcp_server_params)
    postgres_tools = await mcp_server_tools(postgres_mcp_server_params)



    fs_agent = AssistantAgent(
        name="file_manager",
        model_client=model_client,
        tools=filesystem_tools,  # type: ignorels
        description="Agente responsavel pela manipulação de arquivos no filesystem",
        system_message="""Voce é um agente especializado na manipulação dos arquivos do usuário. 
        A não ser que o usuário diga o contrário assuma o caminho default dos arquivos como /data
        tarefas manipulação do filesystem designadas a voce devem  ter o formato de mensagem :
        {agent:"file_manager",tarefa:"uma tarefa qualquer"}
        Não crie novas tarefas. Só quem pode fazer isso é o agente main
        Se a tarefa foi bem sucedida avise que ela foi concluida com  a mensagem "tarefa {agent:"file_manager" tarefa:"uma tarefa qualquer"} concluida".
        """
    )

    pg_agent = AssistantAgent(
        name="pg_agent",
        #reflect_on_tool_use=True,
        model_client=model_client,
        tools=postgres_tools,  # type: ignorels
        description="Agente responsavel pela recuperação de dados e metadados em bancos de dados postgres",
        system_message="""Voce é um assistente especializado em recuperar informações do banco de dados postgres da empresa. 
        Tarefas relacionadas a banco de dados endereçadas a voce normalmente tem o formato de mensagem : 
        {agent:"pg_agent",tarefa:"uma tarefa qualquer"}
        diretrizes:

        - voce tema capacidade de executar queries sql, consultar o schema do banco de dados e retornar os resultados solicitados por meio do uso de ferramentas.
        - as consultas dos usuários também podem ser feitas via linguagem natural.
        - o usuário também pode solicitar metadados de tabelas, como o nome das colunas e os tipos de dados.
        - caso não seja explicitamente mencionado o banco de dados a ser consultado é o notasfiscais e o esquema é public.
        - caso uma tentativa de consulta apresente erro, faça uma consulta ao schema das tabelas envolvidas para entender se os campos utilizados estão os corretos.
        - os resultados retornados sempre devem ser obtidos a partir de uma chamada bem sucedida a sua ferramenta de consulta ao banco.
        
        Não crie novas tarefas. Só quem pode fazer isso é o agente main
        Se a tarefa foi bem sucedida avise que ela foi concluida com  a mensagem "tarefa {agent:"pg_agent" tarefa:"uma tarefa qualquer"} concluida".


        A seguir temos o dicionario de dado banco de notas fiscais:

        ## Visão Geral
        Este banco de dados foi projetado para armazenar informações de Notas Fiscais Eletrônicas (NF-e) brasileiras, incluindo dados do cabeçalho das notas e seus respectivos itens.

        ## Estrutura do Banco

        ### Tabela: `notasfiscais`
        **Descrição:** Armazena as informações principais (cabeçalho) de cada nota fiscal eletrônica.

        | Campo | Tipo | Tamanho | Nulo | Chave | Descrição |
        |-------|------|---------|------|-------|-----------|
        | `chave_acesso` | VARCHAR | 44 | NÃO | PK | Chave de acesso única da NF-e (44 dígitos) |
        | `numero_nf` | VARCHAR | 9 | SIM | - | Número sequencial da nota fiscal |
        | `serie_nf` | VARCHAR | 3 | SIM | - | Série da nota fiscal |
        | `data_emissao` | DATE | - | SIM | - | Data de emissão da nota fiscal |
        | `data_entrada_saida` | DATE | - | SIM | - | Data de entrada ou saída da mercadoria |
        | `cnpj_emitente` | VARCHAR | 14 | SIM | - | CNPJ da empresa emitente (apenas números) |
        | `nome_emitente` | VARCHAR | 255 | SIM | - | Razão social da empresa emitente |
        | `uf_emitente` | CHAR | 2 | SIM | - | Unidade Federativa do emitente |
        | `cnpj_destinatario` | VARCHAR | 14 | SIM | - | CNPJ da empresa destinatária (apenas números) |
        | `nome_destinatario` | VARCHAR | 255 | SIM | - | Razão social da empresa destinatária |
        | `uf_destinatario` | CHAR | 2 | SIM | - | Unidade Federativa do destinatário |
        | `valor_total_nf` | DECIMAL | 15,2 | SIM | - | Valor total da nota fiscal |
        | `valor_produtos` | DECIMAL | 15,2 | SIM | - | Valor total dos produtos/serviços |
        | `valor_frete` | DECIMAL | 15,2 | SIM | - | Valor do frete |
        | `valor_seguro` | DECIMAL | 15,2 | SIM | - | Valor do seguro |
        | `valor_desconto` | DECIMAL | 15,2 | SIM | - | Valor total de descontos |
        | `valor_outras_despesas` | DECIMAL | 15,2 | SIM | - | Valor de outras despesas acessórias |
        | `valor_icms` | DECIMAL | 15,2 | SIM | - | Valor total do ICMS |
        | `valor_icms_st` | DECIMAL | 15,2 | SIM | - | Valor total do ICMS Substituição Tributária |
        | `valor_ipi` | DECIMAL | 15,2 | SIM | - | Valor total do IPI |
        | `valor_pis` | DECIMAL | 15,2 | SIM | - | Valor total do PIS |
        | `valor_cofins` | DECIMAL | 15,2 | SIM | - | Valor total da COFINS |
        | `informacoes_complementares` | TEXT | - | SIM | - | Informações complementares da nota fiscal |

        ### Tabela: `itensnotafiscal`
        **Descrição:** Armazena os itens/produtos de cada nota fiscal eletrônica.

        | Campo | Tipo | Tamanho | Nulo | Chave | Descrição |
        |-------|------|---------|------|-------|-----------|
        | `id_item_nf` | SERIAL | - | NÃO | PK | Identificador único do item (auto incremento) |
        | `chave_acesso_nf` | VARCHAR | 44 | NÃO | FK | Chave de acesso da nota fiscal (referência) |
        | `numero_item` | INT | - | SIM | - | Número sequencial do item na nota |
        | `codigo_produto` | VARCHAR | 60 | SIM | - | Código do produto/serviço |
        | `descricao_produto` | VARCHAR | 255 | SIM | - | Descrição do produto/serviço |
        | `ncm` | VARCHAR | 8 | SIM | - | Código NCM (Nomenclatura Comum do Mercosul) |
        | `cfop` | VARCHAR | 4 | SIM | - | Código Fiscal de Operações e Prestações |
        | `unidade_comercial` | VARCHAR | 6 | SIM | - | Unidade de medida comercial (ex: UN, KG, M) |
        | `quantidade_comercial` | DECIMAL | 15,4 | SIM | - | Quantidade comercializada |
        | `valor_unitario_comercial` | DECIMAL | 15,4 | SIM | - | Valor unitário do produto |
        | `valor_bruto_produto` | DECIMAL | 15,2 | SIM | - | Valor bruto do produto (qtd × valor unitário) |
        | `valor_desconto_item` | DECIMAL | 15,2 | SIM | - | Valor de desconto aplicado ao item |
        | `valor_total_item` | DECIMAL | 15,2 | SIM | - | Valor total do item (bruto - desconto) |
        | `base_calculo_icms` | DECIMAL | 15,2 | SIM | - | Base de cálculo do ICMS |
        | `aliquota_icms` | DECIMAL | 5,2 | SIM | - | Alíquota do ICMS (%) |
        | `valor_icms_item` | DECIMAL | 15,2 | SIM | - | Valor do ICMS do item |
        | `base_calculo_ipi` | DECIMAL | 15,2 | SIM | - | Base de cálculo do IPI |
        | `aliquota_ipi` | DECIMAL | 5,2 | SIM | - | Alíquota do IPI (%) |
        | `valor_ipi_item` | DECIMAL | 15,2 | SIM | - | Valor do IPI do item |

        ## Relacionamentos

        ### 1:N - Nota Fiscal → Itens
        - **Tabela Pai:** `notasfiscais`
        - **Tabela Filha:** `itensnotafiscal`
        - **Chave Estrangeira:** `chave_acesso_nf` → `chave_acesso`
        - **Descrição:** Uma nota fiscal pode ter vários itens, mas cada item pertence a apenas uma nota fiscal
        - **Integridade:** `ON DELETE CASCADE` - ao excluir uma nota fiscal, todos os seus itens são excluídos automaticamente

        ## Índices Recomendados

        ### Índices Primários (já existentes)
        - `notasfiscais.chave_acesso` (PRIMARY KEY)
        - `itensnotafiscal.id_item_nf` (PRIMARY KEY)

        ### Índices Secundários Sugeridos
        ```sql
        -- Para consultas por emitente
        CREATE INDEX idx_notasfiscais_cnpj_emitente ON notasfiscais(cnpj_emitente);

        -- Para consultas por destinatário
        CREATE INDEX idx_notasfiscais_cnpj_destinatario ON notasfiscais(cnpj_destinatario);

        -- Para consultas por data
        CREATE INDEX idx_notasfiscais_data_emissao ON notasfiscais(data_emissao);

        -- Para consultas por UF
        CREATE INDEX idx_notasfiscais_uf_emitente ON notasfiscais(uf_emitente);
        CREATE INDEX idx_notasfiscais_uf_destinatario ON notasfiscais(uf_destinatario);

        -- Para consultas de itens por produto
        CREATE INDEX idx_itens_codigo_produto ON itensnotafiscal(codigo_produto);
        CREATE INDEX idx_itens_ncm ON itensnotafiscal(ncm);
        CREATE INDEX idx_itens_cfop ON itensnotafiscal(cfop);
        ```

        ## Regras de Negócio

        1. **Chave de Acesso:** Deve ser única e ter exatamente 44 caracteres
        2. **CNPJ:** Armazenado apenas com números (14 dígitos)
        3. **Valores Monetários:** Precisão de 2 casas decimais para valores em reais
        4. **Quantidades:** Precisão de 4 casas decimais para permitir frações
        5. **Alíquotas:** Precisão de 2 casas decimais para percentuais
        6. **Datas:** Formato DATE (YYYY-MM-DD)

        ## Observações Técnicas

        - **Encoding:** UTF-8 para suporte a caracteres especiais
        - **Separador CSV:** Ponto e vírgula (;)
        - **Separador Decimal:** Vírgula (,) nos CSVs, convertido para ponto (.) no banco
        - **Tratamento de Nulos:** Campos opcionais permitem NULL, com valores padrão 0 para campos numéricos
        - **Integridade Referencial:** Garantida através de chave estrangeira com CASCADE DELETE

        ## Consultas Comuns

        ### Resumo por Emitente
        ```sql
        SELECT 
            cnpj_emitente,
            nome_emitente,
            COUNT(*) as total_notas,
            SUM(valor_total_nf) as valor_total
        FROM notasfiscais 
        GROUP BY cnpj_emitente, nome_emitente
        ORDER BY valor_total DESC;
        ```

        ### Itens por Nota Fiscal
        ```sql
        SELECT 
            nf.numero_nf,
            nf.serie_nf,
            nf.nome_emitente,
            i.descricao_produto,
            i.quantidade_comercial,
            i.valor_total_item
        FROM notasfiscais nf
        JOIN itensnotafiscal i ON nf.chave_acesso = i.chave_acesso_nf
        WHERE nf.chave_acesso = 'CHAVE_ESPECIFICA';
        ```

        ### Análise por Período
        ```sql
        SELECT 
            DATE_TRUNC('month', data_emissao) as mes,
            COUNT(*) as total_notas,
            SUM(valor_total_nf) as faturamento_total
        FROM notasfiscais 
        WHERE data_emissao BETWEEN '2024-01-01' AND '2024-12-31'
        GROUP BY DATE_TRUNC('month', data_emissao)
        ORDER BY mes;
        ```


        """
    )


    anon_agent = AssistantAgent(
        name="anon_agent",
        model_client=model_client,
        #reflect_on_tool_use=True,
        description="Agente responsavel pela anonimização de dados e informações sensíveis",
        system_message="""Voce é um assistente especializado em anonimizar informações sensíveis, sejam elas de pessoas ou negociais. 
        Tarefas endereçadas a voce normalmente tem o formato de mensagem : 
        {agent:"anon_agent",tarefa:"uma tarefa qualquer"}

        Não crie novas tarefas. Só quem pode fazer isso é o agente main.
        Se a tarefa foi bem sucedida avise que ela foi concluida com  a mensagem "tarefa {agent:"anon_agent" tarefa:"uma tarefa qualquer"} concluida".
        
        Procedimento de anonimização:
        - procure por nomes de pessoas, endereços, números de telefone, e-mails e outras informações quem permitam identificar um individuo. no texto enviado para anonimização.
        - substitua essas informações por marcadores genéricos, como "NOME<numero da ocorrencia>", "ENDEREÇO<numero da ocorrencia>", "TELEFONE<numero da ocorrencia>" e "EMAIL<numero da ocorrencia>@<dominio do e-mail original>". 

        """
    )

    # - anon_agent : anonimiza informações sensíveis sejam elas de pessoais ou negociais. nunca retorne informações sensíveis sem anonimização para os usuários

    main_agent = AssistantAgent(
    "main",
    model_client=model_client,
    description="Responsável por coordenar as atividades dos demais agentes. é o agente que inicia o  fluxo",
    system_message="""Voce é um assistente capaz receber enunciados 
    com tarefas complexas e dividi-las em subtarefas mais simples que
    , serão executadas por uma equipe de agentes inteligentes.

    
     Os agentes a sua disposição são :

    - pg_agent : responsável por recuperar informações de um banco de dados postgres

    - file_manager: capaz de fazer operações no sistema de arquivos do usuário

    - anon_agent : anonimiza informações sensíveis sejam elas de pessoais ou negociais.     
    
    
    Diretrizes para o fluxo de trabalho:
   
    - NUNCA retorne informações sensíveis sem o devido processo de anonimização ! Só considere o processo finalizado depois que o agente anon_agent confirmar que os dados foram anonimizados
    
    - Não execute as tarefas ! Só liste necessárias e observe o progresso da mesmas por parte dos outros agentes. Em caso de problemas replaneje e tente novas abordagens junto aos seus agentes.
    
    - Ao descrever uma tarefa sempre faça no formato: 

    {agent:"agente que você julga ser mais adequado para atender a tarefa",tarefa:"descrição da tarefa"}

     Quando o conjunto de tarefas for finalizado pelos agentes  responda com TERMINATE. 

    - Não mencione TERMINATE de forma alguma antes de ter todo o conjunto de tarefas for finalizado""",
    )
    #- anon_agent : anonimiza informações sensíveis sejam elas de pessoais ou negociais. 
     
     #- NUNCA retorne informações sensíveis sem o devido processo de anonimização ! Só considere o processo finalizado depois que o agente anon_agent confirmar que os dados foram anonimizados
    
    #user_proxy = UserProxyAgent("user_proxy", input_func=input)

    # Define a termination condition that stops the task if the critic approves.
    text_mention_termination = TextMentionTermination("TERMINATE")
    max_messages_termination = MaxMessageTermination(max_messages=25)
    termination = text_mention_termination | max_messages_termination

    
    
    selector_prompt = """Select an agent to perform task.

                        {roles}

                        Current conversation context:
                        {history}

                        Read the above conversation, then select an agent from {participants} to perform the next task.
                        Make sure the planner agent has assigned tasks before other agents start working.
                        Only select one agent.
                      """
    
    # no selector group chat quem seleciona o proximo interlocutor é um modelo de llm baseado na funcao declarada dos agentes e no selector prompt
    team = SelectorGroupChat(
    [main_agent,pg_agent,fs_agent,anon_agent],#anon_agent,
    model_client=model_client,
    termination_condition=termination,
    selector_prompt=selector_prompt,
    allow_repeated_speaker=True,  # Allow an agent to speak multiple turns in a row.
)
    
    
    #await Console(team.run_stream(task="Faça o scrapping da página https://rnp.br, resuma seu conteúdo e salve o resultado no arquivo rnp.txt"))
    #await Console(team.run_stream(task="recupere os dados dos funcionarios com os maiores salários de cada uma das áreas da empresa, salve o resultado no arquivo rel_dados.txt"))
    
    #result = await team.run(task="Faça o scrapping da página https://rnp.br, resuma seu conteúdo e salve o resultado no arquivo rnp.txt")
    #print(" -- Mensagens -- ")
    #for message in result.messages:
    #    print(f"\nAutor: {message.source}")
    #    print(f"Mensagem: {message.content}")

if __name__ == "__main__":
    asyncio.run(main())