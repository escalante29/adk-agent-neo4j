from __future__ import annotations

import os
from typing import Any, Dict, List, Optional

from neo4j import GraphDatabase, Driver


class Neo4jClient:
    """Lightweight wrapper around the official Neo4j Python driver.

    Provides a single convenience method to execute parameterized Cypher and
    return a simplified structure expected by the MCP tool `neo4j_search`.
    """

    def __init__(
        self,
        uri: Optional[str] = None,
        user: Optional[str] = None,
        password: Optional[str] = None,
    ) -> None:
        self._uri = uri or os.getenv("NEO4J_URI")
        self._user = user or os.getenv("NEO4J_USER")
        self._password = password or os.getenv("NEO4J_PASSWORD")
        if not self._uri or not self._user or not self._password:
            raise ValueError("NEO4J_URI, NEO4J_USER, and NEO4J_PASSWORD must be set")
        self._driver: Driver = GraphDatabase.driver(
            self._uri, auth=(self._user, self._password)
        )

    def close(self) -> None:
        self._driver.close()

    def run_query(
        self, cypher: str, params: Optional[Dict[str, Any]] = None, limit: int = 100
    ) -> Dict[str, Any]:
        """Execute a parameterized Cypher query and return simplified results.

        Returns a dict: {"records": List[Dict], "summary": str, "query_id": str}
        """
        parameters = params or {}
        with self._driver.session() as session:
            result = session.run(cypher, parameters=parameters)
            # Collect top records up to limit
            records: List[Dict[str, Any]] = []
            for idx, record in enumerate(result):
                if idx >= limit:
                    break
                # Convert to plain dict
                records.append(record.data())

            summary_obj = result.consume()
            query_id = getattr(summary_obj, "query_id", None) or getattr(
                summary_obj, "query", None
            )
            summary = f"{summary_obj.counters}"
            return {"records": records, "summary": summary, "query_id": str(query_id)}


_neo4j_singleton: Optional[Neo4jClient] = None


def get_neo4j_client() -> Neo4jClient:
    global _neo4j_singleton
    if _neo4j_singleton is None:
        _neo4j_singleton = Neo4jClient()
    return _neo4j_singleton
