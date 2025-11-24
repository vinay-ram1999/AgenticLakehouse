from langgraph.graph import StateGraph, MessagesState, START, END
from langgraph_supervisor.supervisor import _make_call_agent
from langgraph_supervisor.handoff import create_handoff_tool
from langgraph.prebuilt import create_react_agent, ToolNode
from langchain_core.prompts import ChatPromptTemplate
from langgraph.graph.state import CompiledStateGraph
from langgraph.checkpoint.memory import MemorySaver
from langchain_ollama.chat_models import ChatOllama
from langgraph.errors import GraphRecursionError
from langchain_core.messages import AnyMessage
from langchain_groq import ChatGroq
from mcp.client.streamable_http import streamablehttp_client
from langchain_mcp_adapters.prompts import load_mcp_prompt
from langchain_mcp_adapters.tools import load_mcp_tools
from mcp import ClientSession

import os

from ..prompts.web_search import SYSTEM_PROMPT as WEB_SEARCH_SYS_PROMPT
from ..prompts.spark_sql import SYSTEM_PROMPT as SPARK_SQL_SYS_PROMPT
from ..prompts.router import SYSTEM_PROMPT as ROUTER_PROMPT
from .tools.spark_sql import get_spark_sql_tools, SparkSQLResponse
from .tools.tavily_search import load_tavily_search_tool
from .tools.rag import load_supabase_retriever_tool
from ..load_config import LoadToolsConfig
from .utils import plot_agent_schema

TOOLS_CFG = LoadToolsConfig()

CATALOG = os.environ.get("UC_CATALOG_NAME", "tpch")
SCHEMA = os.environ.get("UC_SCHEMA_NAME", "bronze")
DATABRICKS_MCP_HOST = os.environ.get("DATABRICKS_MCP_HOST")


async def build_graph() -> CompiledStateGraph:
    """Builds a graph with multi-agent supervisor architecture"""
    async with streamablehttp_client(DATABRICKS_MCP_HOST) as (read, write, _):
        async with ClientSession(read, write) as session:
            await session.initialize()

            web_search_agent_llm = ChatGroq(model=TOOLS_CFG.web_search_agent_llm, temperature=TOOLS_CFG.web_search_agent_llm_temperature)
            # web_search_agent_llm = ChatOllama(model="gpt-oss:120b-cloud", temperature=TOOLS_CFG.web_search_agent_llm_temperature) #NOTE local dev only
            search_tool = load_tavily_search_tool(TOOLS_CFG.tavily_search_max_results)

            web_search_agent_prompt = ChatPromptTemplate([
                    ("system", WEB_SEARCH_SYS_PROMPT),
                    ("placeholder", "{messages}"),
                    ("placeholder", "{agent_scratchpad}"),
            ])

            web_search_agent = create_react_agent(
                model=web_search_agent_llm, 
                tools=[search_tool], 
                prompt=web_search_agent_prompt, 
                name=TOOLS_CFG.web_search_agent_name
            )

            spark_sql_agent_llm = ChatGroq(model=TOOLS_CFG.spark_sql_agent_llm, temperature=TOOLS_CFG.spark_sql_agent_llm_temperature)
            # spark_sql_agent_llm = ChatOllama(model="gpt-oss:120b-cloud", temperature=TOOLS_CFG.spark_sql_agent_llm_temperature) #NOTE local dev only
            
            # spark_sql_tools = get_spark_sql_tools(spark_sql_agent_llm) + [SparkSQLResponse]
            spark_sql_tools = await load_mcp_tools(session, server_name="databricks_mcp_server")

            spark_sql_agent_prompt = ChatPromptTemplate([
                    ("system", SPARK_SQL_SYS_PROMPT.format(**{"CATALOG_NAME": CATALOG, "SCHEMA_NAME": SCHEMA})),
                    ("placeholder", "{messages}"),
                    ("placeholder", "{agent_scratchpad}"),
            ])

            spark_sql_agent = create_react_agent(
                model=spark_sql_agent_llm, 
                tools=spark_sql_tools, 
                prompt=spark_sql_agent_prompt, 
                name=TOOLS_CFG.spark_sql_agent_name
            )

            router_llm = ChatGroq(model=TOOLS_CFG.router_agent_llm, temperature=TOOLS_CFG.router_agent_llm_temperature)
            # router_llm = ChatOllama(model="gpt-oss:120b-cloud", temperature=TOOLS_CFG.router_agent_llm_temperature) #NOTE local dev only
            retriever_tool = load_supabase_retriever_tool()

            agents = [spark_sql_agent, web_search_agent]
            agent_names = [agent.name for agent in agents]
            
            handoff_tools = [
                create_handoff_tool(
                    agent_name=agent_name,
                    add_handoff_messages=False
                )
                for agent_name in agent_names
            ]
            tool_node = ToolNode(handoff_tools)

            router_agent = create_react_agent(
                model=router_llm,
                tools=tool_node,
                prompt=ROUTER_PROMPT,
                name=TOOLS_CFG.router_agent_name,
            )

            builder = StateGraph(MessagesState)
            builder.add_node(router_agent, destinations=tuple(agent_names) + (END,))
            builder.add_edge(START, router_agent.name)
            for agent in agents:
                builder.add_node(
                    agent.name,
                    _make_call_agent(
                        agent,
                        "full_history", #NOTE "full_history" or "last_message"
                        add_handoff_back_messages=False,
                        supervisor_name=router_agent.name,
                    ),
                )
                builder.add_edge(agent.name, END)

            memory = MemorySaver()
            graph = builder.compile(checkpointer=memory)
            
            plot_agent_schema(graph, "router_agent")
            return graph
