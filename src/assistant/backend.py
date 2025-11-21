from langchain_core.messages import AnyMessage, HumanMessage, AIMessage, ToolMessage

from typing import List, Generator, AsyncGenerator

from ..agents.backend import pretty_print_messages
from ..load_config import LoadToolsConfig
from ..agents import build_graph


TOOLS_CFG = LoadToolsConfig()

config = {"configurable": {"thread_id": TOOLS_CFG.thread_id}}

class ChatBot:
    """
    A class to handle chatbot interactions by utilizing a pre-defined agent graph. 
    The chatbot processes user messages, generates appropriate responses.
    """
    @staticmethod
    async def get_graph():
        """
        Lazily initialize and cache the async graph.
        """
        graph = await build_graph()
        return graph

    @staticmethod
    async def respond(chatbot: List, message: str) -> AsyncGenerator:
        """
        Processes a user message using the agent graph, generates a response, and appends it to the chat history.
        The chat history is also saved to a memory file for future reference.

        Args:
            chatbot (List): A list representing the chatbot conversation history. Each entry is a tuple of the user message and the bot response.
            message (str): The user message to process.

        Returns:
            Tuple: Returns an empty string (representing the new user input placeholder) and the updated conversation history.
        """
        chatbot.append({
            "role": "user",
            "content": message
        })

        graph = await ChatBot.get_graph()

        events = graph.astream(
            {
                "messages": [("user", message)]
            }, 
            config=config, 
            stream_mode=["messages", "updates"],
            # print_mode="values",
        )

        event: AnyMessage
        # for event in events:
        async for event in events:
            if event[0] == "updates":
                pretty_print_messages(event[1])
            elif event[0] == "messages":
                display = ""
                response: AnyMessage = event[1][0]
                if isinstance(response, AIMessage):
                    display += f"*Agent: `{response.name}`*\n"
                    text = response.content if response.content else response.additional_kwargs.get("reasoning_content", "")
                    display += f"{text}\n"
                elif isinstance(response, ToolMessage):
                    display += f"*Tool: `{response.name}`*\n"
                    text = response.content
                    display += f"{text}\n"
                
                chatbot.append({
                    "role": "assistant",
                    "content": display
                })

            yield "", chatbot
