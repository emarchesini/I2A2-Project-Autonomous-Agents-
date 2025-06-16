
import asyncio
from autogen_agentchat.agents import AssistantAgent,UserProxyAgent
from autogen_agentchat.base import TaskResult
from autogen_agentchat.conditions import ExternalTermination, TextMentionTermination
from autogen_agentchat.teams import Swarm
from autogen_agentchat.ui import Console
from autogen_core import CancellationToken
from autogen_ext.models.ollama import OllamaChatCompletionClient
from autogen_ext.tools.mcp import StdioServerParams, mcp_server_tools
from autogen_agentchat.ui import Console
from autogen_agentchat.conditions import MaxMessageTermination, TextMentionTermination
from autogen_agentchat.teams import SelectorGroupChat
from autogen_agentchat.messages import HandoffMessage



puppeteeer_mcp_server_params = StdioServerParams(
        command="docker", args=[ "run", "-i", "--rm", "--init", "-e", "DOCKER_CONTAINER=true", "mcp/puppeteer"]
)

filesystem_mcp_server_params = StdioServerParams(
        command="docker", args=[ "run","-i","--rm","--mount",
                                 "type=bind,src=/home/enzo/dev/autogen/fs,dst=/data",
                                 "mcp/filesystem",
                                 "/data"]
    )

fetch_mcp_server_params = StdioServerParams(
        command="uvx", args=[ "mcp-server-fetch"]
)


homemade_scrapper_mcp_server_params = StdioServerParams(
        command="python", args=[ "tools/scrapper_homemade_scrapper.py"]
)





# Create an OpenAI model client.
model_client = OllamaChatCompletionClient(
    model="qwen2.5:72b-instruct-q3_K_S",
    #model="llama3.3:70b-instruct-q3_K_M",
    #model="qwq:32b-q4_K_M",
    #model="mistral-small:22b-instruct-2409-q8_0",
    host="192.168.0.126:11434",
    #model_info={"function_calling":True,"json_output":True,"vision":False},
    options= {
    #"seed": random.randint(0, 1000000)
  })


async def ainput(prompt: str) -> str:
    """Async version of input."""
    loop = asyncio.get_event_loop()
    user_input = await loop.run_in_executor(None, lambda: input(prompt))
    return user_input

# Use `asyncio.run(...)` when running in a script.
async def main() -> None:

    filesystem_tools = await mcp_server_tools(filesystem_mcp_server_params)
    puppeteer_tools = await mcp_server_tools(homemade_scrapper_mcp_server_params)



    fs_agent = AssistantAgent(
        name="file_manager",
        model_client=model_client,
        tools=filesystem_tools,  # type: ignorels
        handoffs=["summarize","scrapper"],
        description="Agente responsavel pela manipulação de arquivos no filesystem",
        system_message="""Voce é um agente especializado na manipulação dos arquivos do usuário. 
        A não ser que o usuário diga o contrário assuma o caminho default dos arquivos como /data
        se voce precisar de informações extras para cumprir sua tarefa primeiro envie sua mensagem o que voce precisa e em seguida faça o handoff para o user_proxy
        em caso de qualquer problema faca uma mensagem relatando o erro e faca o handoff para o user_proxy
        Se a tarefa foi bem sucedida avise que ela foi concluida com  a mensagem "tarefa {agent:"file_manager" tarefa:"uma tarefa qualquer"} concluida
        Quando a solicitação do usuário estiver integralmente concluida responda com TERMINATE.
        ".
        """
    )

    scrapper_agent = AssistantAgent(
        name="scrapper",
        model_client=model_client,
        handoffs=["summarize", "file_manager"],
        tools=puppeteer_tools,  # type: ignorels
        description="Agente responsável por recuperar informações de páginas web via scrapping",
        system_message="""Voce é um assistente especializado em recuperar informações de páginas web via scrapping.
        se o pedido inicial do usuario foi vago envie uma mensagem com sua dúvida e faca o handoff para o user_proxy. sua atividade deve envolver apenas informacoes textuais do site.
        se voce precisar de informações para cumprir sua tarefa envie uma mensagem com a sua necessidade e em seguida faça o handoff para o agente user_proxy
        """
    )

    
    #main_agent = AssistantAgent(
    #"main",
    #model_client=model_client,
    #description="Responsável por coordenar as atividades dos demais agentes. é o agente que inicia o  fluxo",
    #handoffs=["summarize", "user_proxy","scrapper","file_manager"],
    #system_message="""Voce é um assistente capaz coordenar tarefas complexas com um time de agentes inteligentes.

    
    # Os agentes a sua disposição são :

    #- scrapper: responsável por recuperar informações de uma página web atravez de web scraping

    #- file_manager: capaz de fazer operações no sistema de arquivos do usuário

    #- sumarize: Agente que sumariza informações

    #- user_proxy: se voce precisar esclarecer dúvidas dos outros agentes e não tiver informações para faze-lo primeiro envie a mensagem com o seu pedido e  em seguida faça o handoff para user_proxy

    # Quando o pedido do usuario for atendido pela acao conjunta dos agentes responda com TERMINATE. 
    # Não mencione TERMINATE de forma alguma antes de ter todo o conjunto de tarefas for finalizado""",
    #)

    summarize_agent = AssistantAgent(
    "summarize",
    model_client=model_client,
    handoffs=["scrapper","file_manager"],
    description="agente de sumarização de conteúdo",
    system_message="""Voce é um agente especializado em sumarizar e resumir conteúdo para o usuário. 
    se voce precisar de informações para cumprir sua tarefa primeiro envie sua mensagem o que voce precisa e em seguida faça o handoff para o user_proxy
    Por favor mantenha os resumos a um tamanho máximo de 200 palavras.
    Se a tarefa foi bem sucedida avise que ela foi concluida com  a mensagem "tarefa {agent:"sumarize" tarefa:"uma tarefa qualquer"} concluida".
    """,
    )

    user_proxy = UserProxyAgent("user_proxy", 
                                description="Agente responsável por interagir com o usuário sempre que um agente não souber o que fazer",
                                
                        )

    # Define a termination condition that stops the task if the critic approves.
    text_mention_termination = TextMentionTermination("TERMINATE")
    max_messages_termination = MaxMessageTermination(max_messages=300)
    termination = text_mention_termination | max_messages_termination

    team = Swarm([fs_agent,scrapper_agent,summarize_agent,user_proxy],termination_condition=termination)

    

    task = "recupere a url dentro do arquivo url.txt, faca um scrapping do conteudo da url, sumarize,e salve o conteudo sumarizado no arquivo resumo.txt"


    
    task_result = await Console(team.run_stream(task=task))
    last_message = task_result.messages[-1]

    
    while isinstance(last_message, HandoffMessage) and last_message.target == "user_proxy":
        user_message = input("User: ")

        task_result = await Console(
            team.run_stream(task=HandoffMessage(source="user_proxy", target=last_message.source, content=user_message))
        )
        last_message = task_result.messages[-1]



#    await run_team_stream()
#    await model_client.close()
    #await Console(team.run_stream(task="Faça o scrapping da página https://rnp.br, resuma seu conteúdo e salve o resultado no arquivo rnp.txt"))
    
    #result = await team.run(task="Faça o scrapping da página https://rnp.br, resuma seu conteúdo e salve o resultado no arquivo rnp.txt")
    #print(" -- Mensagens -- ")
    #for message in result.messages:
    #    print(f"\nAutor: {message.source}")
    #    print(f"Mensagem: {message.content}")

if __name__ == "__main__":
    asyncio.run(main())