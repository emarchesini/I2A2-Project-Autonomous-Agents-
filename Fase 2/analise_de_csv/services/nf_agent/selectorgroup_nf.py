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



#puppeteeer_mcp_server_params = StdioServerParams(
#        command="docker", args=[ "run", "-i", "--rm", "--init", "-e", "DOCKER_CONTAINER=true", "mcp/puppeteer"]
#)

filesystem_mcp_server_params = StdioServerParams(
        command="docker", args=[ "run","-i","--rm","--mount",
                                 "type=bind,src=/home/enzo/dev/autogen/fs,dst=/data",
                                 "mcp/filesystem",
                                 "/data"]
    )



homemade_scrapper_mcp_server_params = StdioServerParams(
        command="python", args=[ "tools/scrapper_homemade_scrapper.py"]
)


# Create an OpenAI model client.
model_client = OllamaChatCompletionClient(
    #model="qwen2.5:72b-instruct-q3_K_S",
    model="mistral-small3.1:24b-instruct-2503-q8_0",
    #model="llama3.3:70b-instruct-q3_K_M",
    #model="qwq:32b-q4_K_M",
    #model="mistral-small:22b-instruct-2409-q8_0",
    #host="192.168.0.126:11434",
    host="192.168.0.120:11434",
    model_info={"function_calling":True,"json_output":True,"vision":False,"family":"unknown"},
    options= {
    #"seed": random.randint(0, 1000000)
  })




# Use `asyncio.run(...)` when running in a script.
async def main() -> None:

    filesystem_tools = await mcp_server_tools(filesystem_mcp_server_params)
    scrapping_tools = await mcp_server_tools(homemade_scrapper_mcp_server_params)

    # Criar o UserProxyAgent para permitir input do usuário
    user_proxy = UserProxyAgent(
        name="user_proxy",
        description="Representa o usuário e inicia as conversas com pedidos",
        system_message="""Você representa o usuário no sistema. 
        Sua função é iniciar conversas transmitindo os pedidos do usuário para o agente main.
        Após transmitir o pedido inicial, observe o progresso dos agentes e só intervenha se necessário."""
    )

    fs_agent = AssistantAgent(
        name="file_manager",
        model_client=model_client,
        tools=filesystem_tools,  # type: ignorels
        description="Agente especializado na criação, edição e deleção de arquivos no filesystem do local",
        system_message="""Voce é um agente especializado na criação, edição e deleção de arquivos no filesystem local através de chamadas as ferramentas disponibilizadas a voce 
        A não ser que o usuário diga o contrário sempre assuma como caminho default dos arquivos a pasta /data
        tarefas designadas a voce devem ter obrigatoriamente o seguinte formato de mensagem :
        {agent:"file_manager",tarefa:"uma tarefa qualquer"}
        Não crie novas tarefas. Só execute as que voce receber.
        Não execute tarefas que não estejam estritamente relacionadas a sua função.
        Se a tarefa foi bem sucedida avise que ela foi concluida com  a mensagem "tarefa {agent:"file_manager" tarefa:"uma tarefa qualquer"} concluida".
        """
    )

    scrapper_agent = AssistantAgent(
        name="scrapper",
        model_client=model_client,
        tools=scrapping_tools,  # type: ignorels
        description="Agente responsável por recuperar informações de páginas web via scrapping",
        system_message="""Voce é um assistente especializado em recuperar informações de páginas web 
        scrapping. tarefas de scrapping designadas a voce devem contar ter o formato de mensagem :
        {agent:"scrapper",tarefa:"uma tarefa qualquer"}
        Ignore os historicos de mensagem a dizendo que outros agentes não conseguiram o web scrapping. 
        voce é capaz de faze-lo, então tente de qualquer maneira !
        Não crie novas tarefas. Só quem pode fazer isso é o agente main
        Se a tarefa foi bem sucedida avise que ela foi concluida com  a mensagem "tarefa {agent:"scrapper" tarefa:"uma tarefa qualquer"} concluida".
        """
    )

    
    main_agent = AssistantAgent(
    "main",
    model_client=model_client,
    description="Responsável por coordenar as atividades dos demais agentes. é o agente que inicia o  fluxo",
    system_message="""Voce é um assistente capaz receber enunciados 
    com tarefas complexas e dividi-las em subtarefas mais simples que
    , serão executadas por uma equipe de agentes inteligentes.

    
     Os agentes a sua disposição são :

    - scrapper: responsável por recuperar informações de uma página web atravez de web scraping

    - file_manager: capaz de fazer operações no sistema de arquivos do usuário

    - sumarize: Agente que sumariza informações 

    
    Não execute as tarefas ! Só liste as subtarefas necessárias e observe
     o progresso da mesmas por parte dos outros agentes. Em caso de problemas replaneje e tente novas abordagens junto aos seus agentes.
    Ao descrever uma sub tarefa sempre faça no formato: 


    {agent:"agente que você julga ser mais adequado para atender a tarefa",tarefa:"descrição da tarefa"}

     Quando o conjunto de subtarefas for finalizado pelos agentes  responda com TERMINATE. 
     Não mencione TERMINATE em hipótese alguma antes de ter todo o conjunto de tarefas for finalizado""",
    )

    summarize_agent = AssistantAgent(
    "summarize",
    model_client=model_client,
    description="agente de sumarização de conteúdo",
    system_message="""Voce é um agente especializado em sumarizar e resumir conteúdo para o usuário. 
    Tarefas de sumarização designadas a voce devem contar ter o formato de mensagem :
        {agent:"sumarize",tarefa:"uma tarefa qualquer"}.
    Não crie novas tarefas. Só quem pode fazer isso é o agente main
    Por favor mantenha os resumos a um tamanho máximo de 200 palavras.
    Se a tarefa foi bem sucedida avise que ela foi concluida com  a mensagem "tarefa {agent:"sumarize" tarefa:"uma tarefa qualquer"} concluida".
    """,
    )

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
                        The user_proxy should only speak at the beginning to provide the initial request.
                        Only select one agent.
                      """
    
    # Incluir o user_proxy no grupo de agentes
    team = SelectorGroupChat(
    [user_proxy, main_agent, scrapper_agent, summarize_agent, fs_agent],
    model_client=model_client,
    termination_condition=termination,
    selector_prompt=selector_prompt,
    allow_repeated_speaker=False,  # Allow an agent to speak multiple turns in a row.
)
    
    # Usar Console para permitir interação do usuário
    print("=== Sistema de Agentes Autogen ===")
    print("Digite sua solicitação para os agentes:")
    print("Exemplo: 'Faça o scrapping da página https://www.fee.unicamp.br/sobre-a-feec, resuma seu conteúdo e salve este resumo no arquivo feec.txt'")
    print("=" * 50)
    
    await Console(team.run_stream())

if __name__ == "__main__":
    asyncio.run(main())