from dataclasses import dataclass, field
from decimal import Decimal
from typing import Optional
from enum import Enum


class OrderSide(str, Enum):
    BUY = "BUY"
    SELL = "SELL"


class OrderType(str, Enum):
    MARKET = "MARKET"
    LIMIT = "LIMIT"
    TWAP = "TWAP"


class OrderStatus(str, Enum):
    NEW = "NEW"
    PARTIALLY_FILLED = "PARTIALLY_FILLED"
    FILLED = "FILLED"
    CANCELED = "CANCELED"
    REJECTED = "REJECTED"
    EXPIRED = "EXPIRED"
    UNKNOWN = "UNKNOWN"


@dataclass
class OrderRequest:
    symbol: str
    side: OrderSide
    order_type: OrderType
    quantity: Decimal
    price: Optional[Decimal] = None
    time_in_force: str = "GTC"
    twap_slices: int = 5
    twap_interval_seconds: int = 30

    def to_dict(self) -> dict:
        return {
            "symbol": self.symbol,
            "side": self.side.value,
            "type": self.order_type.value,
            "quantity": str(self.quantity),
            "price": str(self.price) if self.price else None,
            "time_in_force": self.time_in_force,
        }


@dataclass
class OrderResponse:
    order_id: int
    client_order_id: str
    symbol: str
    side: str
    order_type: str
    status: str
    orig_qty: str
    executed_qty: str
    avg_price: str
    price: str
    time_in_force: str
    raw: dict = field(default_factory=dict, repr=False)

    @classmethod
    def from_api(cls, data: dict) -> "OrderResponse":
        return cls(
            order_id=data.get("orderId", 0),
            client_order_id=data.get("clientOrderId", ""),
            symbol=data.get("symbol", ""),
            side=data.get("side", ""),
            order_type=data.get("type", ""),
            status=data.get("status", "UNKNOWN"),
            orig_qty=data.get("origQty", "0"),
            executed_qty=data.get("executedQty", "0"),
            avg_price=data.get("avgPrice", data.get("price", "0")),
            price=data.get("price", "0"),
            time_in_force=data.get("timeInForce", ""),
            raw=data,
        )

    def to_dict(self) -> dict:
        return {
            "order_id": self.order_id,
            "client_order_id": self.client_order_id,
            "symbol": self.symbol,
            "side": self.side,
            "type": self.order_type,
            "status": self.status,
            "orig_qty": self.orig_qty,
            "executed_qty": self.executed_qty,
            "avg_price": self.avg_price,
            "price": self.price,
            "time_in_force": self.time_in_force,
        }


@dataclass
class TWAPResult:
    symbol: str
    side: str
    total_qty: Decimal
    slices_requested: int
    slices_filled: int
    responses: list[OrderResponse] = field(default_factory=list)

    @property
    def success_rate(self) -> float:
        if self.slices_requested == 0:
            return 0.0
        return self.slices_filled / self.slices_requested * 100
