from __future__ import annotations

import re
from textwrap import shorten

from openai import OpenAI
from openai import OpenAIError

from app.config import Settings
from app.models import ChatResponse, Source
from app.services.knowledge_base import KnowledgeBaseService, KnowledgeEntry
from app.services.product_catalog import ProductCatalogService


GENERAL_SYSTEM_PROMPT = """
You are a warm, natural, user-friendly AI assistant.
You can help with general questions, ecommerce shopping guidance, and customer support topics in one chat.
Speak like a helpful real person, not like a documentation search engine.
Be clear, practical, and direct.
Answer first, then guide.
If the user is vague, make a reasonable assumption, give a helpful starting answer, and ask one useful follow-up question.
If the user asks for suggestions, recommend 2 or 3 options with short reasons.
If the user is solving a problem, help them think clearly: name the likely issue, give practical options, recommend the best next step, and keep it easy to follow.
When product context is relevant, use it directly in your answer.
When support knowledge is relevant, use it naturally without sounding robotic.
Avoid policy-dump language.
Do not talk about "retrieved context", "knowledge base", or "matched sources".
""".strip()

SUPPORT_SYSTEM_PROMPT = """
You are a warm and helpful customer support AI.
Speak clearly and naturally, like a real support teammate.
Answer using the retrieved knowledge base whenever possible.
If the answer is unclear or missing, say that honestly and suggest the next best action.
When helpful, ask one short clarifying question instead of dumping policy text.
Lead with the answer in simple words, then give the next step.
Keep answers concise, practical, and friendly.
""".strip()


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

    def _build_client(self) -> OpenAI | None:
        if not self.settings.openai_api_key:
            return None
        return OpenAI(api_key=self.settings.openai_api_key, max_retries=0, timeout=8.0)

    def answer(self, question: str, history: list[dict[str, str]], mode: str = "general") -> ChatResponse:
        chat_mode = mode if mode in {"general", "support"} else "general"
        entries = self.knowledge_base.retrieve(question) if chat_mode == "support" else self.knowledge_base.retrieve(question, limit=3)
        products = self.product_catalog.recommend_products(question, limit=3) if chat_mode == "general" else []
        sources = self._build_sources(entries) if chat_mode == "support" else self._build_combined_sources(entries, products)
        if self.client:
            try:
                answer = self._generate_llm_answer(question, history, entries, products, chat_mode)
                result_mode = f"llm+{chat_mode}"
            except OpenAIError:
                answer = self._generate_fallback_answer(question, entries, products, chat_mode)
                result_mode = f"fallback+{chat_mode}"
        else:
            answer = self._generate_fallback_answer(question, entries, products, chat_mode)
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

    def _generate_llm_answer(
        self,
        question: str,
        history: list[dict[str, str]],
        entries: list[KnowledgeEntry],
        products,
        mode: str,
    ) -> str:
        system_prompt = SUPPORT_SYSTEM_PROMPT if mode == "support" else GENERAL_SYSTEM_PROMPT
        kb_context = "\n\n".join(f"{entry.title}: {entry.content}" for entry in entries)
        product_context = "\n".join(
            f"- {product.name} ({product.brand}) - Rs {product.price}, {product.tag}, {product.description}"
            for product in products
        )
        history_text = "\n".join(
            f"{item.get('role', 'user')}: {item.get('content', '')}"
            for item in history[-6:]
            if item.get("content")
        )
        mode_line = (
            "User selected customer support mode. Prioritize support policy and action-oriented guidance."
            if mode == "support"
            else "User selected unified AI mode. Answer broadly and naturally. Help with shopping, support, and general questions in one conversation."
        )
        response = self.client.responses.create(
            model=self.settings.openai_model,
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
                                f"Product context:\n{product_context or 'No relevant products matched.'}\n\n"
                                f"Knowledge base context:\n{kb_context or 'No matched support context.'}"
                            ),
                        }
                    ],
                },
            ],
        )
        return getattr(response, "output_text", None) or self._generate_fallback_answer(question, entries, products, mode)

    def _generate_fallback_answer(self, question: str, entries: list[KnowledgeEntry], products, mode: str) -> str:
        normalized = question.lower().strip()
        compact = re.sub(r"\s+", " ", normalized)

        if mode == "general":
            if self._looks_like_comparison_request(compact):
                matched_products = self._match_products_from_text(question)
                if len(matched_products) >= 2:
                    return self._build_comparison_answer(matched_products[:2])

            if self._is_support_question(compact) and entries:
                return self._build_support_fallback(entries, compact)

            if self._is_product_question(compact):
                return self._build_product_fallback(question, compact, products)

            if self._is_problem_solving_question(compact):
                return self._build_problem_solving_fallback(compact)

            if compact in {"hi", "hello", "hey", "good morning", "good evening"}:
                return (
                    "Hello. I am ready to help.\n\n"
                    "You can ask me for product suggestions, order help, support guidance, writing help, coding help, or everyday answers."
                )
            if "help" in normalized and len(normalized.split()) <= 4:
                return (
                    "Of course. I can help with a lot of things.\n\n"
                    "You can ask me things like:\n"
                    "- show me good phones under 20000\n"
                    "- compare two products\n"
                    "- explain an order or refund issue\n"
                    "- suggest earbuds for daily use\n"
                    "- explain a topic simply\n"
                    "- help me write a message\n\n"
                    "Just tell me what you want to do."
                )
            if any(term in compact for term in ["write", "message", "email", "caption", "bio", "paragraph", "resume"]):
                return (
                    "Yes, I can help with that.\n\n"
                    "Tell me what you want to write, who it is for, and the tone you want. If you already have a draft, paste it here and I will improve it."
                )
            if any(term in compact for term in ["code", "python", "java", "javascript", "react", "html", "css", "bug", "error", "program"]):
                return (
                    "Yes, I can help with coding too.\n\n"
                    "Send me the code, error message, or the result you want, and I will explain it or help you fix it step by step."
                )
            if any(term in compact for term in ["study", "learn", "explain", "meaning", "what is", "how does"]):
                return (
                    "Sure. I can explain topics in simple words.\n\n"
                    "Tell me the exact topic or question, and if you want, I can explain it like a beginner, student, or interview answer."
                )
            return (
                "I can help with that.\n\n"
                "Tell me the exact outcome you want, and I will give you a clearer answer. For example, you can tell me what you want to buy, fix, write, understand, or compare."
            )

        if "help" in normalized and len(normalized.split()) <= 4:
            return (
                "Of course. I can help with refunds, billing, login issues, order updates, shipping, and account access.\n\n"
                "Tell me your issue in one sentence, like:\n"
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
        return self._build_support_fallback(entries, compact)

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
                    "I do not have a strong match from the catalog yet, so tell me one more preference like battery, display, camera, gaming, or brand, and I will narrow it down better."
                )
            if budget:
                return (
                    f"I can help you find {category_label} under Rs {budget:,}.\n\n"
                    "Tell me what matters most, like camera, gaming, battery, display, work, or portability, and I will guide you better."
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
            lines.append(
                f"{index}. {product.name} by {product.brand} - Rs {product.price:,}. {reason}"
            )

        follow_up = "If you want, I can narrow this down to one best pick for your budget."
        if category == "phone":
            follow_up = "If you want, I can narrow this down by camera, gaming, battery, or display."
        elif category == "laptop":
            follow_up = "If you want, I can narrow this down for study, coding, office work, or gaming."

        return f"{intro}\n\n" + "\n".join(lines) + f"\n\n{follow_up}"

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
                "3. keep one short revision block at the end of each day\n\n"
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

        if any(term in normalized for term in ["should i", "what should i do", "decide", "choose", "confused", "stuck", "problem", "issue"]):
            return (
                "I can help you work through it.\n\n"
                "The easiest way is:\n"
                "1. say what the real problem is\n"
                "2. list the main options\n"
                "3. check what matters most right now\n"
                "4. pick the next small step instead of solving everything at once\n\n"
                "Tell me the situation in one or two lines, and I will help you think it through clearly."
            )

        return (
            "Yes, I can help with real-life problem solving too.\n\n"
            "If you tell me the situation clearly, I can help you break it down, compare options, and decide the best next step."
        )

    def _build_comparison_answer(self, products) -> str:
        left, right = products[0], products[1]
        comparison_lines = [
            f"{left.name} vs {right.name}:",
            f"- Price: Rs {left.price:,} vs Rs {right.price:,}",
            f"- Rating: {left.rating:.1f}/5 vs {right.rating:.1f}/5",
            f"- Best for: {self._comparison_reason(left)}",
            f"- Alternative: {self._comparison_reason(right)}",
        ]
        winner = left if (left.rating, -left.price) >= (right.rating, -right.price) else right
        comparison_lines.append(f"\nIf you want the safer overall pick, I would start with {winner.name}.")
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

    def _build_combined_sources(self, entries: list[KnowledgeEntry], products) -> list[Source]:
        sources = self._build_product_sources(products)
        for item in self._build_sources(entries):
            if len(sources) >= 4:
                break
            sources.append(item)
        return sources
