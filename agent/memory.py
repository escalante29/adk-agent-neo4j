from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import psycopg
from google.cloud import firestore


@dataclass
class MemoryEntry:
    session_id: str
    turn: int
    speaker: str
    text: str
    timestamp: str
    metadata: Dict[str, Any]


class MemoryBackend:
    def save(self, entry: MemoryEntry) -> str:
        raise NotImplementedError

    def query(self, session_id: str, query: str, limit: int) -> List[Dict[str, Any]]:
        raise NotImplementedError


class PostgresMemory(MemoryBackend):
    def __init__(self, dsn: Optional[str] = None) -> None:
        self._dsn = dsn or os.getenv("POSTGRES_DSN")
        if not self._dsn:
            raise ValueError("POSTGRES_DSN must be set for Postgres memory backend")
        self._ensure_schema()

    def _ensure_schema(self) -> None:
        create_sql = """
            CREATE TABLE IF NOT EXISTS conversation_memory (
                session_id TEXT NOT NULL,
                turn INT NOT NULL,
                speaker TEXT NOT NULL,
                text TEXT NOT NULL,
                timestamp TIMESTAMPTZ NOT NULL,
                metadata JSONB NOT NULL,
                PRIMARY KEY(session_id, turn)
            );
            CREATE INDEX IF NOT EXISTS idx_session_turn ON conversation_memory(session_id, turn);
            """
        with psycopg.connect(self._dsn) as conn:
            with conn.cursor() as cur:
                cur.execute(create_sql)
                conn.commit()

    def save(self, entry: MemoryEntry) -> str:
        insert_sql = """
            INSERT INTO conversation_memory (session_id, turn, speaker, text, timestamp, metadata)
            VALUES (%s, %s, %s, %s, %s, %s)
            ON CONFLICT (session_id, turn) DO UPDATE SET
                speaker = EXCLUDED.speaker,
                text = EXCLUDED.text,
                timestamp = EXCLUDED.timestamp,
                metadata = EXCLUDED.metadata
            """
        with psycopg.connect(self._dsn) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    insert_sql,
                    (
                        entry.session_id,
                        entry.turn,
                        entry.speaker,
                        entry.text,
                        datetime.fromisoformat(entry.timestamp),
                        entry.metadata,
                    ),
                )
                conn.commit()
        return f"pg:{entry.session_id}:{entry.turn}"

    def query(self, session_id: str, query: str, limit: int) -> List[Dict[str, Any]]:
        select_sql = """
            SELECT turn, speaker, text, timestamp, metadata
            FROM conversation_memory
            WHERE session_id = %s AND (text ILIKE %s OR speaker ILIKE %s)
            ORDER BY turn DESC
            LIMIT %s
            """
        like = f"%{query}%"
        with psycopg.connect(self._dsn) as conn:
            with conn.cursor() as cur:
                cur.execute(select_sql, (session_id, like, like, limit))
                rows = cur.fetchall()
        matches: List[Dict[str, Any]] = []
        for row in rows:
            turn, speaker, text, ts, metadata = row
            matches.append(
                {
                    "turn": int(turn),
                    "text": str(text),
                    "timestamp": ts.isoformat(),
                }
            )
        return matches


class FirestoreMemory(MemoryBackend):
    def __init__(self, project: Optional[str] = None) -> None:
        self._project = project or os.getenv("FIRESTORE_PROJECT")
        if not self._project:
            raise ValueError(
                "FIRESTORE_PROJECT must be set for Firestore memory backend"
            )
        self._client = firestore.Client(project=self._project)
        self._collection = self._client.collection("conversation_memory")

    def save(self, entry: MemoryEntry) -> str:
        doc_id = f"{entry.session_id}:{entry.turn}"
        self._collection.document(doc_id).set(
            {
                "session_id": entry.session_id,
                "turn": entry.turn,
                "speaker": entry.speaker,
                "text": entry.text,
                "timestamp": entry.timestamp,
                "metadata": entry.metadata,
            }
        )
        return f"fs:{doc_id}"

    def query(self, session_id: str, query: str, limit: int) -> List[Dict[str, Any]]:
        # Firestore doesn't support full-text; perform prefix/contains via client-side filter after fetching by session
        docs = (
            self._collection.where("session_id", "==", session_id)
            .order_by("turn", direction=firestore.Query.DESCENDING)
            .limit(limit * 2)
            .stream()
        )
        matches: List[Dict[str, Any]] = []
        q = query.lower()
        for doc in docs:
            data = doc.to_dict()
            if (
                q in str(data.get("text", "")).lower()
                or q in str(data.get("speaker", "")).lower()
            ):
                matches.append(
                    {
                        "turn": int(data.get("turn", 0)),
                        "text": str(data.get("text", "")),
                        "timestamp": str(data.get("timestamp", "")),
                    }
                )
                if len(matches) >= limit:
                    break
        return matches


_memory_backend: Optional[MemoryBackend] = None


def get_memory_backend() -> MemoryBackend:
    global _memory_backend
    if _memory_backend is None:
        backend = os.getenv("MEMORY_BACKEND", "postgres").lower()
        if backend == "postgres":
            _memory_backend = PostgresMemory()
        elif backend == "firestore":
            _memory_backend = FirestoreMemory()
        else:
            raise ValueError("MEMORY_BACKEND must be 'postgres' or 'firestore'")
    return _memory_backend


def switch_memory_backend(
    target_backend: str, connection: Dict[str, Any]
) -> Dict[str, Any]:
    global _memory_backend
    target = target_backend.lower()
    if target == "postgres":
        dsn = connection.get("dsn") or os.getenv("POSTGRES_DSN")
        os.environ["MEMORY_BACKEND"] = "postgres"
        if dsn:
            os.environ["POSTGRES_DSN"] = dsn
        _memory_backend = PostgresMemory(dsn=dsn)
        return {"ok": True, "backend": "postgres"}
    if target == "firestore":
        project = connection.get("project") or os.getenv("FIRESTORE_PROJECT")
        os.environ["MEMORY_BACKEND"] = "firestore"
        if project:
            os.environ["FIRESTORE_PROJECT"] = project
        _memory_backend = FirestoreMemory(project=project)
        return {"ok": True, "backend": "firestore"}
    return {"ok": False, "backend": target}


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()
