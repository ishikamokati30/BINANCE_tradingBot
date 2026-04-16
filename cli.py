import sys
from decimal import Decimal
from typing import Optional

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich import box

from bot.client import BinanceFuturesClient
from bot.exceptions import BinanceAPIError, NetworkError, ValidationError, ConfigurationError
from bot.logging_config import setup_logging, get_logger
from bot.models import OrderResponse, TWAPResult
from bot.orders import OrderService
from bot.models import OrderRequest
from bot import validators

try:
    from config.settings import settings
except ConfigurationError as exc:
    typer.echo(f"[CONFIG ERROR] {exc}", err=True)
    raise typer.Exit(1)

app = typer.Typer(
    name="trading-bot",
    help="Binance Futures Testnet trading bot — place MARKET, LIMIT, and TWAP orders.",
    add_completion=False,
)
console = Console()
err_console = Console(stderr=True, style="bold red")

def _build_client() -> BinanceFuturesClient:
    return BinanceFuturesClient(
        api_key=settings.api_key,
        api_secret=settings.api_secret,
        base_url=settings.base_url,
    )


def _print_order_response(response: OrderResponse) -> None:
    table = Table(box=box.ROUNDED, show_header=False, title="Order Placed ✓", title_style="bold green")
    table.add_column("Field", style="cyan", no_wrap=True)
    table.add_column("Value", style="white")

    rows = [
        ("Order ID",        str(response.order_id)),
        ("Client Order ID", response.client_order_id),
        ("Symbol",          response.symbol),
        ("Side",            response.side),
        ("Type",            response.order_type),
        ("Status",          response.status),
        ("Original Qty",    response.orig_qty),
        ("Executed Qty",    response.executed_qty),
        ("Avg Price",       response.avg_price if response.avg_price != "0" else "—"),
        ("Limit Price",     response.price if response.price != "0" else "—"),
        ("Time In Force",   response.time_in_force if response.time_in_force else "—"),
    ]
    for field, value in rows:
        table.add_row(field, value)

    console.print(table)


def _print_twap_result(result: TWAPResult) -> None:
    table = Table(box=box.ROUNDED, title="TWAP Execution Complete ✓", title_style="bold green")
    table.add_column("Slice", justify="center")
    table.add_column("Order ID", justify="right")
    table.add_column("Status")
    table.add_column("Executed Qty", justify="right")
    table.add_column("Avg Price", justify="right")

    for i, r in enumerate(result.responses, 1):
        table.add_row(
            str(i),
            str(r.order_id),
            r.status,
            r.executed_qty,
            r.avg_price,
        )

    console.print(table)
    console.print(
        Panel(
            f"[bold]Slices filled:[/bold] {result.slices_filled}/{result.slices_requested}  "
            f"[bold]Success rate:[/bold] {result.success_rate:.1f}%",
            title="TWAP Summary",
            style="green",
        )
    )

