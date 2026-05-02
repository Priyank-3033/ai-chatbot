from __future__ import annotations

import re


class AnswerValidator:
    SUPPORT_FALLBACK = "I don?t have enough information to answer that accurately."

    def validate(self, *, answer: str | None, intent: str, mode: str, context: dict[str, list]) -> str | None:
        text = (answer or "").strip()
        if not text:
            return None

        if mode == "support" or intent == "support":
            has_support_context = bool(context.get("entries") or context.get("documents"))
            if not has_support_context:
                return self.SUPPORT_FALLBACK
            if self._looks_like_guess(text):
                return self.SUPPORT_FALLBACK

        if intent == "product" and not context.get("products") and self._looks_like_concrete_recommendation(text):
            return "Tell me your budget and what matters most, like camera, gaming, battery, or display, and I will suggest the best product."

        return text

    @staticmethod
    def _looks_like_guess(text: str) -> bool:
        lowered = text.lower()
        risky_phrases = ["usually", "generally", "typically", "most likely", "probably", "in most cases"]
        return any(phrase in lowered for phrase in risky_phrases)

    @staticmethod
    def _looks_like_concrete_recommendation(text: str) -> bool:
        lowered = text.lower()
        return bool(re.search(r"\brs\s?\d", lowered) or any(term in lowered for term in ["i recommend", "best option", "top pick"]))


__all__ = ["AnswerValidator"]
