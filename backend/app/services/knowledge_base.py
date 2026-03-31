from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from textwrap import shorten


@dataclass
class KnowledgeEntry:
    title: str
    content: str


class KnowledgeBaseService:
    def __init__(self, knowledge_base_path: Path) -> None:
        self.knowledge_base_path = knowledge_base_path
        self.entries = self._load_entries()

    def rebuild_index(self) -> list[KnowledgeEntry]:
        self.entries = self._load_entries()
        return self.entries

    def retrieve(self, query: str, limit: int = 4) -> list[KnowledgeEntry]:
        query_terms = self._normalize(query)
        if not query_terms:
            return []

        scored_entries: list[tuple[int, KnowledgeEntry]] = []
        for entry in self.entries:
            haystack = self._normalize(f"{entry.title} {entry.content}")
            overlap = len(query_terms & haystack)
            if overlap > 0:
                scored_entries.append((overlap, entry))

        scored_entries.sort(key=lambda item: item[0], reverse=True)
        if scored_entries:
            return [entry for _, entry in scored_entries[:limit]]
        return []

    def _load_entries(self) -> list[KnowledgeEntry]:
        text = self.knowledge_base_path.read_text(encoding="utf-8")
        sections = re.split(r"^##\s+", text, flags=re.MULTILINE)
        entries: list[KnowledgeEntry] = []
        for section in sections[1:]:
            lines = [line.rstrip() for line in section.strip().splitlines() if line.strip()]
            if not lines:
                continue
            title = lines[0]
            content = " ".join(lines[1:]).strip()
            if content:
                entries.append(KnowledgeEntry(title=title, content=content))
        return entries

    @staticmethod
    def preview(entry: KnowledgeEntry, width: int = 150) -> str:
        return shorten(entry.content, width=width, placeholder="...")

    @staticmethod
    def _normalize(text: str) -> set[str]:
        return set(re.findall(r"[a-z0-9']+", text.lower()))
