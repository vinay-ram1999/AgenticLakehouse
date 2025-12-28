# AgenticLakehouse: A Multi-Agent System for Databricks

Welcome to the AgenticLakehouse! This project is an agentic application built using **LangGraph** designed to interact directly with your Databricks Workspace. It provides a conversational interface (built with **Gradio**) to query Unity Catalog tables, retrieve information from documents, and browse the web.

The application is built for rapid prototyping and deployment, running seamlessly as a **Databricks App**.

## Architecture

The core of this application is a multi-agent workflow orchestrated by **LangGraph**. A central router agent assesses the user's request and routes it to the most appropriate specialist agent:

* **Databricks Agent (MCP):** Interfaces with Databricks via the project's MCP (Model Control Plane) server. It uses the MCP server to retrieve Unity Catalog schema and table metadata and to execute SQL queries against configured Databricks endpoints. This provides a cleaner, extensible bridge to Databricks functionality (and replaces the previous `spark_sql`-only path when `DATABRICKS_MCP_HOST` is configured).
* **RAG Agent:** Performs Retrieval-Augmented Generation. It sources documents from Unity Catalog Volumes, retrieves relevant chunks from a **Supabase** (PostgreSQL) vector store, and synthesizes an answer. *(Note: This workflow is still a work in progress).*
* **Web Search Agent:** Uses the Tavily API to answer general knowledge or web-based questions.

### MCP Server Integration

This project includes integration with a dedicated MCP (Model Control Plane) server for Databricks. The Databricks agent can be configured to use the MCP server (via the `DATABRICKS_MCP_HOST` environment variable) to retrieve Unity Catalog schema and table metadata and to execute SQL queries. This replaces (or augments) the prior `spark_sql`-only workflow and provides a cleaner, extensible bridge to Databricks capabilities.

- Current capabilities: schema discovery, table metadata retrieval, and SQL query execution via the MCP server.
- Extensible to: MLflow experiments, Jobs monitoring, Unity Catalog administration, and other Databricks REST endpoints as needed.

Databricks MCP: https://github.com/vinay-ram1999/databricks-mcp-server

### Workflow Diagram

<!-- ![Architecture Diagram](images/AgenticLakehouse.png) -->

![Workflow Diagram](images/AgenticLakehouse_workflow.png)


### LangGraph Workflow (As of Now)

The agentic workflow is defined as a graph, with the router acting as the primary conditional entry point.

![LangGraph Router](images/router_agent.png)

## Key Features

* **Databricks Unity Catalog Interaction:** Directly query your UC tables using natural language via Databricks Serverless Compute.
* **RAG on Lakehouse:** Implements a RAG pipeline using documents stored in Unity Catalog Volumes, demonstrating how to keep your data and retrieval sources within the Databricks ecosystem.
* **Flexible LLM Support:** Easily configure the application to use various LLM providers:
    * **Groq API** (fast inference)
    * **Ollama** (using cloud-served models like `gpt-oss:120b-cloud`)
    * Easily adaptable to **OpenAI** or other LangChain-compatible models.
* **Cost-Effective Replication:** This entire stack can be **run for free** using:
    * Databricks Free Edition (or an existing workspace)
    * Supabase Free Tier (as a vector store)
    * Groq Free Tier or Ollama (for local implementation)
    * Langsmith Free Tier (for observability)
* **Rapid Prototyping:** Built with Gradio for a simple UI, perfect for quick iteration and deployment on Databricks Apps.

## Tech Stack

* **Orchestration:** LangGraph
* **Framework:** LangChain
* **Platform:** Databricks (Unity Catalog, Serverless Compute, UC Volumes, Databricks Apps)
* **UI:** Gradio
* **Vector Store:** Supabase (Can be replaced with **Databricks Lakebase**, which is also based on Postgres)
* **LLMs:** Groq (or) Ollama (**OpenAI** can be implemented if API key is available)
* **Web Search:** Tavily
* **Observability:** LangSmith

## Getting Started: Local Setup

You can run the Gradio application locally to test and develop.

### 1. Prerequisites

You will need accounts/access for the following services:
* **Databricks Workspace:** With a Serverless SQL Warehouse set up.
* **Supabase:** A free project for the vector store.
* **Groq:** An API key for LLM access.
* **Tavily:** An API key for web search.
* **LangSmith (Recommended):** An API key for tracing and debugging.

