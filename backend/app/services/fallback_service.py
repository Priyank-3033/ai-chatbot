from __future__ import annotations


class FallbackService:
    def __init__(self, chatbot_service) -> None:
        self.chatbot_service = chatbot_service

    def handle(
        self,
        *,
        intent: str,
        question: str,
        normalized: str,
        mode: str,
        history: list[dict[str, str]],
        context: dict[str, list],
    ) -> str:
        entries = context.get("entries", [])
        products = context.get("products", [])
        documents = context.get("documents", [])

        if documents and any(term in normalized for term in ["pdf", "document", "file", "notes", "uploaded"]):
            top = documents[0]
            return self.chatbot_service._format_answer(
                f"Your uploaded file suggests: {top['snippet'][:160]}",
                f"I matched your question against the uploaded document `{top['name']}` and used the closest text I found there.",
                "Ask a more specific question from the file if you want a sharper answer."
            )

        math_answer = self.chatbot_service._simple_math_answer(question.strip())
        if math_answer is not None:
            return math_answer

        if mode == "support" or intent == "support":
            if "help" in normalized and len(normalized.split()) <= 4:
                return (
                    "Of course. I can help with refunds, billing, login issues, order updates, shipping, and account access.\n\n"
                    "Tell me your issue in one sentence, for example:\n"
                    "- I forgot my password\n"
                    "- My OTP is not working\n"
                    "- I want a refund\n"
                    "- I need to update my order"
                )
            if not entries:
                if self.chatbot_service._is_support_question(normalized):
                    return "I don?t have enough information to answer that accurately."
                return "I can only help with support-related questions."
            return self.chatbot_service._build_support_fallback(entries, normalized)

        if intent == "product":
            return self.chatbot_service._build_product_fallback(question, normalized, products)

        if intent == "coding":
            return self.chatbot_service._build_coding_fallback(normalized)

        return self.chatbot_service._build_general_rich_fallback(
            question,
            normalized,
            self.chatbot_service._recent_user_context(history),
        )


__all__ = ["FallbackService"]
