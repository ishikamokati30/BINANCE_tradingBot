import time
from decimal import Decimal

from bot.client import BinanceFuturesClient
from bot.exceptions import BinanceAPIError, NetworkError
from bot.logging_config import get_logger
from bot.models import OrderRequest, OrderResponse, OrderType, TWAPResult


logger = get_logger("orders")


class OrderService:

    def __init__(self, client: BinanceFuturesClient):
        self._client = client

    def place(self, request: OrderRequest) -> OrderResponse | TWAPResult:
        logger.info(
            "Placing order",
            extra={"order_request": request.to_dict()},
        )

        if request.order_type == OrderType.MARKET:
            return self._place_market(request)
        elif request.order_type == OrderType.LIMIT:
            return self._place_limit(request)
        elif request.order_type == OrderType.TWAP:
            return self._place_twap(request)
        else:
            raise ValueError(f"Unsupported order type: {request.order_type}")

    def _place_market(self, request: OrderRequest) -> OrderResponse:
        params = {
            "symbol": request.symbol,
            "side": request.side.value,
            "type": "MARKET",
            "quantity": str(request.quantity),
        }
        try:
            raw = self._client.place_order(params)
            response = OrderResponse.from_api(raw)
            logger.info(
                "Market order placed successfully",
                extra={
                    "order_id": response.order_id,
                    "status": response.status,
                    "executed_qty": response.executed_qty,
                    "avg_price": response.avg_price,
                },
            )
            return response
        except (BinanceAPIError, NetworkError) as exc:
            logger.error(
                "Market order failed",
                extra={"error": str(exc), "details": exc.details},
            )
            raise

    def _place_limit(self, request: OrderRequest) -> OrderResponse:
        params = {
            "symbol": request.symbol,
            "side": request.side.value,
            "type": "LIMIT",
            "quantity": str(request.quantity),
            "price": str(request.price),
            "timeInForce": request.time_in_force,
        }
        try:
            raw = self._client.place_order(params)
            response = OrderResponse.from_api(raw)
            logger.info(
                "Limit order placed successfully",
                extra={
                    "order_id": response.order_id,
                    "status": response.status,
                    "price": response.price,
                    "orig_qty": response.orig_qty,
                },
            )
            return response
        except (BinanceAPIError, NetworkError) as exc:
            logger.error(
                "Limit order failed",
                extra={"error": str(exc), "details": exc.details},
            )
            raise

    def _place_twap(self, request: OrderRequest) -> TWAPResult:
        n = request.twap_slices
        interval = request.twap_interval_seconds
        slice_qty = (request.quantity / Decimal(n)).quantize(Decimal("0.001"))

        result = TWAPResult(
            symbol=request.symbol,
            side=request.side.value,
            total_qty=request.quantity,
            slices_requested=n,
            slices_filled=0,
        )

        logger.info(
            "Starting TWAP execution",
            extra={
                "symbol": request.symbol,
                "side": request.side.value,
                "total_qty": str(request.quantity),
                "slices": n,
                "slice_qty": str(slice_qty),
                "interval_seconds": interval,
            },
        )

        for i in range(1, n + 1):
            logger.info(
                f"TWAP slice {i}/{n}",
                extra={
                    "slice": i,
                    "total_slices": n,
                    "slice_qty": str(slice_qty),
                    "symbol": request.symbol,
                },
            )
            try:
                slice_request = OrderRequest(
                    symbol=request.symbol,
                    side=request.side,
                    order_type=OrderType.MARKET,
                    quantity=slice_qty,
                )
                response = self._place_market(slice_request)
                result.responses.append(response)
                result.slices_filled += 1
            except Exception as exc:
                logger.warning(
                    f"TWAP slice {i} failed, continuing",
                    extra={"slice": i, "error": str(exc)},
                )

            if i < n:
                time.sleep(interval)

        logger.info(
            "TWAP execution complete",
            extra={
                "slices_filled": result.slices_filled,
                "slices_requested": result.slices_requested,
                "success_rate_pct": f"{result.success_rate:.1f}",
            },
        )
        return result
