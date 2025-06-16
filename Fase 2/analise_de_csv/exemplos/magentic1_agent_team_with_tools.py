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
from autogen_agentchat.teams import MagenticOneGroupChat
from autogen_agentchat.ui import Console
from autogen_ext.agents.web_surfer import MultimodalWebSurfer
from autogen_ext.agents.file_surfer import FileSurfer
from autogen_ext.agents.magentic_one import MagenticOneCoderAgent
from autogen_agentchat.agents import CodeExecutorAgent
from autogen_ext.code_executors.local import LocalCommandLineCodeExecutor


#puppeteeer_mcp_server_params = StdioServerParams(
#        command="docker", args=[ "run", "-i", "--rm", "--init", "-e", "DOCKER_CONTAINER=true", "mcp/puppeteer"]
#)

#filesystem_mcp_server_params = StdioServerParams(
#        command="docker", args=[ "run","-i","--rm","--mount",
#                                 "type=bind,src=/home/enzo/dev/autogen/fs,dst=/data",
#                                 "mcp/filesystem",
#                                 "/data"]
#    )

#fetch_mcp_server_params = StdioServerParams(
#        command="uvx", args=[ "mcp-server-fetch"]
#)

# Create an OpenAI model client.
model_client = OllamaChatCompletionClient(

    model="qwen3:32b-q8_0",# qwen2.5:32b-instruct-q8_0
    model_info={"function_calling":True,"json_output":True,"vision":False,  "family":"unknown"},
    options= {
  })




# Use `asyncio.run(...)` when running in a script.
async def main() -> None:

    
    
    websurfer = MultimodalWebSurfer(
        "WebSurfer",
        model_client=model_client,
    )

    

    #terminal_agent = CodeExecutorAgent("ComputerTerminal",description="Agente responsável por executar comandos no terminal",
    #                                   code_executor=LocalCommandLineCodeExecutor())
    #coder = MagenticOneCoderAgent("Coder",description="Agente responsável por escrever e corrigir código",
    #                              model_client=model_client)
    #file_surfer = FileSurfer("file_surfer",description="Agente responsável por manipular arquivos no sistema de arquivos",
    #                          model_client=model_client)


    team = MagenticOneGroupChat([websurfer], model_client=model_client) #file_surfer, fs_agent,summarize_agent websurfer coder,terminal_agent,
    await Console(team.run_stream(task="Faça um resumo do que se trata a bitnet na microsoft e como ela funciona"))

    

if __name__ == "__main__":
    asyncio.run(main())