### 2. Clone the Repository

```bash
git clone git@github.com:vinay-ram1999/AgenticLakehouse.git
cd AgenticLakehouse
```

### 3. Set Up Environment Variables

Create a `.env` file in the root of the project and add the following variables:

```bash
# Databricks
DATABRICKS_HOST="https://dbc-xyz.cloud.databricks.com"
DATABRICKS_CLIENT_ID="ed..."
DATABRICKS_CLIENT_SECRET="do..."
DATABRICKS_SERVERLESS_COMPUTE_ID="auto"

UC_CATALOG_NAME="catalog_name..."
UC_SCHEMA_NAME="schema_name..."

# Optional: MCP server endpoint (used by the Databricks agent)
DATABRICKS_MCP_HOST="https://databricks-mcp-server-url.com/mcp"

# LLM Provider (Choose one or both)
GROQ_API_KEY="gsk_..."

# If running Ollama locally
OLLAMA_HOST="http://localhost:11434" 
OLLAMA_PORT="11434"

# Embedding model
GOOGLE_API_KEY="AIz..."

# Supabase (Vector Store)
SUPABASE_URL="https://imbjdwlexwuhdxfqq.supabase.co"
SUPABASE_KEY="sb_secret_..."

# Tool APIs
TAVILY_API_KEY="tvly-..."

# Observability (Recommended)
LANGSMITH_TRACING="true"
LANGSMITH_ENDPOINT="https://api.smith.langchain.com"
LANGSMITH_API_KEY="lsv2_..."
LANGSMITH_PROJECT="AgenticLakehouse (DEV)"
```

### 4. Set Up Supabase
Connect to your Supabase project's SQL editor and run the scripts found in the `supabase/` directory (`DDL_langchain.sql` (Recommended) or `DDL_with_index.sql`) to set up the necessary tables and vector extension.

### 5. Install Dependencies and Run the Apllication
This project uses `uv` for fast package management, but `pip` works as well.

**Using `uv` (Recommended):**

```bash
# Install uv if you don't have it
curl -LsSf https://astral.sh/uv/install.sh | sh

# Sync the virtual environment
uv sync

# Run the Application
uv run main.py
```

**Using `pip`:**

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Run the Application
python main.py
```

The Gradio app will now be running on `http://127.0.0.1:7860`.

## Future Plans

The long-term vision is to create a fully integrated, live "Lakehouse Agent" for the Databricks Workspace.

The MCP server integration described above has been implemented and is now used by the Databricks agent when `DATABRICKS_MCP_HOST` is configured. The MCP server currently provides schema discovery, table metadata retrieval, and SQL query execution.

Next priorities / roadmap:

- **Expose catalog/schema selection in the UI:** let users pick the Unity Catalog `catalog` and `schema` before starting a conversation (similar to Genie).
- **Extend MCP surface:** add endpoints and agent tooling for MLflow (experiments, runs, metrics), Jobs monitoring, Unity Catalog administration, and other Databricks REST features.
- **Add authorization & secure deployment guides:** document recommended auth flows (OAuth/service principals) and production deployment options for the MCP server.
- **Optimize query performance:** introduce caching and query planning improvements; evaluate dedicated compute for high-throughput use-cases.
- **Observability & testing:** expand LangSmith tracing examples, add end-to-end tests for MCP endpoints, and include CI checks for the agent workflows.
- **Docs & examples:** provide a short MCP server README, example requests, and a small Postman/HTTP collection for people to test the MCP API locally.

If you'd like, I can add a short example showing how to set `DATABRICKS_MCP_HOST` locally, or replace the placeholder MCP repo link with your repo URL.

## Databricks App Demo (Spark SQL Agent Version)

- Query: List all tables available to query
![list_tables](images/list_tables.png)

- Query: List the top 3 nations based on the total number of customers from that nation.
![query2](images/query2.png)

- Query: Give me the weather forecast for Detroit, MI for this week in Celsius
![weather](images/web_search.png)

- LangSmith Tracing:
![langsmith](images/langsmith.png)

- Supabase Vector Store:
![supabase](images/supabase.png) 
