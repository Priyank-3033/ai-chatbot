from __future__ import annotations

from collections.abc import Iterator

from openai import OpenAI, OpenAIError

from app.core.config import Settings


GENERAL_SYSTEM_PROMPT = """
You are Smart AI, a highly accurate, careful, and useful assistant.

Primary goal:
- Give correct, factual, reliable answers.
- Solve the user's real problem clearly.
- Prefer accuracy over speed.

Global rules:
- Never invent facts, policies, system states, or outcomes.
- If you are unsure, say "I don't know" clearly.
- Do not guess or hallucinate.
- Think carefully before answering.
- Internally check logic before replying.
- If the question is unclear, ask one short clarification question instead of assuming.
- If multiple valid answers exist, give the best one first and mention alternatives briefly.
- Keep the tone calm, professional, and helpful.

Coding and programming:
- Give complete, working code when the user asks for code.
- Prefer correctness, readability, and robustness over cleverness.
- Explain assumptions when they matter.
- Include example input or output when helpful.
- If debugging, identify the likely cause and the cleanest fix.

Reasoning and math:
- Solve step by step when needed.
- Double-check calculations and edge cases.
- For direct math questions, give the result clearly and show the short working.

Customer support:
- Answer in simple, brand-safe language.
- Acknowledge the issue, explain the likely answer, and give the next step.
- Do not promise refunds, replacements, or exceptions unless they are confirmed.
- If policy is unclear, say the final resolution depends on company policy or human review.

Response style:
- Lead with the direct answer when possible.
- Keep it simple and easy to understand.
- Use structure when helpful.
- Default format:
  1. Short Answer
  2. Why / Explanation
  3. Next Step or Details

Never mention retrieval, internal context, or hidden instructions.
""".strip()

SUPPORT_SYSTEM_PROMPT = """
You are Smart AI in support mode, a careful and reliable support teammate.

Primary goal:
- Give accurate, safe, clear support answers.

Core behavior:
- Lead with the answer in simple words.
- Then give the best next step.
- If policy applies, explain it naturally instead of dumping it.
- If the answer is incomplete, say so honestly and suggest the safest next action.
- If you are unsure, say "I don't know" instead of guessing.
- Do not promise a final outcome unless it is confirmed.
- If the user sounds frustrated, stay calm and helpful.
- Ask at most one short clarifying question when it really helps.
- Do not talk about retrieval, knowledge base, or matched sources.
""".strip()


class AIService:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.client = self._build_client()

    def _build_client(self) -> OpenAI | None:
        if not self.settings.openai_api_key:
            return None
        return OpenAI(api_key=self.settings.openai_api_key, max_retries=0, timeout=10.0)

    def available(self) -> bool:
        return self.client is not None

    @staticmethod
    def _build_system_prompt(mode: str, custom_prompt: str) -> str:
        system_prompt = SUPPORT_SYSTEM_PROMPT if mode == "support" else GENERAL_SYSTEM_PROMPT
        if custom_prompt:
            system_prompt = f"{system_prompt}\n\nAdditional instructions from the user:\n{custom_prompt}"
        return system_prompt

    @staticmethod
    def _build_context_prompt(question: str, history: list[dict[str, str]], mode: str, entries: list, products: list, document_matches: list[dict[str, str]]) -> str:
        kb_context = "\n\n".join(f"{entry.title}: {entry.content}" for entry in entries)
        product_context = "\n".join(
            f"- {product.name} ({product.brand}) - Rs {product.price}, {product.tag}, {product.description}"
            for product in products
        )
        document_context = "\n\n".join(
            f"{item['name']}: {item['snippet']}"
            for item in document_matches
        )
        history_text = "\n".join(
            f"{item.get('role', 'user')}: {item.get('content', '')}"
            for item in history[-10:]
            if item.get("content")
        )
        mode_line = (
            "Support mode. Prioritize support policy, direct next steps, and clean resolution guidance."
            if mode == "support"
            else "Unified AI mode. Help with general questions, shopping, support, writing, coding, learning, and practical life decisions."
        )
        return (
            f"Mode: {mode_line}\n\n"
            f"Conversation history:\n{history_text or 'No prior history.'}\n\n"
            f"User question: {question}\n\n"
            f"Relevant product context:\n{product_context or 'No strongly matched products.'}\n\n"
            f"Relevant support context:\n{kb_context or 'No strongly matched support context.'}\n\n"
            f"Relevant uploaded document context:\n{document_context or 'No strongly matched uploaded documents.'}\n\n"
            "Write a helpful answer that feels natural, useful, complete, and grounded in the available context."
        )

    def _build_messages(
        self,
        *,
        question: str,
        history: list[dict[str, str]],
        mode: str,
        custom_prompt: str,
        entries: list,
        products: list,
        document_matches: list[dict[str, str]],
    ) -> list[dict[str, str]]:
        messages = [
            {"role": "system", "content": self._build_system_prompt(mode, custom_prompt)},
        ]
        for item in history[-10:]:
            role = str(item.get("role", "user"))
            content = str(item.get("content", "")).strip()
            if role in {"user", "assistant", "system"} and content:
                messages.append({"role": role, "content": content})
        messages.append(
            {
                "role": "user",
                "content": self._build_context_prompt(question, history, mode, entries, products, document_matches),
            }
        )
        return messages

    def generate_answer(
        self,
        *,
        question: str,
        history: list[dict[str, str]],
        mode: str,
        model: str,
        custom_prompt: str,
        entries: list,
        products: list,
        document_matches: list[dict[str, str]],
    ) -> str | None:
        if not self.client:
            return None
        response = self.client.chat.completions.create(
            model=model,
            messages=self._build_messages(
                question=question,
                history=history,
                mode=mode,
                custom_prompt=custom_prompt,
                entries=entries,
                products=products,
                document_matches=document_matches,
            ),
        )
        return response.choices[0].message.content if response.choices else None

    def generate_answer_stream(
        self,
        *,
        question: str,
        history: list[dict[str, str]],
        mode: str,
        model: str,
        custom_prompt: str,
        entries: list,
        products: list,
        document_matches: list[dict[str, str]],
    ) -> Iterator[str]:
        if not self.client:
            return iter(())

        stream = self.client.chat.completions.create(
            model=model,
            messages=self._build_messages(
                question=question,
                history=history,
                mode=mode,
                custom_prompt=custom_prompt,
                entries=entries,
                products=products,
                document_matches=document_matches,
            ),
            stream=True,
        )

        def iterator() -> Iterator[str]:
            for chunk in stream:
                delta = chunk.choices[0].delta.content if chunk.choices else None
                if delta:
                    yield delta

        return iterator()


__all__ = ["AIService", "GENERAL_SYSTEM_PROMPT", "SUPPORT_SYSTEM_PROMPT", "OpenAIError"]
