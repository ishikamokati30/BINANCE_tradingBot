class TradingBotError(Exception):

    def __init__(self, message: str, details: dict | None = None):
        super().__init__(message)
        self.message = message
        self.details = details or {}

    def __str__(self) -> str:
        if self.details:
            return f"{self.message} | details={self.details}"
        return self.message


class ValidationError(TradingBotError):
    pass


class BinanceAPIError(TradingBotError):

    def __init__(self, message: str, status_code: int = 0, code: int = 0, details: dict | None = None):
        super().__init__(message, details)
        self.status_code = status_code
        self.code = code  


class NetworkError(TradingBotError):
    pass


class ConfigurationError(TradingBotError):
    pass
