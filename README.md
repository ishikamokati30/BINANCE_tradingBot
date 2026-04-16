# Trading Bot — Binance Futures Testnet

A clean, production-structured Python CLI for placing **MARKET**, **LIMIT**, and **TWAP** orders on Binance Futures Testnet (USDT-M).

---

## Project Structure

```
trading_bot/
├── bot/
│   ├── __init__.py          # Package exports
│   ├── client.py            # HTTP adapter — HMAC signing, retry, connection pool
│   ├── models.py            # Typed DTOs: OrderRequest, OrderResponse, TWAPResult
│   ├── orders.py            # OrderService — MARKET, LIMIT, TWAP logic
│   ├── validators.py        # Input validation — fails before any API call
│   ├── exceptions.py        # Custom exception hierarchy
│   └── logging_config.py    # JSON file logger + coloured console logger
├── config/
│   ├── __init__.py
│   └── settings.py          # .env loader, Settings singleton
├── logs/
│   └── trading_bot.log      # Auto-created; JSON lines, rotating
├── tests/
│   ├── test_validators.py   # 20+ unit tests for validation logic
│   └── test_orders.py       # Order service tests with mocked client
├── cli.py                   # Typer CLI — sub-commands: place, account, ping
├── .env.example             # Template — copy to .env and fill in credentials
├── pyproject.toml           # Dependencies, ruff, mypy, pytest config
└── README.md
```

### Architecture

```
CLI (cli.py)
  └─► validators.py     ← rejects bad input before any network call
        └─► models.py   ← typed OrderRequest DTO
              └─► orders.py (OrderService)
                    └─► client.py (BinanceFuturesClient)
                              └─► Binance Futures Testnet REST API
```

Each layer only knows its immediate neighbour. Logging fires at every boundary.

---

## Setup

### 1. Get Testnet Credentials

1. Go to [https://testnet.binancefuture.com](https://testnet.binancefuture.com)
2. Register / log in
3. Navigate to **API Management** and generate a key pair
4. Copy the API Key and Secret

### 2. Install

```bash
cd trading_bot

python -m venv .venv
source .venv/bin/activate        

pip install -e ".[dev]"
```


```bash
cp .env.example .env
```

---

## Usage

### Check connectivity

```bash
python cli.py ping
```

### Place a MARKET order

```bash
python cli.py place --symbol BTCUSDT --side BUY --type MARKET --qty 0.01
```

### Place a LIMIT order

```bash
python cli.py place --symbol BTCUSDT --side SELL --type LIMIT --qty 0.01 --price 60000
```

### Place a TWAP order (bonus)

Splits 0.05 BTC into 3 equal MARKET slices, 10 seconds apart:

```bash
python cli.py place --symbol BTCUSDT --side BUY --type TWAP --qty 0.05 --slices 3 --interval 10
```

### View account balances

```bash
python cli.py account
```

### Verbose / debug mode

```bash
python cli.py place --symbol BTCUSDT --side BUY --type MARKET --qty 0.01 --verbose
```

### Built-in help

```bash
python cli.py --help
python cli.py place --help
```

---

## Running Tests

```bash
pytest tests/ -v
```

Expected output:
```
tests/test_validators.py::TestValidateSymbol::test_valid_symbol PASSED
tests/test_validators.py::TestValidateSide::test_buy PASSED
...
tests/test_orders.py::TestTWAP::test_twap_places_n_slices PASSED
20 passed in 0.XX seconds
```

---

## Logging

All activity is written as structured JSON to `logs/trading_bot.log` (rotating, max 5 MB × 3 files).

Example log entries:

```json
{"timestamp": "2024-01-15T10:23:01.123Z", "level": "INFO", "logger": "trading_bot.orders", "message": "Placing order", "order_request": {"symbol": "BTCUSDT", "side": "BUY", "type": "MARKET", "quantity": "0.01"}}
{"timestamp": "2024-01-15T10:23:01.456Z", "level": "DEBUG", "logger": "trading_bot.client", "message": "API request", "method": "POST", "url": "https://testnet.binancefuture.com/fapi/v1/order"}
{"timestamp": "2024-01-15T10:23:01.789Z", "level": "INFO", "logger": "trading_bot.orders", "message": "Market order placed successfully", "order_id": 123456, "status": "FILLED", "executed_qty": "0.01", "avg_price": "65000.00"}
```

Set `LOG_LEVEL=DEBUG` in `.env` (or pass `--verbose`) to also capture raw request/response bodies.

---

## Design Decisions

| Decision | Reason |
|---|---|
| `httpx` over `requests` | Built-in connection pooling, modern API, easier to swap for async later |
| `typer` over `argparse` | Auto-generates `--help`, supports sub-commands cleanly, less boilerplate |
| Custom exception hierarchy | Callers catch `BinanceAPIError` vs `NetworkError` vs `ValidationError` without parsing strings |
| Validation before network | Avoids wasting API rate-limit quota on obviously invalid input |
| JSON structured logging | Machine-readable, easy to grep, forward to ELK/Datadog |
| `pyproject.toml` | Modern Python packaging; ruff + mypy config co-located with deps |
| TWAP as client-side slicing | Binance Futures Testnet doesn't support native TWAP; splitting MARKET orders is the industry-standard approach |

---

## Assumptions

- Testnet API credentials are USDT-M Futures, not Spot.
- Quantity precision is set to 3 decimal places (0.001 minimum). Production use requires fetching `LOT_SIZE` filter from `/fapi/v1/exchangeInfo`.
- TWAP places MARKET slices (no passive limit prices) to guarantee fill on testnet.
- Network retries use exponential back-off (max 3 attempts, starting at 1.5 s).

## Validation
<img width="1321" height="622" alt="image" src="https://github.com/user-attachments/assets/a35340bb-9025-4114-b6eb-c8080e4e6f57" />

