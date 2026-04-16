"""
Binance Futures Testnet HTTP client.

Responsibilities:
- HMAC-SHA256 request signing
- Timestamp injection
- Connection pooling via httpx
- Structured logging of every request/response
- Retry with exponential back-off on transient errors
- Raising typed exceptions (BinanceAPIError, NetworkError)
"""
import hashlib
import hmac
import time
from urllib.parse import urlencode

import httpx

from bot.exceptions import BinanceAPIError, NetworkError
from bot.logging_config import get_logger


logger = get_logger("client")

DEFAULT_TIMEOUT = 10.0  
MAX_RETRIES = 3
RETRY_BACKOFF = 1.5      

class BinanceFuturesClient:

    def __init__(self, api_key: str, api_secret: str, base_url: str):
        self._api_key = api_key
        self._api_secret = api_secret
        self._base_url = base_url.rstrip("/")
        self._client = httpx.Client(
            timeout=DEFAULT_TIMEOUT,
            headers={
                "X-MBX-APIKEY": self._api_key,
                "Content-Type": "application/x-www-form-urlencoded",
            },
        )
        logger.info(
            "BinanceFuturesClient initialised",
            extra={"base_url": self._base_url},
        )
    def get_server_time(self) -> dict:
        return self._get("/fapi/v1/time", signed=False)

    def get_account(self) -> dict:
        return self._get("/fapi/v2/account", signed=True)

    def get_exchange_info(self) -> dict:
        """Return exchange trading rules and symbol information."""
        return self._get("/fapi/v1/exchangeInfo", signed=False)

    def place_order(self, params: dict) -> dict:
        return self._post("/fapi/v1/order", params=params, signed=True)

    def get_order(self, symbol: str, order_id: int) -> dict:
        return self._get(
            "/fapi/v1/order",
            params={"symbol": symbol, "orderId": order_id},
            signed=True,
        )

    def _sign(self, params: dict) -> dict:
        params["timestamp"] = int(time.time() * 1000)
        query_string = urlencode(params)
        signature = hmac.new(
            self._api_secret.encode("utf-8"),
            query_string.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()
        params["signature"] = signature
        return params

    def _get(self, endpoint: str, params: dict | None = None, signed: bool = False) -> dict:
        params = params or {}
        if signed:
            params = self._sign(params)
        url = f"{self._base_url}{endpoint}"
        return self._request("GET", url, params=params)

    def _post(self, endpoint: str, params: dict | None = None, signed: bool = False) -> dict:
        params = params or {}
        if signed:
            params = self._sign(params)
        url = f"{self._base_url}{endpoint}"
        return self._request("POST", url, data=params)

    def _request(self, method: str, url: str, **kwargs) -> dict:
        last_exc: Exception | None = None

        for attempt in range(1, MAX_RETRIES + 1):
            logger.debug(
                "API request",
                extra={
                    "attempt": attempt,
                    "method": method,
                    "url": url,
                    "params": kwargs.get("params") or kwargs.get("data"),
                },
            )
            try:
                response = self._client.request(method, url, **kwargs)
                data = response.json()

                logger.debug(
                    "API response",
                    extra={
                        "status_code": response.status_code,
                        "response_body": data,
                    },
                )

                if isinstance(data, dict) and data.get("code", 0) < 0:
                    raise BinanceAPIError(
                        message=data.get("msg", "Unknown API error"),
                        status_code=response.status_code,
                        code=data.get("code", 0),
                        details={"response": data},
                    )

                if response.status_code >= 400:
                    raise BinanceAPIError(
                        message=f"HTTP {response.status_code}",
                        status_code=response.status_code,
                        details={"response": data},
                    )

                return data

            except BinanceAPIError:
             
                raise

            except (httpx.TimeoutException, httpx.ConnectError) as exc:
                last_exc = exc
                wait = RETRY_BACKOFF * (2 ** (attempt - 1))
                logger.warning(
                    "Network error, retrying",
                    extra={
                        "attempt": attempt,
                        "max_retries": MAX_RETRIES,
                        "error": str(exc),
                        "retry_in_seconds": wait,
                    },
                )
                if attempt < MAX_RETRIES:
                    time.sleep(wait)

            except httpx.HTTPError as exc:
                last_exc = exc
                logger.error("Unexpected HTTP error", extra={"error": str(exc)})
                break

        raise NetworkError(
            f"Request failed after {MAX_RETRIES} attempts: {last_exc}",
            details={"url": url, "method": method},
        )

    def close(self):
        self._client.close()

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.close()
