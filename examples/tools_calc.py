"""Small example tool registry: calculator + lookup."""
from aek.tools import ToolRegistry, tool


_PRICES = {
    "apple": 5.0, "banana": 3.5, "orange": 7.0,
    "grape": 12.0, "watermelon": 25.0,
}


@tool(description="Add two numbers")
def add(a: float, b: float) -> float:
    return a + b


@tool(description="Multiply two numbers")
def mul(a: float, b: float) -> float:
    return a * b


@tool(description="Look up the unit price of a fruit in yuan/kg")
def get_price(fruit: str) -> float:
    return _PRICES.get(fruit.lower(), -1)


registry = (
    ToolRegistry()
    .register(add)
    .register(mul)
    .register(get_price)
)
