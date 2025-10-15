# adk-agent-neo4j

Minimal ADK-based agent for exploring a Neo4j knowledge graph with MCP tools, Vertex/Gemini model via Google ADK, and switchable memory backends (Postgres or Firestore).

## Prerequisites

- Python 3.11.2
- `pip install -r requirements.txt`

## Environment

Set the following environment variables:

```
GOOGLE_APPLICATION_CREDENTIALS=/path/to/service_account.json
GEMINI_MODEL=gemini-2.5-flash-lite
ADK_PROJECT_ID=<gcp-project>

NEO4J_URI=neo4j+s://<host>:7687
NEO4J_USER=<user>
NEO4J_PASSWORD=<password>

MEMORY_BACKEND=postgres|firestore
# If postgres:
POSTGRES_DSN=postgresql://user:pass@host:5432/db
# If firestore:
FIRESTORE_PROJECT=<gcp-project>
```

## Run (local dev)

```
python -m agent.main
```

The agent registers MCP tools:

- `neo4j_search` {cypher, params} → {records, summary, query_id}
- `semantic_search` {natural_language_query, top_k} → {matches, summary}
- `fastapi_single_search_mcp` {search_name, params} → {result, api_status}
- `memory_save` {session_id, turn, user, assistant, metadata} → {ok, entry_id}
- `memory_query` {session_id, query, limit} → {matches}
- `memory_switch` {backend, connection} → {ok, backend}

Notes:

- Tool calls and query IDs are logged for audit; do not log raw PII.
- PII should be redacted at the application layer when returning results.
