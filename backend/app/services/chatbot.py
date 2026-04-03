from __future__ import annotations

import ast
import math
import operator
import re
import time
from textwrap import shorten

from openai import OpenAI
from openai import OpenAIError

from app.config import Settings
from app.models import ChatResponse, Source
from app.services.knowledge_base import KnowledgeBaseService, KnowledgeEntry
from app.services.product_catalog import ProductCatalogService

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


# GENERAL_SYSTEM_PROMPT = """
# You are Smart AI, a warm, capable, natural assistant.
# # You help with general questions, ecommerce shopping, practical decision-making, customer support, study help, writing help, coding help, and everyday life problems in one conversation.

# # Core behavior:
# # - Sound like a helpful real person, not a search engine or documentation bot.
# # - Answer the user's actual question first.
# # - Be practical, clear, and specific.
# # - If the user is vague, make one reasonable assumption, give a helpful starting answer, and then ask one useful follow-up question.
# # - For recommendations, give 2 or 3 options with short reasons.
# # - For problem solving, explain the likely issue, give workable options, recommend the best next step, and keep it easy to follow.
# # - For emotional or stressful situations, be calm, supportive, and grounded.
# # - For broad general questions, answer in a complete and useful way instead of pushing the user back for more detail too quickly.
# # - For shopping questions, use available product context directly.
# # - For support questions, use support context naturally without sounding robotic.
# # - Prefer correctness over speed when you know the answer.
# # - If you are unsure, say that clearly instead of sounding confident.
# # - For technical or factual questions, give the direct answer first, then the explanation.
# # - Do not mention retrieval, knowledge base, matched sources, or internal context.
# # - Do not give one-line shallow replies unless the user clearly asks for a very short answer.
# # """.strip()

# SUPPORT_SYSTEM_PROMPT = """
# # You are Smart AI in support mode, a warm and helpful support teammate.

# # Core behavior:
# # - Lead with the answer in simple words.
# # - Then give the best next step.
# # - If policy applies, explain it naturally instead of dumping it.
# # - If the answer is incomplete, say so honestly and suggest the safest next action.
# # - If the user sounds frustrated, stay calm and helpful.
# # - Ask at most one short clarifying question when it really helps.
# # - Do not talk about retrieval, knowledge base, or matched sources.
# """.strip()


