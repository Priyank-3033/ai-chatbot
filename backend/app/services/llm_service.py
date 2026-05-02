from __future__ import annotations

from collections.abc import Iterator

from app.services.answer_validator import AnswerValidator
from app.services.ai_service import AIService


class LLMService:
    def __init__(self, ai_service: AIService) -> None:
        self.ai_service = ai_service
        self.answer_validator = AnswerValidator()

    @staticmethod
    def _trim_history(history: list[dict[str, str]], limit: int = 6) -> list[dict[str, str]]:
        trimmed = []
        for item in history[-limit:]:
            role = str(item.get("role", "user"))
            content = str(item.get("content", "")).strip()
            if role in {"user", "assistant", "system"} and content:
                trimmed.append({"role": role, "content": content})
        return trimmed

    def generate(
        self,
        *,
        question: str,
        history: list[dict[str, str]],
        mode: str,
        model: str,
        system_prompt: str,
        context: dict[str, list],
    ) -> str | None:
        answer = self.ai_service.generate_answer(
            question=question,
            history=self._trim_history(history),
            mode=mode,
            model=model,
            custom_prompt=system_prompt,
            entries=context.get("entries", []),
            products=context.get("products", []),
            document_matches=context.get("documents", []),
        )
        return self.answer_validator.validate(answer=answer, intent=context.get("intent", "general"), mode=mode, context=context)

    def generate_stream(
        self,
        *,
        question: str,
        history: list[dict[str, str]],
        mode: str,
        model: str,
        system_prompt: str,
        context: dict[str, list],
    ) -> Iterator[str]:
        return self.ai_service.generate_answer_stream(
            question=question,
            history=self._trim_history(history),
            mode=mode,
            model=model,
            custom_prompt=system_prompt,
            entries=context.get("entries", []),
            products=context.get("products", []),
            document_matches=context.get("documents", []),
        )


__all__ = ["LLMService"]
