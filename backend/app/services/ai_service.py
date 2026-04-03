from __future__ import annotations

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

        system_prompt = SUPPORT_SYSTEM_PROMPT if mode == "support" else GENERAL_SYSTEM_PROMPT
        if custom_prompt:
            system_prompt = f"{system_prompt}\n\nAdditional instructions from the user:\n{custom_prompt}"

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

        response = self.client.responses.create(
            model=model,
            input=[
                {
                    "role": "system",
                    "content": [{"type": "input_text", "text": system_prompt}],
                },
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "input_text",
                            "text": (
                                f"Mode: {mode_line}\n\n"
                                f"Conversation history:\n{history_text or 'No prior history.'}\n\n"
                                f"User question: {question}\n\n"
                                f"Relevant product context:\n{product_context or 'No strongly matched products.'}\n\n"
                                f"Relevant support context:\n{kb_context or 'No strongly matched support context.'}\n\n"
                                f"Relevant uploaded document context:\n{document_context or 'No strongly matched uploaded documents.'}\n\n"
                                "Write a helpful answer that feels natural, useful, complete, and grounded in the available context."
                            ),
                        }
                    ],
                },
            ],
        )
        return getattr(response, "output_text", None)


__all__ = ["AIService", "GENERAL_SYSTEM_PROMPT", "SUPPORT_SYSTEM_PROMPT", "OpenAIError"]
