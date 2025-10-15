from __future__ import annotations

from typing import Any, Dict

from agent.neo4j_client import get_neo4j_client
from agent.memory import MemoryEntry, get_memory_backend, switch_memory_backend, now_iso
from agent.semantic import semantic_search_candidates


def neo4j_search(input: Dict[str, Any]) -> Dict[str, Any]:
    cypher = str(input.get("cypher", ""))
    params = dict(input.get("params", {}))
    client = get_neo4j_client()
    return client.run_query(cypher, params=params)


def semantic_search(input: Dict[str, Any]) -> Dict[str, Any]:
    nlq = str(input.get("natural_language_query", ""))
    top_k = int(input.get("top_k", 3))
    return semantic_search_candidates(nlq, top_k)


def fastapi_single_search_mcp(input: Dict[str, Any]) -> Dict[str, Any]:
    # Bridge placeholder; assumes existing FastAPI function by name
    search_name = str(input.get("search_name", ""))
    params = dict(input.get("params", {}))
    # Stubbed response to satisfy tool contract
    return {"result": {"search": search_name, "params": params}, "api_status": 200}


def memory_save(input: Dict[str, Any]) -> Dict[str, Any]:
    session_id = str(input.get("session_id"))
    turn = int(input.get("turn"))
    user = str(input.get("user"))
    assistant = str(input.get("assistant"))
    metadata = dict(input.get("metadata", {}))
    backend = get_memory_backend()
    # Save both user and assistant turns for audit
    user_entry = MemoryEntry(
        session_id=session_id,
        turn=turn * 2 - 1,
        speaker="user",
        text=user,
        timestamp=now_iso(),
        metadata=metadata,
    )
    assistant_entry = MemoryEntry(
        session_id=session_id,
        turn=turn * 2,
        speaker="assistant",
        text=assistant,
        timestamp=now_iso(),
        metadata=metadata,
    )
    user_id = backend.save(user_entry)
    assistant_id = backend.save(assistant_entry)
    return {"ok": True, "entry_id": assistant_id or user_id}


def memory_query(input: Dict[str, Any]) -> Dict[str, Any]:
    session_id = str(input.get("session_id"))
    query = str(input.get("query", ""))
    limit = int(input.get("limit", 20))
    backend = get_memory_backend()
    matches = backend.query(session_id, query, limit)
    return {"matches": matches}


def memory_switch(input: Dict[str, Any]) -> Dict[str, Any]:
    backend = str(input.get("backend"))
    connection = dict(input.get("connection", {}))
    return switch_memory_backend(backend, connection)
