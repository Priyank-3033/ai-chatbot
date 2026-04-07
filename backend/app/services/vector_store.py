from __future__ import annotations

import json
import math
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from uuid import uuid4

from app.core.config import Settings


class VectorStoreService:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.db_path = settings.vector_store_path / "vectors.sqlite3"

    @contextmanager
    def connect(self):
        connection = sqlite3.connect(self.db_path)
        connection.row_factory = sqlite3.Row
        try:
            yield connection
            connection.commit()
        finally:
            connection.close()

    def ensure_storage(self) -> None:
        Path(self.settings.vector_store_path).mkdir(parents=True, exist_ok=True)
        with self.connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS document_vectors (
                    id TEXT PRIMARY KEY,
                    document_id TEXT NOT NULL,
                    user_id INTEGER NOT NULL,
                    document_name TEXT NOT NULL,
                    source_type TEXT NOT NULL,
                    content_type TEXT NOT NULL,
                    page_number INTEGER,
                    chunk_index INTEGER NOT NULL,
                    chunk_text TEXT NOT NULL,
                    embedding_json TEXT NOT NULL,
                    metadata_json TEXT NOT NULL,
                    created_at TEXT NOT NULL
                )
                """
            )

    def add_document_chunks(
        self,
        *,
        document_id: str,
        user_id: int,
        document_name: str,
        source_type: str,
        content_type: str,
        chunks: list[str],
        embeddings: list[list[float]],
    ) -> None:
        if not chunks or not embeddings:
            return
        with self.connect() as connection:
            for index, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
                connection.execute(
                    """
                    INSERT INTO document_vectors (
                        id, document_id, user_id, document_name, source_type, content_type, page_number, chunk_index, chunk_text, embedding_json, metadata_json, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now'))
                    """,
                    (
                        f"{document_id}:{index}:{uuid4().hex[:8]}",
                        document_id,
                        user_id,
                        document_name,
                        source_type,
                        content_type,
                        None,
                        index,
                        chunk,
                        json.dumps(embedding),
                        json.dumps(
                            {
                                "source": source_type,
                                "content_type": content_type,
                                "chunk_index": index,
                            }
                        ),
                    ),
                )

    def delete_document(self, document_id: str) -> None:
        with self.connect() as connection:
            connection.execute("DELETE FROM document_vectors WHERE document_id = ?", (document_id,))

    def search(
        self,
        *,
        user_id: int,
        query_embedding: list[float],
        limit: int = 5,
        min_score: float = 0.18,
    ) -> list[dict[str, str]]:
        with self.connect() as connection:
            rows = connection.execute(
                """
                SELECT document_id, document_name, source_type, content_type, page_number, chunk_text, embedding_json, metadata_json
                FROM document_vectors
                WHERE user_id = ?
                """,
                (user_id,),
            ).fetchall()

        scored: list[tuple[float, dict[str, str]]] = []
        for row in rows:
            embedding = json.loads(row["embedding_json"])
            score = self._cosine_similarity(query_embedding, embedding)
            if score >= min_score:
                scored.append(
                    (
                        score,
                        {
                            "name": row["document_name"],
                            "snippet": row["chunk_text"],
                            "document_id": row["document_id"],
                            "source_type": row["source_type"],
                            "content_type": row["content_type"],
                            "page_number": row["page_number"],
                            "score": score,
                            "metadata": json.loads(row["metadata_json"] or "{}"),
                            "distance": 1 - score,
                        },
                    )
                )
        scored.sort(key=lambda item: item[0], reverse=True)
        return [item for _, item in scored[:limit]]

    @staticmethod
    def _cosine_similarity(left: list[float], right: list[float]) -> float:
        if not left or not right or len(left) != len(right):
            return 0.0
        dot = sum(a * b for a, b in zip(left, right))
        left_norm = math.sqrt(sum(a * a for a in left))
        right_norm = math.sqrt(sum(b * b for b in right))
        if left_norm == 0 or right_norm == 0:
            return 0.0
        return dot / (left_norm * right_norm)
