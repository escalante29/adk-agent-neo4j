from __future__ import annotations

from typing import Dict, List


def semantic_search_candidates(
    natural_language_query: str, top_k: int = 3
) -> Dict[str, object]:
    text = natural_language_query.strip()
    # Simple heuristic stub to propose candidate stored searches or cypher
    candidates: List[Dict[str, object]] = []
    lowered = text.lower()
    if "dispute" in lowered or "disputes" in lowered:
        candidates.append(
            {
                "score": 0.92,
                "query": "credit_disputes_recent",
                "query_id": "stored:credit_disputes_recent",
            }
        )
    if "high risk" in lowered or "risk score" in lowered:
        candidates.append(
            {
                "score": 0.88,
                "query": "MATCH (c:Customer)-[r:HAS_RISK]->(s:Score) WHERE s.value > $min RETURN c,r,s ORDER BY s.value DESC LIMIT 100",
                "query_id": "cypher:high_risk_scores",
            }
        )
    # generic fallback
    candidates.append({"score": 0.5, "query": text, "query_id": "nl:fallback"})
    return {
        "matches": candidates[:top_k],
        "summary": "Generated candidate queries from natural language.",
    }