class ChatbotService:
    def __init__(
        self,
        settings: Settings,
        knowledge_base: KnowledgeBaseService,
        product_catalog: ProductCatalogService,
    ) -> None:
        self.settings = settings
        self.knowledge_base = knowledge_base
        self.product_catalog = product_catalog
        self.client = self._build_client()
        self._llm_disabled_until = 0.0

    def _build_client(self) -> OpenAI | None:
        if not self.settings.openai_api_key:
            return None
        return OpenAI(api_key=self.settings.openai_api_key, max_retries=0, timeout=10.0)

    @staticmethod
    def _format_answer(short_answer: str, why: str, next_step: str) -> str:
        return (
            f"Short Answer: {short_answer}\n\n"
            f"Why: {why}\n\n"
            f"Next Step: {next_step}"
        )

    def answer(
        self,
        question: str,
        history: list[dict[str, str]],
        mode: str = "general",
        model: str | None = None,
        custom_prompt: str | None = None,
        uploaded_documents: list[dict[str, str]] | None = None,
    ) -> ChatResponse:
        chat_mode = mode if mode in {"general", "support"} else "general"
        selected_model = model if model in {"gpt-4o-mini", "gpt-4o"} else self.settings.openai_model
        cleaned_prompt = (custom_prompt or "").strip()
        entries = self.knowledge_base.retrieve(question) if chat_mode == "support" else self.knowledge_base.retrieve(question, limit=4)
        products = self.product_catalog.recommend_products(question, limit=4) if chat_mode == "general" else []
        document_matches = self._retrieve_uploaded_documents(question, uploaded_documents or [])
        sources = self._build_sources(entries) if chat_mode == "support" else self._build_combined_sources(entries, products, document_matches)

        if self.client and not self._llm_temporarily_disabled():
            try:
                answer = self._generate_llm_answer(question, history, entries, products, document_matches, chat_mode, selected_model, cleaned_prompt)
                result_mode = f"llm+{chat_mode}+{selected_model}"
            except OpenAIError:
                self._temporarily_disable_llm()
                answer = self._generate_fallback_answer(question, entries, products, document_matches, chat_mode, history)
                result_mode = f"fallback+{chat_mode}"
        else:
            answer = self._generate_fallback_answer(question, entries, products, document_matches, chat_mode, history)
            result_mode = f"fallback+{chat_mode}"

        return ChatResponse(answer=answer, sources=sources, mode=result_mode)

    def welcome_message(self, mode: str) -> str:
        return (
            "I can help with refunds, billing, login issues, orders, shipping, and account questions. Tell me what happened, and I will guide you step by step."
            if mode == "support"
            else "Hi, I am here to help with shopping suggestions, product discovery, support questions, writing, learning, coding, and everyday tasks. What do you want help with today?"
        )

    def default_session_title(self, mode: str) -> str:
        return "New support chat" if mode == "support" else "New general chat"

    def suggested_session_title(self, question: str, mode: str) -> str:
        prefix = "Support" if mode == "support" else "Chat"
        cleaned = " ".join(question.strip().split())
        return shorten(cleaned, width=42, placeholder="...") or f"{prefix} session"

    def _llm_temporarily_disabled(self) -> bool:
        return time.time() < self._llm_disabled_until

    def _temporarily_disable_llm(self, seconds: int = 300) -> None:
        self._llm_disabled_until = time.time() + seconds

    def _generate_llm_answer(
        self,
        question: str,
        history: list[dict[str, str]],
        entries: list[KnowledgeEntry],
        products,
        document_matches: list[dict[str, str]],
        mode: str,
        model: str,
        custom_prompt: str,
    ) -> str:
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
            for item in history[-8:]
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
                                "Write a helpful answer that feels natural, useful, and complete."
                            ),
                        }
                    ],
                },
            ],
        )
        return getattr(response, "output_text", None) or self._generate_fallback_answer(question, entries, products, document_matches, mode, history)

    def _generate_fallback_answer(
        self,
        question: str,
        entries: list[KnowledgeEntry],
        products,
        document_matches: list[dict[str, str]],
        mode: str,
        history: list[dict[str, str]] | None = None,
    ) -> str:
        normalized = re.sub(r"\s+", " ", question.lower().strip())
        history = history or []
        recent_context = self._recent_user_context(history)
        contextual_normalized = self._merge_with_recent_context(normalized, recent_context)

        if document_matches and any(term in contextual_normalized for term in ["pdf", "document", "file", "notes", "from this file", "from the file", "uploaded"]):
            top = document_matches[0]
            return self._format_answer(
                f"Your uploaded file suggests: {top['snippet'][:160]}",
                f"I matched your question against the uploaded document `{top['name']}` and used the closest text I found there.",
                "Ask a more specific question from the file if you want a sharper answer, for example a summary, explanation, or answer from one section."
            )

        math_answer = self._simple_math_answer(question.strip())
        if math_answer is not None:
            return math_answer

        if mode == "support":
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
                return (
                    "I want to help, but I do not have a clear support answer for that yet.\n\n"
                    "This support mode works best for password reset, refunds, billing, shipping, order updates, and login problems. If you describe the issue in one clear sentence, I will try again."
                )
            return self._build_support_fallback(entries, contextual_normalized)

        if self._looks_like_comparison_request(contextual_normalized):
            matched_products = self._match_products_from_text(question)
            if len(matched_products) >= 2:
                return self._build_comparison_answer(matched_products[:2])
            if len(products) >= 2:
                return self._build_comparison_answer(products[:2])

        if self._is_support_question(contextual_normalized) and entries:
            return self._build_support_fallback(entries, contextual_normalized)

        if self._is_product_question(contextual_normalized):
            return self._build_product_fallback(question, contextual_normalized, products)

        if self._is_problem_solving_question(contextual_normalized):
            return self._build_problem_solving_fallback(contextual_normalized)

        if self._is_career_question(contextual_normalized):
            return self._build_career_topic_fallback(contextual_normalized)

        if self._is_study_question(contextual_normalized):
            return self._build_study_topic_fallback(question.strip(), contextual_normalized)

        if self._is_daily_life_question(contextual_normalized):
            return self._build_daily_life_topic_fallback(contextual_normalized)

        if any(term in contextual_normalized for term in ["write", "message", "email", "caption", "bio", "paragraph", "proposal", "resume", "cover letter"]):
            return self._build_writing_fallback(contextual_normalized)

        if any(term in contextual_normalized for term in ["code", "python", "java", "javascript", "react", "html", "css", "bug", "error", "program", "sql", "api"]):
            return self._build_coding_fallback(contextual_normalized)

        if self._is_programming_question(contextual_normalized):
            return self._build_programming_topic_fallback(question.strip(), contextual_normalized)

        if any(term in contextual_normalized for term in ["study", "learn", "explain", "meaning", "what is", "how does", "teach me", "simple words"]):
            return self._build_learning_fallback(question, contextual_normalized)

        factual_answer = self._build_common_factual_fallback(question.strip(), contextual_normalized)
        if factual_answer is not None:
            return factual_answer

        if any(term in contextual_normalized for term in ["healthy", "health", "weight", "exercise", "workout", "sleep", "water", "diet"]):
            return self._build_health_fallback(contextual_normalized)

        if any(term in contextual_normalized for term in ["travel", "trip", "vacation", "journey", "visit", "tour"]):
            return self._build_travel_fallback(contextual_normalized)

        if any(term in contextual_normalized for term in ["business", "startup", "market", "sell", "customer", "profit", "idea"]):
            return self._build_business_fallback(contextual_normalized)

        if normalized in {"hi", "hello", "hey", "good morning", "good evening"}:
            return (
                "Hello. I am ready to help.\n\n"
                "You can ask me for product suggestions, order help, support guidance, writing help, coding help, study help, or everyday life decisions."
            )

        if "help" in normalized and len(normalized.split()) <= 4:
            return (
                "Of course. I can help with a lot of things.\n\n"
                "For example, you can ask me to:\n"
                "- suggest a product under your budget\n"
                "- compare two products\n"
                "- explain an order or refund problem\n"
                "- help write an email or message\n"
                "- explain a topic simply\n"
                "- help fix a coding issue\n"
                "- help you decide what to do next\n\n"
                "Just tell me the exact thing you want help with."
            )

        return self._build_general_rich_fallback(question, contextual_normalized, recent_context)

    @staticmethod
    def _simple_math_answer(question: str) -> str | None:
        stripped = question.strip()
        lowered = stripped.lower()

        percent_match = re.fullmatch(r"(\d+(?:\.\d+)?)%\s+of\s+(\d+(?:\.\d+)?)", lowered)
        if percent_match:
            percent = float(percent_match.group(1))
            value = float(percent_match.group(2))
            result = (percent / 100) * value
            if result.is_integer():
                result = int(result)
            return (
                f"Short answer: {result}\n\n"
                f"Explanation: {percent}% of {value:g} means ({percent} / 100) x {value:g}.\n\n"
                f"Steps / Details:\n1. Convert {percent}% into {percent / 100}\n2. Multiply by {value:g}\n3. Final result is {result}"
            )

        conversion_answer = ChatbotService._simple_conversion_answer(lowered)
        if conversion_answer is not None:
            return conversion_answer

        compact = stripped.replace(" ", "").replace("x", "*").replace("X", "*")
        if not re.fullmatch(r"[\d\.\+\-\*/\(\)]+", compact):
            return None
        try:
            node = ast.parse(compact, mode="eval")
        except SyntaxError:
            return None

        operators = {
            ast.Add: operator.add,
            ast.Sub: operator.sub,
            ast.Mult: operator.mul,
            ast.Div: operator.truediv,
            ast.USub: operator.neg,
            ast.UAdd: operator.pos,
        }

        def evaluate(expr):
            if isinstance(expr, ast.Expression):
                return evaluate(expr.body)
            if isinstance(expr, ast.Constant) and isinstance(expr.value, (int, float)):
                return expr.value
            if isinstance(expr, ast.UnaryOp) and type(expr.op) in operators:
                return operators[type(expr.op)](evaluate(expr.operand))
            if isinstance(expr, ast.BinOp) and type(expr.op) in operators:
                left = evaluate(expr.left)
                right = evaluate(expr.right)
                return operators[type(expr.op)](left, right)
            raise ValueError("Unsupported expression")

        try:
            result = evaluate(node)
        except (ValueError, ZeroDivisionError):
            return None

        if isinstance(result, float) and result.is_integer():
            result = int(result)
        return f"Short answer: {result}\n\nExplanation: I evaluated the expression `{question}`.\n\nSteps / Details:\n1. Read the numbers and operators\n2. Apply the calculation in order\n3. Final result is {result}"

    @staticmethod
    def _simple_conversion_answer(lowered: str) -> str | None:
        conversions = {
            ("km", "m"): 1000,
            ("m", "cm"): 100,
            ("cm", "mm"): 10,
            ("kg", "g"): 1000,
            ("hour", "minutes"): 60,
            ("hours", "minutes"): 60,
            ("minute", "seconds"): 60,
            ("minutes", "seconds"): 60,
        }
        match = re.fullmatch(r"(\d+(?:\.\d+)?)\s*([a-z]+)\s+(?:to|in)\s+([a-z]+)", lowered)
        if not match:
            sqrt_match = re.fullmatch(r"(?:sqrt|square root of)\s*(\d+(?:\.\d+)?)", lowered)
            if sqrt_match:
                value = float(sqrt_match.group(1))
                result = math.sqrt(value)
                if result.is_integer():
                    result = int(result)
                return (
                    f"Short answer: {result}\n\n"
                    f"Explanation: Square root means the number which multiplies by itself to give {value:g}.\n\n"
                    f"Steps / Details:\n1. Take the square root of {value:g}\n2. Final result is {result}"
                )
            return None

        value = float(match.group(1))
        from_unit = match.group(2)
        to_unit = match.group(3)
        factor = conversions.get((from_unit, to_unit))
        if factor is None:
            return None
        result = value * factor
        if result.is_integer():
            result = int(result)
        return (
            f"Short answer: {result} {to_unit}\n\n"
            f"Explanation: 1 {from_unit} = {factor:g} {to_unit}.\n\n"
            f"Steps / Details:\n1. Start with {value:g} {from_unit}\n2. Multiply by {factor:g}\n3. Final result is {result} {to_unit}"
        )

    def _build_product_fallback(self, question: str, normalized: str, products) -> str:
        budget = self._extract_budget(normalized)
        priority = self._extract_priority(normalized)
        category = self._detect_product_category(normalized)
        category_label = {
            "phone": "phones",
            "laptop": "laptops",
            "tablet": "tablets",
            "watch": "smartwatches",
            "accessory": "accessories",
        }.get(category, "products")

        if not products:
            if budget and priority:
                return (
                    f"I can help you find {category_label} under Rs {budget:,} for {priority}.\n\n"
                    "I do not have a strong match from the catalog yet, so tell me one more preference like battery, display, brand, weight, or performance and I will narrow it down better."
                )
            if budget:
                return (
                    f"I can help you find {category_label} under Rs {budget:,}.\n\n"
                    "Tell me what matters most, like camera, gaming, battery, display, study, office work, or portability, and I will guide you better."
                )
            return (
                f"I can help you choose {category_label}.\n\n"
                "Tell me your budget and what matters most, and I will give you better options instead of generic suggestions."
            )

        intro = "Here are the best options I would start with right now:"
        if budget and priority:
            intro = f"Here are the better {category_label} I would look at under Rs {budget:,} for {priority}:"
        elif budget:
            intro = f"Here are some strong {category_label} under Rs {budget:,}:"
        elif priority:
            intro = f"Here are some good {category_label} I would look at for {priority}:"

        lines = []
        for index, product in enumerate(products[:3], start=1):
            reason = self._product_reason(product, priority or normalized)
            lines.append(f"{index}. {product.name} by {product.brand} - Rs {product.price:,}. {reason}")

        follow_up = "If you want, I can narrow this down to one best pick for your budget."
        if category == "phone":
            follow_up = "If you want, I can narrow this down by camera, gaming, battery, or display."
        elif category == "laptop":
            follow_up = "If you want, I can narrow this down for study, coding, office work, or gaming."

        return f"{intro}\n\n" + "\n".join(lines) + f"\n\nBest next step: {follow_up}"

    def _build_support_fallback(self, entries: list[KnowledgeEntry], normalized: str) -> str:
        top_entry = entries[0]
        title = top_entry.title.lower()

        if "account" in title or "password" in normalized or "login" in normalized or "otp" in normalized:
            return (
                "Here is the simple answer.\n\n"
                "You can reset your password from the login page using the Forgot Password option. If you no longer have access to your email, the account should move to manual verification before the email can be changed.\n\n"
                "If you want, tell me exactly what part is failing, like password reset, OTP, or email access, and I will guide you more clearly."
            )

        if "billing" in title or "refund" in normalized or "charged" in normalized:
            return (
                "Here is the clearest guidance I can give.\n\n"
                "Refund requests are generally handled within the allowed window after the latest charge, especially when usage stays within the policy threshold. If this is about a duplicate or unexpected charge, it helps to confirm the plan name, charge date, and whether it was monthly or annual.\n\n"
                "If you want, tell me what you were charged for and I will help you phrase the next support step."
            )

        if "shipping" in title or "order" in normalized or "address" in normalized:
            return (
                "Here is the practical answer.\n\n"
                "Order changes are usually possible only before the package reaches the packed stage. After that, the request normally becomes a post-order support case.\n\n"
                "If you want, tell me whether the order is already packed or shipped and I will tell you the best next step."
            )

        primary = shorten(top_entry.content, width=250, placeholder="...")
        related_titles = ", ".join(entry.title for entry in entries[1:3])
        related_line = f"\n\nRelated help: {related_titles}." if related_titles else ""
        return (
            f"Here is the best answer I can give from the support information right now:\n\n{primary}"
            f"{related_line}\n\n"
            "If you want, tell me your exact situation and I will explain it in simpler words."
        )

    def _build_problem_solving_fallback(self, normalized: str) -> str:
        if any(term in normalized for term in ["study", "exam", "prepare", "syllabus", "revision", "homework"]):
            return (
                "Let us make this easier.\n\n"
                "A good study plan is usually:\n"
                "1. list the subjects or chapters you actually need to finish\n"
                "2. divide them into small daily targets\n"
                "3. keep one short revision block at the end of each day\n"
                "4. leave time for practice instead of only reading\n\n"
                "If you want, tell me your exam date and subjects, and I will build a simple study plan for you."
            )

        if any(term in normalized for term in ["job", "career", "interview", "resume", "cv", "offer", "promotion"]):
            return (
                "Yes, I can help you think through that.\n\n"
                "For career problems, the best approach is usually to compare three things: growth, stability, and fit. Once those are clear, the decision becomes much easier.\n\n"
                "If you want, tell me the exact situation, like interview prep, two job options, or resume help, and I will guide you step by step."
            )

        if any(term in normalized for term in ["money", "budget", "save", "salary", "expense", "spend", "afford"]):
            return (
                "We can solve that in a practical way.\n\n"
                "Start by splitting the problem into three parts: fixed expenses, flexible spending, and savings target. Once those are clear, you can see what needs to change first.\n\n"
                "If you want, send me your monthly income and main expenses, and I will help you make a simple budget."
            )

        if any(term in normalized for term in ["time", "schedule", "routine", "busy", "overwhelmed", "late", "procrastin"]):
            return (
                "A good way to fix that is to reduce the problem, not just work harder.\n\n"
                "Pick the top 3 tasks that actually matter today, finish the hardest one first, and keep short time blocks instead of trying to do everything at once.\n\n"
                "If you want, tell me what your day looks like, and I will help you build a practical routine."
            )

        if any(term in normalized for term in ["relationship", "friend", "family", "argue", "fight", "talk to", "message them"]):
            return (
                "I can help you think through that calmly.\n\n"
                "Usually the best first step is to be clear about what you feel, what happened, and what result you want before reacting. That makes the next conversation much better.\n\n"
                "If you want, tell me the situation and I can help you plan what to say."
            )

        return (
            "I can help you think this through.\n\n"
            "A simple way to solve it is:\n"
            "1. say what the real problem is\n"
            "2. list the main options\n"
            "3. decide what matters most right now\n"
            "4. pick the next small step instead of solving everything at once\n\n"
            "Tell me the situation in one or two lines, and I will help you work through it clearly."
        )

    def _build_programming_topic_fallback(self, question: str, normalized: str) -> str:
        if any(term in normalized for term in ["logic", "approach", "algorithm", "dry run"]):
            return (
                "Yes. For programming problems, the best way is to separate the solution into logic first and code second.\n\n"
                "A strong method is:\n"
                "1. understand the input and output clearly\n"
                "2. solve one small example by hand\n"
                "3. write the step-by-step logic\n"
                "4. only then convert it into code\n"
                "5. test edge cases before finishing\n\n"
                "If you want, send me the exact problem and language, and I will give you the logic plus working code."
            )

        if any(term in normalized for term in ["project", "beginner project", "mini project"]):
            return (
                "A good programming project should be small enough to finish and useful enough to learn from.\n\n"
                "Good beginner project ideas are:\n"
                "1. calculator\n"
                "2. to-do app\n"
                "3. student record system\n"
                "4. login form\n"
                "5. weather app using API\n\n"
                "If you tell me your language or skill level, I can suggest the best project and the exact steps."
            )

        if any(term in normalized for term in ["interview", "placement", "coding round", "oa"]):
            return (
                "For coding interview prep, focus on the pattern, not just random questions.\n\n"
                "A strong order is:\n"
                "1. arrays and strings\n"
                "2. hash maps and sets\n"
                "3. binary search\n"
                "4. linked list, stack, queue\n"
                "5. trees and recursion\n"
                "6. graphs and dynamic programming basics\n\n"
                "If you want, I can make you a simple coding interview roadmap with daily practice."
            )

        return (
            "Yes, I can help properly with programming questions.\n\n"
            "Ask me in this format for the best answer:\n"
            "1. topic or problem name\n"
            "2. language you want\n"
            "3. whether you want logic, code, or both\n\n"
            "Example:\n"
            "- reverse array in Java with explanation\n"
            "- Python code for palindrome check\n"
            "- explain binary search simply"
        )

    def _build_career_topic_fallback(self, normalized: str) -> str:
        if any(term in normalized for term in ["resume", "cv"]):
            return (
                "For a stronger resume, focus on clarity and proof, not decoration.\n\n"
                "A good resume line usually has:\n"
                "1. what you built or did\n"
                "2. which tools you used\n"
                "3. what result or impact it had\n\n"
                "If you want, paste one resume point and I will rewrite it in a better way."
            )

        if any(term in normalized for term in ["interview", "hr round", "introduce yourself", "self introduction"]):
            return (
                "For interviews, the best answers are clear, calm, and specific.\n\n"
                "A simple structure is:\n"
                "1. who you are\n"
                "2. what skills or experience matter most\n"
                "3. why you fit the role\n\n"
                "If you want, I can give you an interview answer exactly for your field."
            )

        if any(term in normalized for term in ["job offer", "switch", "which job", "career option", "future"]):
            return (
                "For career decisions, compare these four things first:\n"
                "1. growth\n"
                "2. learning\n"
                "3. stability\n"
                "4. salary and work-life fit\n\n"
                "The best option is usually the one that improves your future value, not only your short-term comfort.\n\n"
                "If you tell me the two options, I can compare them clearly."
            )

        return (
            "I can help with career questions in a practical way.\n\n"
            "Tell me whether you need help with resume, interview, skill roadmap, job switch, or career confusion, and I will guide you step by step."
        )

    def _build_study_topic_fallback(self, question: str, normalized: str) -> str:
        if any(term in normalized for term in ["plan", "schedule", "routine", "timetable"]):
            return (
                "A good study plan is simple enough to follow every day.\n\n"
                "Use this structure:\n"
                "1. hardest topic first\n"
                "2. 2 or 3 study blocks per day\n"
                "3. short revision at night\n"
                "4. practice questions every few days\n\n"
                "If you tell me your subjects and exam date, I can make the full schedule for you."
            )

        if any(term in normalized for term in ["focus", "concentrate", "remember", "revision"]):
            return (
                "For studying better, the goal is not longer hours. It is better recall.\n\n"
                "A strong method is:\n"
                "1. study one topic in short blocks\n"
                "2. close the book and recall from memory\n"
                "3. revise the weak parts again\n"
                "4. test yourself instead of only rereading\n\n"
                "If you want, I can help you make a better revision method for your subject."
            )

        return (
            f"I can explain or plan that in a study-friendly way.\n\n"
            f"Topic: {question}\n\n"
            "If you want, I can answer it in one of these styles:\n"
            "1. simple explanation\n"
            "2. exam answer\n"
            "3. short notes\n"
            "4. step-by-step learning plan"
        )

    def _build_daily_life_topic_fallback(self, normalized: str) -> str:
        if any(term in normalized for term in ["habit", "routine", "discipline", "wakeup", "sleep schedule"]):
            return (
                "A better routine usually comes from reducing friction, not from making huge promises.\n\n"
                "A practical way is:\n"
                "1. choose one habit only\n"
                "2. attach it to an existing part of your day\n"
                "3. make it easy enough to repeat daily\n"
                "4. track consistency, not perfection\n\n"
                "If you tell me the habit you want, I can help you build a realistic routine."
            )

        if any(term in normalized for term in ["sad", "upset", "lonely", "demotivated", "stress", "anxiety"]):
            return (
                "I am sorry you are dealing with that.\n\n"
                "A useful first step is to slow things down and focus on one stabilizing action right now, like rest, water, a short walk, or talking to someone you trust.\n\n"
                "If you want, tell me what is going on and I will help you think through it carefully."
            )

        if any(term in normalized for term in ["decision", "choose", "confused", "stuck", "what should i do"]):
            return (
                "When you feel stuck, use this simple filter:\n"
                "1. what matters most right now\n"
                "2. what option carries the least regret later\n"
                "3. what small step gives you more clarity quickly\n\n"
                "If you tell me the exact decision, I can help you choose more clearly."
            )

        return (
            "I can help with everyday life problems too.\n\n"
            "Tell me the exact situation, and I will try to give a practical answer, not just a generic one."
        )

    def _build_writing_fallback(self, normalized: str) -> str:
        if any(term in normalized for term in ["email", "mail"]):
            return (
                "Yes, I can help with that.\n\n"
                "Tell me who the email is for, what you need to say, and the tone you want, like formal, polite, friendly, or professional. If you already have a draft, paste it here and I will improve it."
            )
        if any(term in normalized for term in ["resume", "cv", "cover letter"]):
            return (
                "Yes, I can help with that too.\n\n"
                "If you share your role, experience level, and current draft, I can help you improve the wording, structure, and impact."
            )
        return (
            "Sure. I can help you write it clearly.\n\n"
            "Tell me what you want to write, who it is for, and the tone you want. If you already have a draft, I can rewrite it into something stronger."
        )

    def _build_coding_fallback(self, normalized: str) -> str:
        if self._looks_like_hello_world_request(normalized):
            language = "python"
            if "java" in normalized:
                language = "java"
            elif "javascript" in normalized or "js" in normalized:
                language = "javascript"
            elif "c++" in normalized or "cpp" in normalized:
                language = "c++"
            elif "c#" in normalized or "c sharp" in normalized:
                language = "c#"
            elif "html" in normalized:
                language = "html"

            examples = {
                "python": 'Here is a simple Python hello world program:\n\n```python\nprint("Hello, world!")\n```\n\nRun it with `python filename.py`.',
                "java": 'Here is a simple Java hello world program:\n\n```java\npublic class Main {\n    public static void main(String[] args) {\n        System.out.println("Hello, world!");\n    }\n}\n```\n\nSave it as `Main.java`, then compile with `javac Main.java` and run with `java Main`.',
                "javascript": 'Here is a simple JavaScript hello world example:\n\n```javascript\nconsole.log("Hello, world!");\n```\n\nRun it in the browser console or with `node filename.js`.',
                "c++": 'Here is a simple C++ hello world program:\n\n```cpp\n#include <iostream>\n\nint main() {\n    std::cout << "Hello, world!" << std::endl;\n    return 0;\n}\n```\n\nCompile it with a C++ compiler, then run the output file.',
                "c#": 'Here is a simple C# hello world program:\n\n```csharp\nusing System;\n\nclass Program {\n    static void Main() {\n        Console.WriteLine("Hello, world!");\n    }\n}\n```\n\nRun it with your C# compiler or `dotnet run`.',
                "html": 'Here is a simple HTML hello world example:\n\n```html\n<!DOCTYPE html>\n<html>\n  <body>\n    <h1>Hello, world!</h1>\n  </body>\n</html>\n```\n\nOpen it in a browser to see the result.',
            }
            return examples[language]

        beginner_code_examples = self._beginner_code_example(normalized)
        if beginner_code_examples:
            return beginner_code_examples

        dsa_response = self._dsa_fallback(normalized)
        if dsa_response:
            return dsa_response

        if any(term in normalized for term in ["code for", "write code", "example code", "sample code", "program for"]):
            return (
                "Yes. I can write the code for you.\n\n"
                "Tell me these 2 things:\n"
                "1. which language you want\n"
                "2. what the program should do\n\n"
                "For example:\n"
                "- write Python code for a calculator\n"
                "- give me Java code for hello world\n"
                "- create HTML and CSS for a login page"
            )

        if any(term in normalized for term in ["error", "bug", "not working", "exception"]):
            return self._format_answer(
                "Yes, I can help debug it.",
                "The fastest way to find the real issue is to look at the code, the error message, and what you expected to happen together.",
                "Send me the code, the exact error, and the expected result, and I will help you fix it step by step."
            )
        return self._format_answer(
            "Yes, I can help with coding.",
            "I can explain concepts, write clean examples, or help fix errors, but I need the topic, language, or problem to give the best answer.",
            "Tell me what you are building or what code you want, and I will give you a clearer answer with working examples."
        )

    @staticmethod
    def _dsa_fallback(normalized: str) -> str | None:
        dsa_terms = [
            "dsa",
            "data structure",
            "data structures",
            "algorithm",
            "algorithms",
            "array question",
            "linked list",
            "stack",
            "queue",
            "tree",
            "graph",
            "recursion",
            "sorting",
            "searching",
        ]
        if not any(term in normalized for term in dsa_terms):
            return None

        if any(term in normalized for term in ["question", "questions", "problems", "practice"]):
            return (
                "Sure. Here are good beginner-to-intermediate DSA questions to practice:\n\n"
                "1. Reverse an array\n"
                "2. Find the maximum and minimum in an array\n"
                "3. Check if a string is a palindrome\n"
                "4. Find duplicates in an array\n"
                "5. Implement stack using array\n"
                "6. Implement queue using array or linked list\n"
                "7. Reverse a linked list\n"
                "8. Detect a cycle in a linked list\n"
                "9. Binary search in a sorted array\n"
                "10. Sort an array using bubble sort, selection sort, and merge sort\n"
                "11. Find the height of a binary tree\n"
                "12. Level-order traversal of a binary tree\n"
                "13. DFS and BFS traversal of a graph\n"
                "14. Detect if a graph has a cycle\n"
                "15. Solve Fibonacci using recursion and dynamic programming\n\n"
                "If you want, I can also give:\n"
                "- DSA questions topic-wise\n"
                "- DSA questions for interviews\n"
                "- DSA questions with answers in Java, Python, or C++"
            )

        if any(term in normalized for term in ["roadmap", "plan", "how to learn", "start dsa", "learn dsa"]):
            return (
                "A simple DSA roadmap is:\n\n"
                "1. Arrays and strings\n"
                "2. Recursion and basic sorting\n"
                "3. Linked list, stack, queue\n"
                "4. Binary search and hashing\n"
                "5. Trees and binary search trees\n"
                "6. Graphs and traversals\n"
                "7. Dynamic programming basics\n\n"
                "Best next step: start with arrays, strings, and binary search first, then move to linked list and trees."
            )

        return (
            "Yes, I can help with DSA.\n\n"
            "You can ask me for:\n"
            "- DSA questions\n"
            "- DSA roadmap\n"
            "- topic-wise practice problems\n"
            "- code solutions in Java, Python, or C++\n"
            "- interview preparation questions"
        )

    @staticmethod
    def _looks_like_hello_world_request(normalized: str) -> bool:
        has_hello = any(
            term in normalized
            for term in [
                "hello world",
                "hello word",
                "helo world",
                "hlo world",
                "print hello",
                "hello wrld",
            ]
        )
        has_code_intent = any(
            term in normalized
            for term in [
                "code",
                "program",
                "example",
                "sample",
                "write",
                "give me",
                "show me",
                "batao",
                "do",
                "de do",
                "dedo",
            ]
        )
        has_language = any(
            term in normalized
            for term in [
                "java",
                "python",
                "javascript",
                "js",
                "c++",
                "cpp",
                "c#",
                "c sharp",
                "html",
                "language java",
                "java language",
                "laungvage java",
            ]
        )
        return has_hello or (has_language and has_code_intent and "hello" in normalized)

    @staticmethod
    def _beginner_code_example(normalized: str) -> str | None:
        language = "python"
        if "java" in normalized:
            language = "java"
        elif "javascript" in normalized or "js" in normalized:
            language = "javascript"
        elif "c++" in normalized or "cpp" in normalized:
            language = "c++"
        elif "c#" in normalized or "c sharp" in normalized:
            language = "c#"
        elif "html" in normalized:
            language = "html"

        request_groups = [
            (
                ["palindrome"],
                {
                    "python": 'Here is a simple Python palindrome program:\n\n```python\ntext = input("Enter a string: ")\n\nif text == text[::-1]:\n    print("Palindrome")\nelse:\n    print("Not palindrome")\n```\n\nThis checks whether the string reads the same forward and backward.',
                    "java": 'Here is a simple Java palindrome program:\n\n```java\nimport java.util.Scanner;\n\npublic class Main {\n    public static void main(String[] args) {\n        Scanner sc = new Scanner(System.in);\n        System.out.print("Enter a string: ");\n        String text = sc.nextLine();\n        String reversed = new StringBuilder(text).reverse().toString();\n\n        if (text.equals(reversed)) {\n            System.out.println("Palindrome");\n        } else {\n            System.out.println("Not palindrome");\n        }\n    }\n}\n```\n\nThis checks whether the string is the same in forward and reverse order.',
                    "javascript": 'Here is a simple JavaScript palindrome program:\n\n```javascript\nconst text = prompt("Enter a string:");\nconst reversed = text.split("").reverse().join("");\n\nif (text === reversed) {\n  console.log("Palindrome");\n} else {\n  console.log("Not palindrome");\n}\n```\n\nThis compares the original string with its reversed version.',
                    "c++": 'Here is a simple C++ palindrome program:\n\n```cpp\n#include <iostream>\n#include <string>\n#include <algorithm>\nusing namespace std;\n\nint main() {\n    string text, reversed;\n    cout << "Enter a string: ";\n    cin >> text;\n\n    reversed = text;\n    reverse(reversed.begin(), reversed.end());\n\n    if (text == reversed) {\n        cout << "Palindrome" << endl;\n    } else {\n        cout << "Not palindrome" << endl;\n    }\n\n    return 0;\n}\n```\n\nThis compares the original string with the reversed string.',
                    "c#": 'Here is a simple C# palindrome program:\n\n```csharp\nusing System;\n\nclass Program {\n    static void Main() {\n        Console.Write("Enter a string: ");\n        string text = Console.ReadLine();\n        char[] chars = text.ToCharArray();\n        Array.Reverse(chars);\n        string reversed = new string(chars);\n\n        if (text == reversed) {\n            Console.WriteLine("Palindrome");\n        } else {\n            Console.WriteLine("Not palindrome");\n        }\n    }\n}\n```\n\nThis checks whether the original string and reversed string are equal.',
                    "html": 'For palindrome logic, HTML alone is not enough. Use JavaScript with HTML if you want an input form and palindrome check in the browser.',
                },
            ),
            (
                ["variable", "variables"],
                {
                    "python": 'Here is a simple Python variable example:\n\n```python\nname = "Riya"\nage = 21\nprint(name)\nprint(age)\n```\n\nA variable stores a value so you can use it later in the program.',
                    "java": 'Here is a simple Java variable example:\n\n```java\npublic class Main {\n    public static void main(String[] args) {\n        String name = "Riya";\n        int age = 21;\n\n        System.out.println(name);\n        System.out.println(age);\n    }\n}\n```\n\nA variable stores a value that your program can use later.',
                    "javascript": 'Here is a simple JavaScript variable example:\n\n```javascript\nlet name = "Riya";\nlet age = 21;\n\nconsole.log(name);\nconsole.log(age);\n```\n\nVariables store values you want to reuse.',
                    "c++": 'Here is a simple C++ variable example:\n\n```cpp\n#include <iostream>\n#include <string>\nusing namespace std;\n\nint main() {\n    string name = "Riya";\n    int age = 21;\n\n    cout << name << endl;\n    cout << age << endl;\n    return 0;\n}\n```\n\nVariables store data your program needs.',
                    "c#": 'Here is a simple C# variable example:\n\n```csharp\nusing System;\n\nclass Program {\n    static void Main() {\n        string name = "Riya";\n        int age = 21;\n\n        Console.WriteLine(name);\n        Console.WriteLine(age);\n    }\n}\n```\n\nVariables hold values your program can use.',
                    "html": 'HTML itself does not use variables like programming languages. If you want variables, JavaScript is usually used with HTML.',
                },
            ),
            (
                ["if else", "if-else", "condition", "conditional"],
                {
                    "python": 'Here is a simple Python if-else example:\n\n```python\nage = 18\n\nif age >= 18:\n    print("Adult")\nelse:\n    print("Minor")\n```\n\nThis checks a condition and runs one of two paths.',
                    "java": 'Here is a simple Java if-else example:\n\n```java\npublic class Main {\n    public static void main(String[] args) {\n        int age = 18;\n\n        if (age >= 18) {\n            System.out.println("Adult");\n        } else {\n            System.out.println("Minor");\n        }\n    }\n}\n```\n\nThis checks a condition and chooses one block to run.',
                    "javascript": 'Here is a simple JavaScript if-else example:\n\n```javascript\nlet age = 18;\n\nif (age >= 18) {\n  console.log("Adult");\n} else {\n  console.log("Minor");\n}\n```\n\nThis runs different code based on a condition.',
                    "c++": 'Here is a simple C++ if-else example:\n\n```cpp\n#include <iostream>\nusing namespace std;\n\nint main() {\n    int age = 18;\n\n    if (age >= 18) {\n        cout << "Adult" << endl;\n    } else {\n        cout << "Minor" << endl;\n    }\n    return 0;\n}\n```',
                    "c#": 'Here is a simple C# if-else example:\n\n```csharp\nusing System;\n\nclass Program {\n    static void Main() {\n        int age = 18;\n\n        if (age >= 18) {\n            Console.WriteLine("Adult");\n        } else {\n            Console.WriteLine("Minor");\n        }\n    }\n}\n```',
                    "html": 'HTML does not directly support if-else logic. That is usually done with JavaScript or in a backend language.',
                },
            ),
            (
                ["for loop", "loop", "repeat"],
                {
                    "python": 'Here is a simple Python for loop example:\n\n```python\nfor i in range(1, 6):\n    print(i)\n```\n\nThis prints numbers from 1 to 5.',
                    "java": 'Here is a simple Java for loop example:\n\n```java\npublic class Main {\n    public static void main(String[] args) {\n        for (int i = 1; i <= 5; i++) {\n            System.out.println(i);\n        }\n    }\n}\n```\n\nThis prints numbers from 1 to 5.',
                    "javascript": 'Here is a simple JavaScript for loop example:\n\n```javascript\nfor (let i = 1; i <= 5; i++) {\n  console.log(i);\n}\n```\n\nThis repeats the code 5 times.',
                    "c++": 'Here is a simple C++ for loop example:\n\n```cpp\n#include <iostream>\nusing namespace std;\n\nint main() {\n    for (int i = 1; i <= 5; i++) {\n        cout << i << endl;\n    }\n    return 0;\n}\n```',
                    "c#": 'Here is a simple C# for loop example:\n\n```csharp\nusing System;\n\nclass Program {\n    static void Main() {\n        for (int i = 1; i <= 5; i++) {\n            Console.WriteLine(i);\n        }\n    }\n}\n```',
                    "html": 'HTML does not have loops by itself. Loops are usually done with JavaScript or backend code.',
                },
            ),
            (
                ["input", "scanner", "user input"],
                {
                    "python": 'Here is a simple Python input example:\n\n```python\nname = input("Enter your name: ")\nprint("Hello,", name)\n```\n\nThis takes input from the user and prints it.',
                    "java": 'Here is a simple Java input example using Scanner:\n\n```java\nimport java.util.Scanner;\n\npublic class Main {\n    public static void main(String[] args) {\n        Scanner sc = new Scanner(System.in);\n        System.out.print("Enter your name: ");\n        String name = sc.nextLine();\n        System.out.println("Hello, " + name);\n    }\n}\n```\n\nThis takes input from the user and prints it.',
                    "javascript": 'In browser JavaScript, a simple input example is:\n\n```javascript\nlet name = prompt("Enter your name:");\nconsole.log("Hello, " + name);\n```',
                    "c++": 'Here is a simple C++ input example:\n\n```cpp\n#include <iostream>\n#include <string>\nusing namespace std;\n\nint main() {\n    string name;\n    cout << "Enter your name: ";\n    getline(cin, name);\n    cout << "Hello, " << name << endl;\n    return 0;\n}\n```',
                    "c#": 'Here is a simple C# input example:\n\n```csharp\nusing System;\n\nclass Program {\n    static void Main() {\n        Console.Write("Enter your name: ");\n        string name = Console.ReadLine();\n        Console.WriteLine("Hello, " + name);\n    }\n}\n```',
                    "html": 'If you want user input in HTML, you usually use an `<input>` element and JavaScript to read the value.',
                },
            ),
        ]

        for triggers, examples in request_groups:
            if any(trigger in normalized for trigger in triggers):
                return examples[language]

        hindi_english_triggers = [
            "ka code",
            "ka program",
            "ka example",
            "kaise likhe",
            "kaise banaye",
            "batao code",
            "java me",
            "python me",
            "javascript me",
            "code do",
            "program do",
        ]
        if any(trigger in normalized for trigger in hindi_english_triggers):
            return (
                "Yes, I can give the code directly.\n\n"
                "Bas topic aur language likho, for example:\n"
                "- java me hello world code\n"
                "- python me for loop code\n"
                "- javascript me if else example\n"
                "- java me input wala program\n\n"
                "Phir I will give you the exact code with a short explanation."
            )

        return None

    def _build_learning_fallback(self, question: str, normalized: str) -> str:
        if any(term in normalized for term in ["what is", "meaning", "define"]):
            return self._format_answer(
                "Yes, I can explain that simply.",
                f"The topic `{question.strip()}` can be easier to understand when we break it into basic meaning, simple examples, and where it is used.",
                "If you want, I can explain it like a beginner answer, exam answer, or interview answer."
            )
        if any(term in normalized for term in ["difference", "compare", "vs", "versus"]):
            return self._format_answer(
                "Yes, I can explain the difference clearly.",
                "A strong comparison should show what each thing means, the main difference, where each one is used, and which is better in which situation.",
                "Send me the two exact things you want to compare, and I will explain them simply."
            )
        return self._format_answer(
            "Yes, I can explain that in simple words.",
            "Learning answers are strongest when I know whether you want a beginner explanation, short notes, or an exam-style answer.",
            "Tell me the exact topic or question, and I will explain it in the style you want."
        )

    @staticmethod
    def _build_common_factual_fallback(question: str, normalized: str) -> str | None:
        capitals = {
            "india": "New Delhi",
            "france": "Paris",
            "japan": "Tokyo",
            "usa": "Washington, D.C.",
            "united states": "Washington, D.C.",
            "uk": "London",
            "united kingdom": "London",
            "germany": "Berlin",
            "canada": "Ottawa",
            "australia": "Canberra",
        }
        planets = {
            "largest planet": "Jupiter",
            "smallest planet": "Mercury",
            "red planet": "Mars",
        }

        capital_match = re.search(r"capital of ([a-z ]+)", normalized)
        if capital_match:
            country = capital_match.group(1).strip()
            capital = capitals.get(country)
            if capital:
                return ChatbotService._format_answer(
                    capital,
                    f"{capital} is the capital city of {country.title()}.",
                    "If you want, I can also tell you the country, currency, language, or a short fact about it."
                )

        if "largest planet" in normalized:
            return ChatbotService._format_answer(
                planets["largest planet"],
                "Jupiter is the largest planet in our solar system.",
                "If you want, I can also list all planets in order or compare Jupiter with Earth."
            )

        if "smallest planet" in normalized:
            return ChatbotService._format_answer(
                planets["smallest planet"],
                "Mercury is the smallest planet in our solar system.",
                "If you want, I can also compare Mercury with Earth or give the planet order."
            )

        if "red planet" in normalized:
            return ChatbotService._format_answer(
                planets["red planet"],
                "Mars is called the red planet because of the iron oxide on its surface.",
                "If you want, I can also give a short facts list about Mars."
            )

        if "who invented python" in normalized or "inventor of python" in normalized:
            return ChatbotService._format_answer(
                "Guido van Rossum",
                "Python was created by Guido van Rossum and first released in the early 1990s.",
                "If you want, I can also explain why Python became popular."
            )

        if "who invented java" in normalized or "inventor of java" in normalized:
            return ChatbotService._format_answer(
                "James Gosling",
                "Java was created by James Gosling and his team at Sun Microsystems.",
                "If you want, I can also explain where Java is commonly used."
            )

        if "html stand for" in normalized or "full form of html" in normalized:
            return ChatbotService._format_answer(
                "HyperText Markup Language",
                "HTML stands for HyperText Markup Language and is used to structure web pages.",
                "If you want, I can also explain the difference between HTML, CSS, and JavaScript."
            )

        if "css stand for" in normalized or "full form of css" in normalized:
            return ChatbotService._format_answer(
                "Cascading Style Sheets",
                "CSS stands for Cascading Style Sheets and is used to style web pages.",
                "If you want, I can also explain how CSS works with HTML."
            )

        return None

    def _build_health_fallback(self, normalized: str) -> str:
        if any(term in normalized for term in ["sleep", "tired", "fatigue"]):
            return self._format_answer(
                "Start with the basics: sleep timing, screen use, caffeine, and stress.",
                "Tiredness often improves when the daily routine improves, and those causes are common and practical to check first.",
                "Tell me your sleep pattern and what is happening during the day, and I will help you narrow down the likely cause. If symptoms are strong or persistent, get proper medical advice."
            )
        if any(term in normalized for term in ["weight", "diet", "exercise", "workout"]):
            return self._format_answer(
                "Use a simple routine you can actually continue.",
                "Most people get better results from regular meals, enough protein, walking or basic exercise, and consistency instead of extreme plans.",
                "Tell me your goal like weight loss, strength, or general fitness, and I will help you make a realistic routine."
            )
        return self._format_answer(
            "I can help with general wellness questions in a practical way.",
            "Health and habit questions are easier to solve when we separate the goal, the likely cause, and the safest next step.",
            "Tell me the exact issue, goal, or habit you want to improve, and I will help you make a simple plan."
        )

    def _build_travel_fallback(self, normalized: str) -> str:
        return self._format_answer(
            "Travel planning becomes much easier once the basics are fixed.",
            "The most useful first decisions are budget, number of days, and the kind of trip you want, like relaxing, family, adventure, or sightseeing.",
            "Tell me your budget, how many days you have, and the kind of trip you want, and I will help you build a practical plan."
        )

    def _build_business_fallback(self, normalized: str) -> str:
        if any(term in normalized for term in ["startup", "business idea", "idea"]):
            return self._format_answer(
                "A strong business idea solves a clear problem for a specific group of people.",
                "The best ideas are easier to validate when you know who has the problem, how they solve it today, and why your version is better or simpler.",
                "Tell me your idea, the target users, and what makes it different, and I will help you test whether it is strong."
            )
        return self._format_answer(
            "I can help with business questions in a practical way.",
            "Business problems are easier to solve when we break them into idea, customers, pricing, marketing, and growth instead of treating everything as one problem.",
            "Tell me whether you need help with an idea, customers, marketing, pricing, or growth, and I will break it down clearly."
        )

    def _build_general_rich_fallback(self, question: str, normalized: str, recent_context: str) -> str:
        if recent_context and any(term in normalized for term in ["which one", "which is better", "best one", "what about that", "and this", "that one"]):
            return self._format_answer(
                "The better choice is the one that best matches your goal, budget, and risk level.",
                f"From our recent context, we were talking about: {recent_context}. That context matters because the best answer depends on what we were already comparing.",
                "Send me the two exact options again if you want a direct side-by-side choice."
            )

        if recent_context and any(term in normalized for term in ["continue", "more", "next", "explain more", "tell me more"]):
            return self._format_answer(
                f"We can continue from the recent topic: {recent_context}.",
                "The most useful follow-up is usually to focus on the main decision, the biggest risk, and the next small action instead of restarting from zero.",
                "Tell me which exact part you want me to continue, and I will go deeper from there."
            )

        if any(term in normalized for term in ["confidence", "confident", "fear", "anxious", "nervous", "stress", "stressed"]):
            return (
                "A good first move is not trying to feel perfect. It is usually better to make the situation smaller and easier to handle.\n\n"
                "Try this:\n"
                "1. name the exact thing making you anxious\n"
                "2. prepare one small next step instead of solving everything\n"
                "3. focus on action, not overthinking\n\n"
                "If you want, tell me the exact situation and I will help you handle it in a practical way."
            )

        if any(term in normalized for term in ["money", "save money", "spending", "expense", "expenses", "budget"]):
            return (
                "The fastest improvement usually comes from tracking where money leaks, not from extreme cuts.\n\n"
                "A practical method is:\n"
                "1. list fixed costs first\n"
                "2. find 2 or 3 flexible expenses you can reduce\n"
                "3. set one savings number you can actually maintain\n\n"
                "If you want, send me your monthly income and main expenses and I will help you build a simple budget."
            )

        if any(term in normalized for term in ["focus", "concentrate", "distraction", "lazy", "motivation", "productive", "productivity"]):
            return (
                "A better approach is to reduce friction instead of waiting for motivation.\n\n"
                "Try this simple system:\n"
                "1. choose one clear task\n"
                "2. work for 25 minutes without switching\n"
                "3. remove the main distraction before you start\n"
                "4. stop trying to do too many things at once\n\n"
                "If you want, tell me what you are trying to focus on and I will help you build a routine that fits."
            )

        if any(term in normalized for term in ["plan", "roadmap", "goal", "improve", "better", "grow"]):
            return (
                "A strong plan usually has three parts: the goal, the main obstacle, and the next step.\n\n"
                "A practical way to do it is:\n"
                "1. define the exact result you want\n"
                "2. identify what is blocking you most\n"
                "3. choose the smallest useful action you can take today\n"
                "4. review and adjust after that instead of overplanning\n\n"
                "If you want, tell me the goal and your current situation, and I will help you turn it into a clear plan."
            )

        if any(term in normalized for term in ["career", "job", "future", "skill", "skills", "learn next"]):
            return (
                "The best career decisions usually come from matching three things: your strength, market demand, and the kind of work you actually want to do.\n\n"
                "A practical next step is:\n"
                "1. choose one target role or direction\n"
                "2. list the top 3 skills needed for it\n"
                "3. build one small project or proof of skill\n"
                "4. improve your resume and interview answers around that direction\n\n"
                "If you want, tell me your field and goal, and I will suggest a clearer path."
            )

        if any(term in normalized for term in ["relationship", "friend", "family", "love", "breakup", "argument"]):
            return (
                "The safest approach is to slow the situation down and be clear about what you want from the conversation.\n\n"
                "A useful method is:\n"
                "1. separate what happened from what you felt\n"
                "2. decide whether you want clarity, apology, distance, or repair\n"
                "3. speak calmly and directly instead of reacting fast\n\n"
                "If you want, tell me what happened and I can help you decide what to say next."
            )

        if len(normalized.split()) <= 3:
            return (
                "I can help with that.\n\n"
                "Give me the exact topic, goal, or problem in one line and I will answer more directly. For example:\n"
                "- best phone under 20000\n"
                "- help me write a formal email\n"
                "- how to focus while studying\n"
                "- compare two laptops for coding"
            )

        if any(term in normalized for term in ["what do you think", "your opinion", "is it good", "is it worth", "good or bad"]):
            return (
                "My honest view is this: it depends on what you care about most.\n\n"
                "The easiest way to judge it is to look at the tradeoff between value, risk, and usefulness for your situation. "
                "If you tell me the exact thing you are evaluating, I will give you a more direct opinion."
            )

        if any(term in normalized for term in ["how to", "steps", "process", "guide"]):
            return (
                "I can help with that step by step.\n\n"
                "The best way is usually:\n"
                "1. understand the goal clearly\n"
                "2. break it into small steps\n"
                "3. avoid common mistakes early\n"
                "4. finish with the next action to take\n\n"
                "Tell me the exact task and I will turn it into a clear step-by-step plan."
            )

        return self._format_answer(
            "I can help, but I need the exact situation to give the best answer.",
            "The most accurate answer usually depends on your real goal, your main limit like time or money, and what options you are actually choosing between."
            + (f" This also looks related to our recent chat about {recent_context}." if recent_context else ""),
            "Tell me your exact situation in one or two lines, and I will give you a more direct answer."
        )

    @staticmethod
    def _is_programming_question(normalized: str) -> bool:
        terms = {
            "code",
            "coding",
            "program",
            "programming",
            "python",
            "java",
            "javascript",
            "react",
            "html",
            "css",
            "sql",
            "bug",
            "error",
            "api",
            "function",
            "class",
            "dsa",
            "algorithm",
            "data structure",
        }
        return any(term in normalized for term in terms)

    @staticmethod
    def _is_career_question(normalized: str) -> bool:
        terms = {
            "career",
            "job",
            "resume",
            "cv",
            "interview",
            "offer",
            "promotion",
            "salary",
            "switch",
            "placement",
            "future",
        }
        return any(term in normalized for term in terms)

    @staticmethod
    def _is_study_question(normalized: str) -> bool:
        terms = {
            "study",
            "exam",
            "learn",
            "revision",
            "subject",
            "syllabus",
            "homework",
            "notes",
            "chapter",
            "focus while studying",
        }
        return any(term in normalized for term in terms)

    @staticmethod
    def _is_daily_life_question(normalized: str) -> bool:
        terms = {
            "habit",
            "routine",
            "discipline",
            "sleep",
            "stress",
            "anxiety",
            "lonely",
            "confused",
            "decision",
            "daily life",
            "motivation",
            "focus",
            "productive",
        }
        return any(term in normalized for term in terms)

    @staticmethod
    def _recent_user_context(history: list[dict[str, str]]) -> str:
        recent_user_messages = [
            item.get("content", "").strip()
            for item in history[-12:]
            if item.get("role") == "user" and item.get("content", "").strip()
        ]
        if not recent_user_messages:
            return ""
        joined = " | ".join(recent_user_messages[-5:])
        return shorten(joined, width=280, placeholder="...")

    @staticmethod
    def _merge_with_recent_context(normalized: str, recent_context: str) -> str:
        if not recent_context:
            return normalized
        follow_up_triggers = {
            "which one",
            "which is better",
            "best one",
            "what about",
            "and this",
            "that one",
            "this one",
            "better one",
            "continue",
            "more",
            "next",
            "explain more",
            "tell me more",
            "can you explain",
            "what about",
            "and now",
            "then what",
            "so what",
        }
        if any(trigger in normalized for trigger in follow_up_triggers):
            return f"{recent_context.lower()} {normalized}"
        return normalized

    def _build_comparison_answer(self, products) -> str:
        left, right = products[0], products[1]
        comparison_lines = [
            f"Short Answer: {left.name} and {right.name} are both good, but they fit different needs.",
            "",
            "Why:",
            f"- {left.name}: Rs {left.price:,}, rating {left.rating:.1f}/5, best for {self._comparison_reason(left)}.",
            f"- {right.name}: Rs {right.price:,}, rating {right.rating:.1f}/5, best for {self._comparison_reason(right)}.",
            "",
            f"Pros of {left.name}:",
            f"- {left.tag}",
            f"- {', '.join(left.features[:2])}" if left.features else "- Balanced overall option",
            "",
            f"Pros of {right.name}:",
            f"- {right.tag}",
            f"- {', '.join(right.features[:2])}" if right.features else "- Strong alternative option",
        ]
        winner = left if (left.rating, -left.price) >= (right.rating, -right.price) else right
        comparison_lines.extend(
            [
                "",
                f"Next Step: If you want the safer overall pick, I would start with {winner.name}. If you tell me your priority like camera, gaming, battery, or value, I can pick one more confidently.",
            ]
        )
        return "\n".join(comparison_lines)

    def _match_products_from_text(self, question: str):
        normalized = question.lower()
        matches = []
        for product in self.product_catalog.products:
            name = product.name.lower()
            brand = product.brand.lower()
            if name in normalized or (brand in normalized and any(part in normalized for part in name.split())):
                matches.append(product)
        return matches

    @staticmethod
    def _looks_like_comparison_request(normalized: str) -> bool:
        return any(term in normalized for term in ["compare", "vs", "versus", "difference between"])

    @staticmethod
    def _is_support_question(normalized: str) -> bool:
        support_terms = {
            "refund",
            "password",
            "login",
            "otp",
            "shipping",
            "order",
            "billing",
            "charged",
            "return",
            "cancel",
            "address",
            "delivery",
            "invoice",
            "account",
        }
        return any(term in normalized for term in support_terms)

    @staticmethod
    def _is_product_question(normalized: str) -> bool:
        product_terms = {
            "phone",
            "smartphone",
            "mobile",
            "laptop",
            "tablet",
            "watch",
            "smartwatch",
            "earbud",
            "earbuds",
            "headphone",
            "accessory",
            "buy",
            "purchase",
            "recommend",
            "suggest",
            "best",
            "budget",
            "under",
            "show me",
        }
        return any(term in normalized for term in product_terms)

    @staticmethod
    def _detect_product_category(normalized: str) -> str | None:
        if any(term in normalized for term in ["earbud", "earbuds", "headphone", "accessory"]):
            return "accessory"
        if any(term in normalized for term in ["laptop", "notebook"]):
            return "laptop"
        if any(term in normalized for term in ["tablet", "tab", "ipad"]):
            return "tablet"
        if any(term in normalized for term in ["watch", "smartwatch", "wearable"]):
            return "watch"
        if any(term in normalized for term in ["phone", "mobile", "smartphone"]):
            return "phone"
        return None

    @staticmethod
    def _extract_budget(normalized: str) -> int | None:
        match = re.search(r"(\d[\d,]{3,})", normalized)
        if not match:
            return None
        try:
            return int(match.group(1).replace(",", ""))
        except ValueError:
            return None

    @staticmethod
    def _extract_priority(normalized: str) -> str | None:
        priorities = [
            "camera",
            "gaming",
            "battery",
            "display",
            "performance",
            "study",
            "coding",
            "office",
            "travel",
            "fitness",
            "music",
        ]
        for priority in priorities:
            if priority in normalized:
                return priority
        return None

    @staticmethod
    def _product_reason(product, priority_hint: str) -> str:
        text = f"{product.tag} {' '.join(product.features)} {product.description}".lower()
        if "camera" in priority_hint and ("camera" in text or "ois" in text):
            return f"A strong camera-focused option with {product.tag.lower()} positioning and useful imaging features."
        if "gaming" in priority_hint and ("gaming" in text or "refresh" in text or "chipset" in text):
            return f"A better gaming fit because it leans into smooth performance and display responsiveness."
        if "battery" in priority_hint and "battery" in text:
            return f"A good pick if battery life matters because it highlights stronger battery-focused features."
        if "display" in priority_hint and "display" in text:
            return f"A nice display-first option with screen-focused features that stand out."
        return f"It stands out for {product.tag.lower()} and has a solid {product.rating:.1f}/5 rating."

    @staticmethod
    def _comparison_reason(product) -> str:
        text = f"{product.tag} {' '.join(product.features)} {product.description}".lower()
        if "gaming" in text:
            return "gaming and smoother high-refresh performance"
        if "camera" in text or "ois" in text:
            return "camera quality and balanced daily use"
        if "battery" in text:
            return "battery life and reliability"
        if "audio" in text or "anc" in text:
            return "portable audio and everyday listening"
        return product.tag.lower()

    @staticmethod
    def _is_problem_solving_question(normalized: str) -> bool:
        triggers = {
            "problem",
            "issue",
            "stuck",
            "confused",
            "decide",
            "choose",
            "should i",
            "what should i do",
            "not sure",
            "help me plan",
            "study",
            "exam",
            "job",
            "career",
            "interview",
            "resume",
            "money",
            "budget",
            "save",
            "schedule",
            "routine",
            "overwhelmed",
            "message them",
            "family",
            "friend",
            "relationship",
        }
        return any(trigger in normalized for trigger in triggers)

    @staticmethod
    def _build_sources(entries: list[KnowledgeEntry]) -> list[Source]:
        return [Source(title=entry.title, snippet=shorten(entry.content, width=150, placeholder="...")) for entry in entries[:3]]

    @staticmethod
    def _build_product_sources(products) -> list[Source]:
        return [
            Source(title=product.name, snippet=f"Rs {product.price} | {product.tag} | {shorten(product.description, width=90, placeholder='...')}")
            for product in products[:3]
        ]

    def _build_combined_sources(self, entries: list[KnowledgeEntry], products, document_matches: list[dict[str, str]] | None = None) -> list[Source]:
        sources = self._build_product_sources(products)
        for item in self._build_sources(entries):
            if len(sources) >= 4:
                break
            sources.append(item)
        for item in document_matches or []:
            if len(sources) >= 4:
                break
            sources.append(Source(title=f"Document: {item['name']}", snippet=item["snippet"]))
        return sources

    @staticmethod
    def _retrieve_uploaded_documents(question: str, uploaded_documents: list[dict[str, str]], limit: int = 2) -> list[dict[str, str]]:
        query_terms = set(re.findall(r"[a-z0-9']+", question.lower()))
        if not query_terms:
            return []
        scored: list[tuple[int, dict[str, str]]] = []
        for item in uploaded_documents:
            content = f"{item.get('name', '')} {item.get('text', '')}".lower()
            haystack = set(re.findall(r"[a-z0-9']+", content))
            overlap = len(query_terms & haystack)
            if overlap > 0:
                snippet = shorten(item.get("text", "").replace("\n", " "), width=220, placeholder="...")
                scored.append((overlap, {"name": item.get("name", "document"), "snippet": snippet}))
        scored.sort(key=lambda value: value[0], reverse=True)
        return [item for _, item in scored[:limit]]
