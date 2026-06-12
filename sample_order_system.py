"""A small ordering system — used for testing Codebase Shaker."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class Product:
    """Represents a product in the catalog."""

    name: str
    price: float
    stock: int

    def is_available(self) -> bool:
        return self.stock > 0

    def reduce_stock(self, quantity: int) -> None:
        if quantity > self.stock:
            raise ValueError(f"Only {self.stock} left in stock")
        self.stock -= quantity


@dataclass
class OrderLine:
    """One line item in an order."""

    product: Product
    quantity: int

    def total(self) -> float:
        return self.product.price * self.quantity


@dataclass
class Order:
    """A customer order."""

    customer: str
    lines: list[OrderLine] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)

    def add_item(self, product: Product, quantity: int) -> None:
        if not product.is_available():
            raise ValueError(f"{product.name} is out of stock")
        product.reduce_stock(quantity)
        self.lines.append(OrderLine(product, quantity))

    def total(self) -> float:
        return sum(line.total() for line in self.lines)

    def summary(self) -> str:
        lines_str = "\n".join(
            f"  - {line.product.name} x{line.quantity} = ${line.total():.2f}"
            for line in self.lines
        )
        return f"Order for {self.customer}:\n{lines_str}\nTotal: ${self.total():.2f}"


class Catalog:
    """Holds all available products."""

    def __init__(self) -> None:
        self._products: dict[str, Product] = {}

    def add(self, product: Product) -> None:
        self._products[product.name] = product

    def get(self, name: str) -> Product:
        if name not in self._products:
            raise KeyError(f"Product '{name}' not found")
        return self._products[name]

    def list_available(self) -> list[Product]:
        return [p for p in self._products.values() if p.is_available()]


def place_order(catalog: Catalog, customer: str, items: list[tuple[str, int]]) -> Order:
    """High-level helper: look up products and build an order."""
    order = Order(customer=customer)
    for product_name, qty in items:
        product = catalog.get(product_name)
        order.add_item(product, qty)
    return order


if __name__ == "__main__":
    catalog = Catalog()
    catalog.add(Product("Widget", 9.99, 100))
    catalog.add(Product("Gadget", 24.99, 50))
    catalog.add(Product("Gizmo", 49.99, 0))

    order = place_order(catalog, "Alice", [("Widget", 2), ("Gadget", 1)])
    print(order.summary())
