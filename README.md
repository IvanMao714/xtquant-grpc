# xtquant-grpc

A gRPC wrapper for [xtquant](https://dict.thinktrader.net/nativeApi/start_now.html) (MiniQMT Python SDK), enabling market data and trading capabilities to be accessed over the network from any language.

## Why This Project

xtquant is a Python quantitative trading library provided by MiniQMT, featuring **market data** (xtdata) and **trading** (xttrader) modules. However, it can only be used via Python on the same Windows machine running the MiniQMT client.

This project exposes xtquant as a network service via gRPC:

- **Cross-language** — Go / Java / Rust / C# / Node.js etc. can generate clients from the proto file
- **Remote access** — Other machines (including Linux / Mac) can fetch quotes and place orders over the network
- **Microservice friendly** — Easy to integrate into microservice-based quantitative trading systems

## Requirements

| Item | Requirement |
|------|-------------|
| OS | Windows (MiniQMT is Windows-only) |
| Python | 3.11+ |
| MiniQMT | Installed and running |
| xtquant | Bundled with MiniQMT; ensure `import xtquant` works in Python |

## Installation

```bash
# Clone the project
git clone <repo-url>
cd xtquant-grpc

# Install dependencies
pip install -e .

# Generate protobuf code
python gen_proto.py
```

## Starting the Server

```bash
# Market data service only (no trading account needed)
python main.py --port 50051

# Market data + trading service
python main.py --port 50051 \
    --mini-qmt-path "D:\path\to\userdata_mini" \
    --session-id 123456
```

### Parameters

| Parameter | Description | Default |
|-----------|-------------|---------|
| `--port` | gRPC listen port | `50051` |
| `--mini-qmt-path` | MiniQMT `userdata_mini` path (enables trading service) | empty (disabled) |
| `--session-id` | Trading session ID; must be unique across concurrent strategies | current timestamp |

## Client Usage Examples

### Python

```python
import grpc
from pb import xtquant_pb2, xtquant_pb2_grpc

channel = grpc.insecure_channel("localhost:50051")
market = xtquant_pb2_grpc.MarketDataServiceStub(channel)
trading = xtquant_pb2_grpc.TradingServiceStub(channel)

# ---- Get Kline Data ----
resp = market.GetMarketData(xtquant_pb2.GetMarketDataRequest(
    stock_codes=["600000.SH"],
    period="1d",
    start_time="20240101",
    count=10,
))
for code, klines in resp.data.items():
    for bar in klines.bars:
        print(f"{code} | {bar.time} O={bar.open} H={bar.high} L={bar.low} C={bar.close}")

# ---- Get Real-time Tick ----
resp = market.GetFullTick(xtquant_pb2.GetFullTickRequest(
    stock_codes=["600000.SH", "000001.SZ"],
))
for code, tick in resp.ticks.items():
    print(f"{code} last={tick.last_price} bid1={tick.bid_price[0] if tick.bid_price else '-'}")

# ---- Get Sector Constituents ----
resp = market.GetStockList(xtquant_pb2.GetStockListRequest(sector_name="沪深A股"))  # Chinese sector name
print(f"A-shares total: {len(resp.stock_codes)}")

# ---- Get Instrument Detail ----
detail = market.GetInstrumentDetail(xtquant_pb2.GetInstrumentDetailRequest(
    stock_code="600000.SH",
))
print(f"{detail.instrument_name} upper_limit={detail.up_stop_price} lower_limit={detail.down_stop_price}")

# ---- Place Order (requires trading service) ----
resp = trading.OrderStock(xtquant_pb2.OrderStockRequest(
    account_id="1000000365",
    account_type="STOCK",
    stock_code="600000.SH",
    order_type=23,       # STOCK_BUY
    volume=100,
    price_type=11,       # FIX_PRICE
    price=10.5,
    strategy_name="my_strategy",
    order_remark="test_order",
))
print(f"Order result: order_id={resp.order_id}, success={resp.success}")

# ---- Query Positions ----
resp = trading.QueryPositions(xtquant_pb2.AccountRequest(
    account_id="1000000365",
    account_type="STOCK",
))
for pos in resp.positions:
    print(f"{pos.stock_code} volume={pos.volume} available={pos.can_use_volume} cost={pos.avg_price}")
```

### Download Historical Data (Streaming Progress)

```python
# Batch download with real-time progress tracking
for progress in market.DownloadHistoryData(xtquant_pb2.DownloadHistoryDataRequest(
    stock_codes=["600000.SH", "000001.SZ", "000300.SH"],
    period="1d",
    start_time="20240101",
)):
    print(f"[{progress.finished}/{progress.total}] {progress.stock_code} done")
# Output:
# [1/3] 600000.SH done
# [2/3] 000001.SZ done
# [3/3] 000300.SH done
```

### Subscribe to Real-time Quotes (Streaming)

```python
# Subscribe to single-stock kline
for update in market.SubscribeQuote(xtquant_pb2.SubscribeQuoteRequest(
    stock_code="600000.SH",
    period="1m",
)):
    for bar in update.bars:
        print(f"{update.stock_code} close={bar.close} vol={bar.volume}")

# Subscribe to full-market tick (for large number of instruments)
for tick in market.SubscribeWholeQuote(xtquant_pb2.SubscribeWholeQuoteRequest(
    code_list=["SH", "SZ"],
)):
    print(f"{tick.stock_code} last={tick.last_price}")
```

### Subscribe to Trading Events (Streaming)

```python
for event in trading.SubscribeTrading(xtquant_pb2.AccountRequest(
    account_id="1000000365",
    account_type="STOCK",
)):
    if event.HasField("order_update"):
        o = event.order_update
        print(f"Order update: {o.stock_code} status={o.order_status}")
    elif event.HasField("trade_update"):
        t = event.trade_update
        print(f"Trade: {t.stock_code} price={t.traded_price} volume={t.traded_volume}")
    elif event.HasField("order_error"):
        print(f"Order error: {event.order_error.error_msg}")
```

## gRPC Service Reference

### MarketDataService (Market Data)

| Method | Type | Description | xtdata Mapping |
|--------|------|-------------|----------------|
| `GetMarketData` | Unary | Get kline data | `get_market_data_ex` |
| `GetFullTick` | Unary | Get tick snapshot | `get_full_tick` |
| `GetInstrumentDetail` | Unary | Get instrument info | `get_instrument_detail` |
| `GetStockList` | Unary | Get sector constituents | `get_stock_list_in_sector` |
| `GetSectorList` | Unary | Get sector list | `get_sector_list` |
| `DownloadHistoryData` | Stream | Download historical data with progress | `download_history_data2` |
| `GetTradingCalendar` | Unary | Get trading calendar | `get_trading_calendar` |
| `GetFinancialData` | Unary | Get financial data | `get_financial_data` |
| `SubscribeQuote` | Stream | Subscribe single-stock quotes | `subscribe_quote` |
| `SubscribeWholeQuote` | Stream | Subscribe full-market quotes | `subscribe_whole_quote` |

### TradingService (Trading)

| Method | Type | Description | xttrader Mapping |
|--------|------|-------------|-----------------|
| `OrderStock` | Unary | Place order | `order_stock` |
| `CancelOrder` | Unary | Cancel order | `cancel_order_stock` |
| `QueryAsset` | Unary | Query account asset | `query_stock_asset` |
| `QueryOrders` | Unary | Query orders | `query_stock_orders` |
| `QueryTrades` | Unary | Query trades | `query_stock_trades` |
| `QueryPositions` | Unary | Query positions | `query_stock_positions` |
| `SubscribeTrading` | Stream | Trading event push | `subscribe` + callbacks |

## Common Constants Reference

gRPC clients need to pass integer constant values defined in xtconstant when placing orders:

### Order Type (order_type)

| Name | Value | Description |
|------|-------|-------------|
| `STOCK_BUY` | 23 | Stock buy |
| `STOCK_SELL` | 24 | Stock sell |
| `CREDIT_BUY` | 25 | Margin collateral buy |
| `CREDIT_SELL` | 26 | Margin collateral sell |
| `CREDIT_FIN_BUY` | 27 | Margin financing buy |
| `CREDIT_SLO_SELL` | 28 | Securities lending sell |

### Price Type (price_type)

| Name | Value | Description |
|------|-------|-------------|
| `LATEST_PRICE` | 5 | Latest price |
| `FIX_PRICE` | 11 | Limit price |

### Order Status (order_status)

| Name | Value | Description |
|------|-------|-------------|
| `ORDER_UNREPORTED` | 48 | Unreported |
| `ORDER_WAIT_REPORTING` | 49 | Pending report |
| `ORDER_REPORTED` | 50 | Reported |
| `ORDER_REPORTED_CANCEL` | 51 | Reported, pending cancel |
| `ORDER_PARTSUCC_CANCEL` | 52 | Partially filled, pending cancel |
| `ORDER_PART_CANCEL` | 53 | Partially cancelled |
| `ORDER_CANCELED` | 54 | Cancelled |
| `ORDER_PART_SUCC` | 55 | Partially filled |
| `ORDER_SUCCEEDED` | 56 | Fully filled |
| `ORDER_JUNK` | 57 | Rejected |
| `ORDER_UNKNOWN` | 255 | Unknown |

> Full constants list available via `from xtquant import xtconstant` in Python.

## Project Structure

```
xtquant-grpc/
├── proto/
│   └── xtquant.proto        # gRPC service & message definitions
├── pb/                       # Generated protobuf code (run gen_proto.py)
├── server/
│   ├── __init__.py
│   ├── market_data.py       # Market data service (wraps xtdata)
│   └── trading.py           # Trading service (wraps xttrader)
├── test/
│   ├── conftest.py          # Shared test fixtures
│   ├── test_xtdata_direct.py  # Direct xtdata integration tests
│   └── test_grpc_server.py  # Full gRPC round-trip tests
├── main.py                   # Server entry point
├── gen_proto.py              # Protobuf code generation script
├── pyproject.toml
└── README.md
```

## Cross-language Clients

Copy `proto/xtquant.proto` to your project and generate client code with protoc:

```bash
# Go
protoc --go_out=. --go-grpc_out=. proto/xtquant.proto

# Java
protoc --java_out=. --grpc-java_out=. proto/xtquant.proto

# C#
protoc --csharp_out=. --grpc_csharp_out=. proto/xtquant.proto
```

## Notes

1. **MiniQMT must be running** — Both xtdata and xttrader depend on the locally running MiniQMT client
2. **Data must be downloaded first** — Before calling `GetMarketData` for historical data, download it via `DownloadHistoryData`
3. **Subscription limits** — Single-stock subscriptions should not exceed ~50; use `SubscribeWholeQuote` for many instruments
4. **Unique session ID** — Concurrent strategies must use different `--session-id` values

## License

MIT
