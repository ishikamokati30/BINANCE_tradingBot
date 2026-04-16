import pytest
from decimal import Decimal

from bot.exceptions import ValidationError
from bot.models import OrderType, OrderSide
from bot import validators

class TestValidateSymbol:
    def test_valid_symbol(self):
        assert validators.validate_symbol("btcusdt") == "BTCUSDT"

    def test_valid_symbol_already_upper(self):
        assert validators.validate_symbol("ETHUSDT") == "ETHUSDT"

    def test_strips_whitespace(self):
        assert validators.validate_symbol("  BTCUSDT  ") == "BTCUSDT"

    def test_empty_raises(self):
        with pytest.raises(ValidationError, match="empty"):
            validators.validate_symbol("")

    def test_numeric_raises(self):
        with pytest.raises(ValidationError):
            validators.validate_symbol("BTC123")

    def test_too_short_raises(self):
        with pytest.raises(ValidationError):
            validators.validate_symbol("B")


class TestValidateSide:
    def test_buy(self):
        assert validators.validate_side("BUY") == OrderSide.BUY

    def test_sell_lowercase(self):
        assert validators.validate_side("sell") == OrderSide.SELL

    def test_invalid_raises(self):
        with pytest.raises(ValidationError, match="BUY or SELL"):
            validators.validate_side("LONG")


class TestValidateOrderType:
    def test_market(self):
        assert validators.validate_order_type("MARKET") == OrderType.MARKET

    def test_limit(self):
        assert validators.validate_order_type("limit") == OrderType.LIMIT

    def test_twap(self):
        assert validators.validate_order_type("TWAP") == OrderType.TWAP

    def test_invalid_raises(self):
        with pytest.raises(ValidationError):
            validators.validate_order_type("STOP")


class TestValidateQuantity:
    def test_valid_string(self):
        assert validators.validate_quantity("0.01") == Decimal("0.01")

    def test_valid_float(self):
        assert validators.validate_quantity(0.5) == Decimal("0.5")

    def test_zero_raises(self):
        with pytest.raises(ValidationError, match="greater than zero"):
            validators.validate_quantity("0")

    def test_negative_raises(self):
        with pytest.raises(ValidationError):
            validators.validate_quantity("-1")

    def test_below_minimum_raises(self):
        with pytest.raises(ValidationError, match="minimum"):
            validators.validate_quantity("0.00001")

    def test_non_numeric_raises(self):
        with pytest.raises(ValidationError):
            validators.validate_quantity("abc")


class TestValidatePrice:
    def test_price_ignored_for_market(self):
        result = validators.validate_price("99999", OrderType.MARKET)
        assert result is None

    def test_price_ignored_for_twap(self):
        result = validators.validate_price("99999", OrderType.TWAP)
        assert result is None

    def test_price_required_for_limit(self):
        with pytest.raises(ValidationError, match="required"):
            validators.validate_price(None, OrderType.LIMIT)

    def test_valid_limit_price(self):
        assert validators.validate_price("60000", OrderType.LIMIT) == Decimal("60000")

    def test_zero_price_raises(self):
        with pytest.raises(ValidationError):
            validators.validate_price("0", OrderType.LIMIT)


class TestValidateTWAPParams:
    def test_valid(self):
        assert validators.validate_twap_params(5, 30) == (5, 30)

    def test_too_few_slices(self):
        with pytest.raises(ValidationError, match="slices"):
            validators.validate_twap_params(1, 30)

    def test_too_many_slices(self):
        with pytest.raises(ValidationError):
            validators.validate_twap_params(25, 30)

    def test_interval_too_short(self):
        with pytest.raises(ValidationError, match="interval"):
            validators.validate_twap_params(5, 1)
