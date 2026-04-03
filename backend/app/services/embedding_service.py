from __future__ import annotations

import hashlib
import math
import re

from openai import OpenAI

from app.core.config import Settings


class EmbeddingService:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self._client = OpenAI(api_key=settings.openai_api_key) if settings.openai_api_key else None

    def embed(self, text: str) -> list[float]:
        if self._client:
            response = self._client.embeddings.create(
                model=self.settings.embedding_model_name,
                input=text,
            )
            return response.data[0].embedding
        return self._local_hash_embedding(text)

    def embed_many(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        if self._client:
            response = self._client.embeddings.create(
                model=self.settings.embedding_model_name,
                input=texts,
            )
            return [item.embedding for item in response.data]
        return [self._local_hash_embedding(text) for text in texts]

    @staticmethod
    def _local_hash_embedding(text: str, dimensions: int = 256) -> list[float]:
        vector = [0.0] * dimensions
        tokens = re.findall(r"[a-z0-9']+", text.lower())
        if not tokens:
            return vector
        for token in tokens:
            digest = hashlib.sha256(token.encode("utf-8")).digest()
            index = int.from_bytes(digest[:4], "big") % dimensions
            sign = 1.0 if digest[4] % 2 == 0 else -1.0
            vector[index] += sign
        norm = math.sqrt(sum(value * value for value in vector))
        if norm > 0:
            vector = [value / norm for value in vector]
        return vector