@app.command()
def place(
    symbol: str = typer.Option(..., "--symbol", "-s", help="Trading pair, e.g. BTCUSDT"),
    side: str = typer.Option(..., "--side", help="BUY or SELL"),
    order_type: str = typer.Option(..., "--type", "-t", help="MARKET, LIMIT, or TWAP"),
    qty: str = typer.Option(..., "--qty", "-q", help="Order quantity (e.g. 0.01)"),
    price: Optional[str] = typer.Option(None, "--price", "-p", help="Limit price (required for LIMIT orders)"),
    slices: int = typer.Option(5, "--slices", help="[TWAP] Number of slices (2–20)"),
    interval: int = typer.Option(30, "--interval", help="[TWAP] Seconds between slices (5–300)"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Show DEBUG logs in console"),
):
    """Place a MARKET, LIMIT, or TWAP order on Binance Futures Testnet."""
    log_level = "DEBUG" if verbose else settings.log_level
    logger = setup_logging(level=log_level)
    log = get_logger("cli")

    try:
        validated_symbol = validators.validate_symbol(symbol)
        validated_side = validators.validate_side(side)
        validated_type = validators.validate_order_type(order_type)
        validated_qty = validators.validate_quantity(qty)
        validated_price = validators.validate_price(price, validated_type)

        if validated_type.value == "TWAP":
            validated_slices, validated_interval = validators.validate_twap_params(slices, interval)
        else:
            validated_slices, validated_interval = slices, interval

    except ValidationError as exc:
        err_console.print(f"Validation error: {exc.message}")
        log.error("Input validation failed", extra={"error": str(exc), "details": exc.details})
        raise typer.Exit(1)

    request = OrderRequest(
        symbol=validated_symbol,
        side=validated_side,
        order_type=validated_type,
        quantity=validated_qty,
        price=validated_price,
        twap_slices=validated_slices,
        twap_interval_seconds=validated_interval,
    )

    console.print(
        Panel(
            f"[bold]Symbol:[/bold] {request.symbol}  "
            f"[bold]Side:[/bold] {request.side.value}  "
            f"[bold]Type:[/bold] {request.order_type.value}  "
            f"[bold]Qty:[/bold] {request.quantity}"
            + (f"  [bold]Price:[/bold] {request.price}" if request.price else ""),
            title="Order Request",
            style="blue",
        )
    )

    try:
        with _build_client() as client:
            service = OrderService(client)
            result = service.place(request)

        if isinstance(result, TWAPResult):
            _print_twap_result(result)
        else:
            _print_order_response(result)

    except BinanceAPIError as exc:
        err_console.print(f"Binance API error (code {exc.code}): {exc.message}")
        log.error("Order placement failed", extra={"binance_code": exc.code, "error": exc.message})
        raise typer.Exit(1)

    except NetworkError as exc:
        err_console.print(f"Network error: {exc.message}")
        log.error("Network failure", extra={"error": str(exc)})
        raise typer.Exit(1)


@app.command()
def account(
    verbose: bool = typer.Option(False, "--verbose", "-v"),
):
    """Display account balances for assets with non-zero balance."""
    logger = setup_logging(level="DEBUG" if verbose else settings.log_level)
    log = get_logger("cli")

    try:
        with _build_client() as client:
            data = client.get_account()

        assets = [a for a in data.get("assets", []) if float(a.get("walletBalance", 0)) > 0]

        table = Table(box=box.ROUNDED, title="Account Balances", title_style="bold cyan")
        table.add_column("Asset", style="cyan")
        table.add_column("Wallet Balance", justify="right")
        table.add_column("Available Balance", justify="right")
        table.add_column("Unrealised PnL", justify="right")

        for a in assets:
            table.add_row(
                a.get("asset", ""),
                a.get("walletBalance", "0"),
                a.get("availableBalance", "0"),
                a.get("unrealizedProfit", "0"),
            )

        if not assets:
            console.print("[yellow]No assets with non-zero balance found.[/yellow]")
        else:
            console.print(table)

    except (BinanceAPIError, NetworkError) as exc:
        err_console.print(f"Error: {exc}")
        log.error("Account query failed", extra={"error": str(exc)})
        raise typer.Exit(1)

@app.command()
def ping():
    """Check connectivity to the Binance Futures Testnet."""
    setup_logging(level=settings.log_level)
    log = get_logger("cli")

    try:
        with _build_client() as client:
            data = client.get_server_time()
        server_time = data.get("serverTime", "unknown")
        console.print(f"[green]✓ Connected.[/green] Server time: [bold]{server_time}[/bold]")
        log.info("Ping successful", extra={"server_time": server_time})
    except (BinanceAPIError, NetworkError) as exc:
        err_console.print(f"✗ Connection failed: {exc}")
        log.error("Ping failed", extra={"error": str(exc)})
        raise typer.Exit(1)

if __name__ == "__main__":
    app()
