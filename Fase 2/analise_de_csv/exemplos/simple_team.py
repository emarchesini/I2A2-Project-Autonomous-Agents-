import asyncio
from autogen_agentchat.agents import AssistantAgent
from autogen_agentchat.base import TaskResult
from autogen_agentchat.conditions import ExternalTermination, TextMentionTermination
from autogen_agentchat.teams import RoundRobinGroupChat
from autogen_agentchat.ui import Console
from autogen_core import CancellationToken
from autogen_ext.models.ollama import OllamaChatCompletionClient



# Create an OpenAI model client.
model_client = OllamaChatCompletionClient(
    model="qwen2.5:72b-instruct-q3_K_S",
    #host="192.168.0.126:11434",
    options= {
    #"seed": random.randint(0, 1000000)
  })

# Create the primary agent.
poet_agent = AssistantAgent(
    "poet",
    model_client=model_client,
    system_message="Você é um assistente de IA útil, especializado em criar poemas. Reúna sugestões para melhorar sua escrita e as incorpore no seu trabalho. Quando estiver satisfeito com os feedbacks, responda com APPROVE",
)

# Create the critic agent.
critic_agent = AssistantAgent(
    "critic",
    model_client=model_client,
    system_message="Forneça feedback construtivo.",
)

# Define a termination condition that stops the task if the critic approves.
text_termination = TextMentionTermination("APPROVE")

# Create a team with the primary and critic agents.
team = RoundRobinGroupChat([poet_agent, critic_agent], termination_condition=text_termination)


# Use `asyncio.run(...)` when running in a script.
async def main() -> None:
        await Console(team.run_stream(task="Escreva um pequeno poema sobre a chegada do outono."))

#    result = await team.run(task="Escreva um pequeno poema sobre a chegada do outono.")
#    print(" -- Mensagens -- ")
#    for message in result.messages:
#        print(f"\nAutor: {message.source}")
#        print(f"Mensagem: {message.content}")

if __name__ == "__main__":
    asyncio.run(main())