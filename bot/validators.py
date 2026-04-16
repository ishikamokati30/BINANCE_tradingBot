import re
from decimal import Decimal, InvalidOperation
from typing import Optional

from bot.exceptions import ValidationError
from bot.models import OrderSide, OrderType


SYMBOL_PATTERN = re.compile(r"^[A-Z]{2,20}$")

MIN_QUANTITY = Decimal("0.001")
MAX_QUANTITY = Decimal("1000")

MIN_PRICE = Decimal("0.01")
MAX_PRICE = Decimal("10_000_000")


def validate_symbol(symbol: str) -> str:
    if not symbol:
        raise ValidationError("Symbol must not be empty.")
    normalised = symbol.strip().upper()
    if not SYMBOL_PATTERN.match(normalised):
        raise ValidationError(
            f"Invalid symbol '{symbol}'. Must be uppercase letters only (e.g. BTCUSDT).",
            details={"symbol": symbol},
        )
    return normalised


def validate_side(side: str) -> OrderSide:
    try:
        return OrderSide(side.strip().upper())
    except ValueError:
        raise ValidationError(
            f"Invalid side '{side}'. Must be BUY or SELL.",
            details={"side": side, "valid_values": ["BUY", "SELL"]},
        )


def validate_order_type(order_type: str) -> OrderType:
    try:
        return OrderType(order_type.strip().upper())
    except ValueError:
        raise ValidationError(
            f"Invalid order type '{order_type}'. Must be MARKET, LIMIT, or TWAP.",
            details={"order_type": order_type, "valid_values": ["MARKET", "LIMIT", "TWAP"]},
        )


def validate_quantity(quantity: str | float | Decimal) -> Decimal:
    try:
        qty = Decimal(str(quantity))
    except (InvalidOperation, ValueError):
        raise ValidationError(
            f"Invalid quantity '{quantity}'. Must be a positive number.",
            details={"quantity": str(quantity)},
        )
    if qty <= 0:
        raise ValidationError(
            f"Quantity must be greater than zero, got {qty}.",
            details={"quantity": str(qty)},
        )
    if qty < MIN_QUANTITY:
        raise ValidationError(
            f"Quantity {qty} is below the minimum allowed ({MIN_QUANTITY}).",
            details={"quantity": str(qty), "minimum": str(MIN_QUANTITY)},
        )
    if qty > MAX_QUANTITY:
        raise ValidationError(
            f"Quantity {qty} exceeds the maximum allowed ({MAX_QUANTITY}).",
            details={"quantity": str(qty), "maximum": str(MAX_QUANTITY)},
        )
    return qty


def validate_price(price: str | float | Decimal | None, order_type: OrderType) -> Optional[Decimal]:
    if order_type == OrderType.MARKET:
        return None

    if order_type == OrderType.TWAP:
        return None
    if price is None or str(price).strip() == "":
        raise ValidationError(
            "Price is required for LIMIT orders.",
            details={"order_type": order_type.value},
        )
    try:
        p = Decimal(str(price))
    except (InvalidOperation, ValueError):
        raise ValidationError(
            f"Invalid price '{price}'. Must be a positive number.",
            details={"price": str(price)},
        )
    if p <= 0:
        raise ValidationError(
            f"Price must be greater than zero, got {p}.",
            details={"price": str(p)},
        )
    if p < MIN_PRICE:
        raise ValidationError(
            f"Price {p} is below the minimum allowed ({MIN_PRICE}).",
        )
    if p > MAX_PRICE:
        raise ValidationError(
            f"Price {p} exceeds the maximum allowed ({MAX_PRICE}).",
        )
    return p


def validate_twap_params(slices: int, interval: int) -> tuple[int, int]:
    if slices < 2 or slices > 20:
        raise ValidationError(
            f"TWAP slices must be between 2 and 20, got {slices}.",
            details={"slices": slices},
        )
    if interval < 5 or interval > 300:
        raise ValidationError(
            f"TWAP interval must be between 5 and 300 seconds, got {interval}.",
            details={"interval_seconds": interval},
        )
    return slices, interval
