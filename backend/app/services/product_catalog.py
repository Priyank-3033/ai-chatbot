from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path


@dataclass
class Product:
    id: str
    name: str
    brand: str
    category: str
    sku: str
    price: int
    rating: float
    storage: str
    tag: str
    image: str
    gallery: list[str]
    description: str
    long_description: str
    features: list[str]
    specs: dict[str, str]
    stock: int
    delivery_note: str


class ProductCatalogService:
    def __init__(self, data_path: Path) -> None:
        self.data_path = data_path
        self.products = self._load_products()

    def _load_products(self) -> list[Product]:
        raw_items = json.loads(self.data_path.read_text(encoding="utf-8"))
        items: list[Product] = []
        for item in raw_items:
            normalized = {
                "id": item["id"],
                "name": item["name"],
                "brand": item["brand"],
                "category": item["category"],
                "sku": item.get("sku", item["id"].upper()),
                "price": item["price"],
                "rating": item["rating"],
                "storage": item.get("storage", "-"),
                "tag": item.get("tag", "Featured"),
                "image": item["image"],
                "gallery": item.get("gallery") or [item["image"]],
                "description": item["description"],
                "long_description": item.get("long_description", item["description"]),
                "features": item.get("features", []),
                "specs": item.get("specs", {}),
                "stock": item.get("stock", 10),
                "delivery_note": item.get("delivery_note", "Fast delivery available"),
            }
            items.append(Product(**normalized))
        return items

    def _save(self) -> None:
        self.data_path.write_text(
            json.dumps([asdict(product) for product in self.products], indent=2),
            encoding="utf-8",
        )

    def list_products(self, category: str | None = None, search: str | None = None) -> list[Product]:
        items = self.products
        if category:
            items = [item for item in items if item.category == category]
        if search:
            needle = search.lower().strip()
            items = [
                item
                for item in items
                if needle in item.name.lower()
                or needle in item.brand.lower()
                or needle in item.description.lower()
                or needle in item.long_description.lower()
                or needle in item.sku.lower()
                or any(needle in feature.lower() for feature in item.features)
                or any(needle in value.lower() for value in item.specs.values())
            ]
        return items

    def get_product(self, product_id: str) -> Product | None:
        for product in self.products:
            if product.id == product_id:
                return product
        return None

    def recommend_products(self, question: str, limit: int = 3) -> list[Product]:
        normalized = question.lower()
        products = self.products

        budget = self._extract_budget(normalized)
        if budget:
            products = [product for product in products if product.price <= budget]

        if "earbud" in normalized or "audio" in normalized or "headphone" in normalized:
            products = [product for product in products if product.category == "accessory"] or products
        elif "laptop" in normalized or "notebook" in normalized:
            products = [product for product in products if product.category == "laptop"] or products
        elif "tablet" in normalized or "tab" in normalized or "ipad" in normalized:
            products = [product for product in products if product.category == "tablet"] or products
        elif "watch" in normalized or "smartwatch" in normalized or "wearable" in normalized:
            products = [product for product in products if product.category == "watch"] or products
        elif "phone" in normalized or "mobile" in normalized or "smartphone" in normalized:
            products = [product for product in products if product.category == "phone"] or products

        if "camera" in normalized:
            products = sorted(products, key=lambda product: ("camera" in product.tag.lower() or any("camera" in feature.lower() for feature in product.features), product.rating, -product.price), reverse=True)
        elif "gaming" in normalized or "game" in normalized:
            products = sorted(products, key=lambda product: ("gaming" in product.tag.lower() or any("gaming" in feature.lower() for feature in product.features), product.rating, -product.price), reverse=True)
        elif "battery" in normalized:
            products = sorted(products, key=lambda product: (any("battery" in feature.lower() for feature in product.features), product.rating, -product.price), reverse=True)
        else:
            products = sorted(products, key=lambda product: (product.rating, -product.price), reverse=True)

        return products[:limit]

    def upsert_product(self, payload: dict) -> Product:
        product = Product(**payload)
        for index, item in enumerate(self.products):
            if item.id == product.id:
                self.products[index] = product
                self._save()
                return product
        self.products.append(product)
        self._save()
        return product

    def delete_product(self, product_id: str) -> bool:
        original_count = len(self.products)
        self.products = [product for product in self.products if product.id != product_id]
        if len(self.products) == original_count:
            return False
        self._save()
        return True

    @staticmethod
    def _extract_budget(text: str) -> int | None:
        digits = []
        current = ""
        for char in text:
            if char.isdigit():
                current += char
            elif current:
                digits.append(current)
                current = ""
        if current:
            digits.append(current)
        if not digits:
            return None
        try:
            return int(digits[0])
        except ValueError:
            return None
