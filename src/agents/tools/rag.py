from langchain_community.vectorstores import SupabaseVectorStore
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain.tools.retriever import create_retriever_tool
from langchain_core.prompts import ChatPromptTemplate
from supabase.client import Client, create_client
from langgraph.graph import MessagesState
from pydantic import BaseModel, Field
from langchain_groq import ChatGroq
from langchain.tools import Tool

from dotenv import load_dotenv
from typing import Literal
import os

from ...load_config import LoadToolsConfig

load_dotenv()

RAG_ROUTER_PROMPT = """
You are an expert at routing a user question to a retriever or web search.
The retriever is for a vectorstore that contains documents related to documentation of TPC-H data stored in Databricks Lakehouse.
Use the retriever for questions on these topics. Otherwise, use web-search for collecting current information.
"""
TOOLS_CFG = LoadToolsConfig()

SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")

def load_supabase_retriever_tool() -> Tool:
    """Creates the supabase document retriever tool"""
    supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
    embeddings = GoogleGenerativeAIEmbeddings(model=TOOLS_CFG.rag_agent_embedding)

    vector_store = SupabaseVectorStore(
        embedding=embeddings,
        client=supabase,
        table_name=TOOLS_CFG.rag_agent_vs_table,
        query_name=TOOLS_CFG.rag_agent_vs_query,
    )
    retriever = vector_store.as_retriever()

    retriever_tool = create_retriever_tool(
        retriever,
        "retrieve_docs",
        "Search and return information from the vector store.",
    )
    return retriever_tool


class RouteQuery(BaseModel):
    """Route a user query to the most relevant datasource."""
    datasource: Literal["retriever", "web_search"] = Field(..., description="Given a user question choose to route it to web search or retriever of a vectorstore.")


def route_question(state: MessagesState):
    """
    Route question to web search or RAG.

    Args:
        state (dict): The current graph state

    Returns:
        str: Next node to call
    """
    print("---ROUTE QUESTION---")
    router_llm = ChatGroq(model=TOOLS_CFG.supervisor_agent_llm, temperature=TOOLS_CFG.supervisor_agent_llm_temperature)
    router_llm = router_llm.with_structured_output(RouteQuery, method="function_calling")

    route_prompt = ChatPromptTemplate.from_messages(
        [
            ("system", RAG_ROUTER_PROMPT),
            ("human", "{question}"),
        ]
    )
    question_router = route_prompt | router_llm
    question = state["messages"][0].content
    source: RouteQuery = question_router.invoke({"question": question})
    if source.datasource == "web_search":
        print("---ROUTE QUESTION TO WEB SEARCH---")
        return "web_search"
    elif source.datasource == "retriever":
        print("---ROUTE QUESTION TO RETRIEVER---")
        return "retriever"

