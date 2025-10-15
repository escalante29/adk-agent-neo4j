from __future__ import annotations

import os
from typing import Any, Dict

from adk import Agent, Tool
from google import genai as google_genai  # type: ignore

from agent.tools import mcp_tools


def build_agent() -> Agent:
    model = os.getenv("GEMINI_MODEL", "gemini-2.5-flash-lite")
    # ADK Agent with Vertex/Gemini preferences
    agent = Agent(model=model)

    # Register MCP tools with exact names/signatures
    agent.register_tool(
        Tool(
            name="neo4j_search",
            description="Run parameterized Cypher against Neo4j",
            input_schema={"cypher": "str", "params": "dict"},
            output_schema={"records": "list", "summary": "str", "query_id": "str"},
            handler=lambda input: mcp_tools.neo4j_search(input),
        )
    )
    agent.register_tool(
        Tool(
            name="semantic_search",
            description="Generate candidate stored searches or Cypher from NLQ",
            input_schema={"natural_language_query": "str", "top_k": "int"},
            output_schema={"matches": "list", "summary": "str"},
            handler=lambda input: mcp_tools.semantic_search(input),
        )
    )
    agent.register_tool(
        Tool(
            name="fastapi_single_search_mcp",
            description="Bridge to existing FastAPI single-search by name",
            input_schema={"search_name": "str", "params": "dict"},
            output_schema={"result": "dict", "api_status": "int"},
            handler=lambda input: mcp_tools.fastapi_single_search_mcp(input),
        )
    )
    agent.register_tool(
        Tool(
            name="memory_save",
            description="Persist one user+assistant turn to memory",
            input_schema={
                "session_id": "str",
                "turn": "int",
                "user": "str",
                "assistant": "str",
                "metadata": "dict",
            },
            output_schema={"ok": "bool", "entry_id": "str"},
            handler=lambda input: mcp_tools.memory_save(input),
        )
    )
    agent.register_tool(
        Tool(
            name="memory_query",
            description="Query conversation memory for a session",
            input_schema={"session_id": "str", "query": "str", "limit": "int"},
            output_schema={"matches": "list"},
            handler=lambda input: mcp_tools.memory_query(input),
        )
    )
    agent.register_tool(
        Tool(
            name="memory_switch",
            description="Switch memory backend and optionally migrate",
            input_schema={"backend": "str", "connection": "dict"},
            output_schema={"ok": "bool", "backend": "str"},
            handler=lambda input: mcp_tools.memory_switch(input),
        )
    )
    return agent


def main() -> None:
    # Ensure Vertex/Gemini auth present for ADK
    if not os.getenv("GOOGLE_APPLICATION_CREDENTIALS"):
        raise EnvironmentError(
            "GOOGLE_APPLICATION_CREDENTIALS must be set for Vertex/ADK"
        )
    agent = build_agent()
    # Run local dev server; ADK binds to configured port (default 8080)
    agent.serve()


if __name__ == "__main__":
    main()
