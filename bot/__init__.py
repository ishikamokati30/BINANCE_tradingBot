"""
trading_bot.bot — core application package.

Public surface:
    BinanceFuturesClient  — HTTP adapter for Binance Futures Testnet
    OrderService          — order placement business logic
    OrderRequest          — input DTO
    OrderResponse         — output DTO
    TWAPResult            — TWAP execution result
"""
__version__ = "1.0.0"

from bot.client import BinanceFuturesClient
from bot.orders import OrderService
from bot.models import OrderRequest, OrderResponse, TWAPResult, OrderSide, OrderType

__all__ = [
    "BinanceFuturesClient",
    "OrderService",
    "OrderRequest",
    "OrderResponse",
    "TWAPResult",
    "OrderSide",
    "OrderType",
]
