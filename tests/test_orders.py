from decimal import Decimal
from unittest.mock import MagicMock, patch, call
import pytest

from bot.models import OrderRequest, OrderResponse, OrderSide, OrderType, TWAPResult
from bot.orders import OrderService
from bot.exceptions import BinanceAPIError


MOCK_ORDER_RESPONSE = {
    "orderId": 123456,
    "clientOrderId": "test_abc",
    "symbol": "BTCUSDT",
    "side": "BUY",
    "type": "MARKET",
    "status": "FILLED",
    "origQty": "0.010",
    "executedQty": "0.010",
    "avgPrice": "65000.00",
    "price": "0",
    "timeInForce": "GTC",
}


@pytest.fixture
def mock_client():
    client = MagicMock()
    client.place_order.return_value = MOCK_ORDER_RESPONSE
    return client


@pytest.fixture
def service(mock_client):
    return OrderService(mock_client)


class TestPlaceMarket:
    def test_returns_order_response(self, service, mock_client):
        request = OrderRequest(
            symbol="BTCUSDT",
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            quantity=Decimal("0.01"),
        )
        result = service.place(request)
        assert isinstance(result, OrderResponse)
        assert result.order_id == 123456
        assert result.status == "FILLED"

    def test_correct_params_sent(self, service, mock_client):
        request = OrderRequest(
            symbol="BTCUSDT",
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            quantity=Decimal("0.01"),
        )
        service.place(request)
        mock_client.place_order.assert_called_once()
        params = mock_client.place_order.call_args[0][0]
        assert params["symbol"] == "BTCUSDT"
        assert params["side"] == "BUY"
        assert params["type"] == "MARKET"
        assert params["quantity"] == "0.01"

    def test_api_error_propagates(self, service, mock_client):
        mock_client.place_order.side_effect = BinanceAPIError("Invalid symbol", code=-1121)
        request = OrderRequest(
            symbol="INVALID",
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            quantity=Decimal("0.01"),
        )
        with pytest.raises(BinanceAPIError):
            service.place(request)


class TestPlaceLimit:
    def test_limit_order_includes_price(self, service, mock_client):
        mock_client.place_order.return_value = {
            **MOCK_ORDER_RESPONSE,
            "type": "LIMIT",
            "status": "NEW",
            "price": "60000.00",
            "avgPrice": "0",
        }
        request = OrderRequest(
            symbol="BTCUSDT",
            side=OrderSide.SELL,
            order_type=OrderType.LIMIT,
            quantity=Decimal("0.01"),
            price=Decimal("60000"),
        )
        result = service.place(request)
        assert isinstance(result, OrderResponse)
        params = mock_client.place_order.call_args[0][0]
        assert params["type"] == "LIMIT"
        assert params["price"] == "60000"
        assert "timeInForce" in params


class TestTWAP:
    def test_twap_places_n_slices(self, service, mock_client):
        request = OrderRequest(
            symbol="BTCUSDT",
            side=OrderSide.BUY,
            order_type=OrderType.TWAP,
            quantity=Decimal("0.030"),
            twap_slices=3,
            twap_interval_seconds=0,  # no sleep in tests
        )
        with patch("time.sleep"):
            result = service.place(request)

        assert isinstance(result, TWAPResult)
        assert result.slices_requested == 3
        assert result.slices_filled == 3
        assert mock_client.place_order.call_count == 3

    def test_twap_continues_on_partial_failure(self, service, mock_client):
        # Fail the second slice, succeed the rest
        mock_client.place_order.side_effect = [
            MOCK_ORDER_RESPONSE,
            BinanceAPIError("Rate limited", code=-1003),
            MOCK_ORDER_RESPONSE,
        ]
        request = OrderRequest(
            symbol="BTCUSDT",
            side=OrderSide.BUY,
            order_type=OrderType.TWAP,
            quantity=Decimal("0.030"),
            twap_slices=3,
            twap_interval_seconds=0,
        )
        with patch("time.sleep"):
            result = service.place(request)

        assert result.slices_filled == 2
        assert result.slices_requested == 3
        assert result.success_rate == pytest.approx(66.67, 0.1)
