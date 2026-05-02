from __future__ import annotations

import re


class IntentClassifier:
    PRODUCT_KEYWORDS = {
        "buy", "price", "best", "recommend", "budget", "phone", "mobile", "laptop", "tablet", "watch",
        "smartwatch", "camera", "gaming", "battery", "display", "product",
    }
    SUPPORT_KEYWORDS = {
        "refund", "order", "login", "password", "shipping", "delivery", "otp", "billing", "cancel",
        "return", "account", "invoice", "charged", "address",
    }
    CODING_KEYWORDS = {
        "code", "python", "java", "javascript", "react", "html", "css", "error", "bug", "api", "sql",
        "program", "coding", "function", "class", "dsa", "algorithm",
    }

    def detect(self, text: str, mode: str = "general") -> str:
        normalized = (text or "").lower()
        words = set(re.findall(r"[a-z0-9_+#.-]+", normalized))

        if mode == "support":
            return "support"

        def score(keywords: set[str]) -> int:
            return sum(2 if token in words else 1 for token in keywords if token in normalized)

        scores = {
            "product": score(self.PRODUCT_KEYWORDS),
            "support": score(self.SUPPORT_KEYWORDS),
            "coding": score(self.CODING_KEYWORDS),
        }
        best_intent = max(scores, key=scores.get)
        if scores[best_intent] > 0:
            return best_intent
        return "general"


__all__ = ["IntentClassifier"]
