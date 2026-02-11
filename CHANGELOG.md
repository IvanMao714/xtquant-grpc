# Changelog

All notable changes to xtquant-grpc are documented in this file.

## [0.5.2] - 2026-02-11

### Removed
- **`ps_ttm` and `dividend_yield`** fields from `StockValuation` proto — xtdata does not provide these; fields that have no data source are removed instead of filling with 0

### Changed
- Renumbered `StockValuation` proto fields (4-9) after field removal
- Updated `docs/financial_data.md` — each field now shows its exact formula / data source in a dedicated column

## [0.5.1] - 2026-02-11

### Fixed
- **`GetValuationMetrics` field mapping** — corrected to use actual xtdata field names:
  - EPS: `s_fa_eps_basic` (was `m_epsbasic`)
  - BPS: `s_fa_bps` (for PB calculation)
  - Total shares: `total_capital` (was `totalCapital`)
  - Float shares: `circulating_capital` (was `circACapital`)
- **PE and PB are now computed** from latest tick price / EPS and price / BPS respectively (xtdata does NOT store PE/PB directly)
- Updated proto comments, docs, and CHANGELOG to reflect actual data sources

## [0.5.0] - 2026-02-11

### Added
- **`GetValuationMetrics` RPC** — structured endpoint returning PE, PB, EPS, turnover rate, total/float shares, and market cap per stock. PE/PB computed from latest price and Pershareindex fields
- **`DownloadFinancialData` RPC** — server-streaming download of financial data with progress tracking, using `xtdata.download_financial_data2`
- **`report_type` field** in `GetFinancialDataRequest` — supports `"report_time"` (default) and `"announce_time"` filtering
- `scripts/test_financial_data.py` — exploration script to discover all 8 financial table schemas and instrument detail fields
- `docs/financial_data.md` — comprehensive financial data API reference with actual field names, table schemas, and usage examples
- `CHANGELOG.md` — full project history

### Changed
- `GetFinancialData` now passes `report_type` to `xtdata.get_financial_data`
- Updated README with new RPC reference entries

## [0.4.0] - 2026-02-09

### Changed
- **Replaced `GetTradingCalendar` with `GetTradingDates`** — uses `xtdata.get_trading_dates` which returns millisecond timestamps and supports a `count` parameter
- **Fixed date offset bug** — `GetMarketData` time field now uses `df["time"]` (ms timestamps) instead of `df.index` (UTC dates off by 1 day for Chinese stocks). Clients receive raw ms timestamps and convert to local time
- **xtdata connection check at startup** — server waits for xtdata to connect before accepting gRPC requests (5-minute timeout with polling)
- Added detailed server-side logging for `DownloadHistoryData` (request info, per-stock progress, completion/error)

## [0.3.0] - 2026-02-08

### Changed
- **Columnar `GetMarketDataResponse`** — replaced `map<string, StockKlines>` with parallel arrays (`repeated string stock_code`, `repeated int64 time`, `repeated double open`, ...) for zero-overhead DataFrame construction
- Increased gRPC max message size to 1 GB (server + client) to support large unary responses
- Removed `StockKlines` message; added `stock_code` field to `KlineBar`

## [0.2.0] - 2026-02-07

### Changed
- **Streaming `DownloadHistoryData`** — changed from unary to server-streaming RPC using `xtdata.download_history_data2` with progress callback
- Added `DownloadProgress` message type with `total`, `finished`, `stock_code`, `message` fields
- Background thread + queue pattern for bridging synchronous xtdata callbacks to gRPC streaming
- Initial progress message yielded immediately to prevent client timeout on large downloads

## [0.1.0] - 2026-02-06

### Added
- Initial release of xtquant-grpc
- **MarketDataService** with 8 RPCs:
  - `GetMarketData` — kline data via `get_market_data_ex`
  - `GetFullTick` — real-time tick snapshots via `get_full_tick`
  - `GetInstrumentDetail` — instrument info via `get_instrument_detail`
  - `GetStockList` — sector constituents via `get_stock_list_in_sector`
  - `GetSectorList` — sector list via `get_sector_list`
  - `DownloadHistoryData` — historical data download
  - `GetTradingCalendar` — trading calendar
  - `GetFinancialData` — financial data (JSON response)
  - `SubscribeQuote` — single-stock quote subscription (streaming)
  - `SubscribeWholeQuote` — full-market quote subscription (streaming)
- **TradingService** with 7 RPCs:
  - `OrderStock`, `CancelOrder`, `QueryAsset`, `QueryOrders`, `QueryTrades`, `QueryPositions`, `SubscribeTrading`
- Integration tests (direct xtdata + gRPC round-trip)
- Project documentation (README) with cross-language client examples
- Protobuf code generation script (`gen_proto.py`)
