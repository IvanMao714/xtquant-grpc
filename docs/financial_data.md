# Financial Data API Reference

This document describes the financial data capabilities exposed by the xtquant-grpc server, including available tables, field schemas, and client usage examples.

## Overview

Financial data in xtquant comes from `xtdata.get_financial_data` and must be **downloaded locally first** before querying. The gRPC server provides three related RPCs:

| RPC | Type | Description |
|-----|------|-------------|
| `DownloadFinancialData` | Server stream | Download financial data with progress tracking |
| `GetFinancialData` | Unary | Query downloaded financial data (returns JSON) |
| `GetValuationMetrics` | Unary | Get structured valuation metrics (PE, PB, EPS, etc.) |

## Available Tables

Pass these names in the `table_list` field of `GetFinancialData` / `DownloadFinancialData`:

| Table Name | Description |
|------------|-------------|
| `Balance` | Balance sheet (assets, liabilities, equity) |
| `Income` | Income statement (revenue, expenses, profit) |
| `CashFlow` | Cash flow statement |
| `Capital` | Share capital (total shares, float shares) |
| `Holdernum` | Shareholder count |
| `Top10holder` | Top 10 shareholders |
| `Top10flowholder` | Top 10 float shareholders |
| `Pershareindex` | Per-share metrics (EPS, BPS, ROE, etc.) |

## Workflow

```
1. DownloadFinancialData  -->  downloads data to local MiniQMT cache
2. GetFinancialData       -->  queries from local cache (JSON response)
3. GetValuationMetrics    -->  structured valuation data (no JSON parsing needed)
```

Financial data must be downloaded before querying. Without downloading, `GetFinancialData` and `GetValuationMetrics` will return empty results.

## RPC Reference

### DownloadFinancialData

Streams `DownloadProgress` messages as each stock's financial data completes downloading.

```protobuf
rpc DownloadFinancialData(DownloadFinancialDataRequest) returns (stream DownloadProgress);
```

**Request fields:**

| Field | Type | Description |
|-------|------|-------------|
| `stock_codes` | repeated string | Stock codes, e.g. `["600000.SH", "000001.SZ"]` |
| `table_list` | repeated string | Table names to download (see table above) |
| `start_time` | string | Start time filter, e.g. `"20230101"` |
| `end_time` | string | End time filter |

**Python example:**

```python
for progress in market.DownloadFinancialData(xtquant_pb2.DownloadFinancialDataRequest(
    stock_codes=["600000.SH", "000001.SZ"],
    table_list=["Pershareindex", "Capital", "Balance", "Income"],
)):
    print(f"[{progress.finished}/{progress.total}] {progress.stock_code}")
```

### GetFinancialData

Returns raw financial data as JSON. Flexible but requires client-side JSON parsing.

```protobuf
rpc GetFinancialData(GetFinancialDataRequest) returns (GetFinancialDataResponse);
```

**Request fields:**

| Field | Type | Description |
|-------|------|-------------|
| `stock_codes` | repeated string | Stock codes |
| `table_list` | repeated string | Table names |
| `start_time` | string | Start time |
| `end_time` | string | End time |
| `report_type` | string | `"report_time"` (default) — filter by report date; `"announce_time"` — filter by disclosure date |

**Python example:**

```python
import json

resp = market.GetFinancialData(xtquant_pb2.GetFinancialDataRequest(
    stock_codes=["600000.SH"],
    table_list=["Pershareindex", "Capital"],
    report_type="report_time",
))
data = json.loads(resp.data_json)
# data = {"600000.SH": {"Pershareindex": [...], "Capital": [...]}}
for table_name, records in data["600000.SH"].items():
    print(f"{table_name}: {len(records)} records")
    if records:
        print(f"  Fields: {list(records[-1].keys())}")
```

### GetValuationMetrics

Returns structured valuation data — no JSON parsing needed. Combines data from `Pershareindex`, `Capital`, and real-time tick price.

```protobuf
rpc GetValuationMetrics(GetValuationMetricsRequest) returns (GetValuationMetricsResponse);
```

**Response fields (per stock):**

| Field | Type | Formula / Source | Description |
|-------|------|------------------|-------------|
| `stock_code` | string | — | Stock code |
| `pe_ttm` | double | `tick.lastPrice / Pershareindex.s_fa_eps_basic` | PE ratio (computed) |
| `pb` | double | `tick.lastPrice / Pershareindex.s_fa_bps` | Price-to-Book (computed) |
| `turnover_rate` | double | `tick.volume / Capital.circulating_capital * 100` | Turnover rate % (computed) |
| `eps` | double | `Pershareindex.s_fa_eps_basic` | Basic earnings per share |
| `total_shares` | int64 | `Capital.total_capital` | Total shares outstanding |
| `float_shares` | int64 | `Capital.circulating_capital` | Circulating shares |
| `total_market_cap` | double | `tick.lastPrice * Capital.total_capital` | Total market cap (computed) |
| `float_market_cap` | double | `tick.lastPrice * Capital.circulating_capital` | Float market cap (computed) |

> **Note:** PE, PB, turnover rate, and market cap are NOT stored in xtdata — they are computed at query time from the latest tick price combined with `Pershareindex` and `Capital` table data. Outside trading hours, `lastPrice` equals the last closing price.

**Python example:**

```python
resp = market.GetValuationMetrics(xtquant_pb2.GetValuationMetricsRequest(
    stock_codes=["600000.SH", "000001.SZ"],
))
for v in resp.valuations:
    print(f"{v.stock_code}: PE={v.pe_ttm:.2f} PB={v.pb:.2f} EPS={v.eps:.4f} "
          f"Turnover={v.turnover_rate:.2f}% MarketCap={v.total_market_cap/1e8:.0f}亿")
```

**Polars DataFrame example:**

```python
import polars as pl

resp = market.GetValuationMetrics(xtquant_pb2.GetValuationMetricsRequest(
    stock_codes=stock_codes,
))
df = pl.DataFrame([{
    "stock_code": v.stock_code,
    "pe_ttm": v.pe_ttm,
    "pb": v.pb,
    "eps": v.eps,
    "turnover_rate": v.turnover_rate,
    "total_shares": v.total_shares,
    "float_shares": v.float_shares,
    "total_market_cap": v.total_market_cap,
    "float_market_cap": v.float_market_cap,
} for v in resp.valuations])
print(df)
```

## Field Discovery

To discover the exact field names available in each financial table on your MiniQMT instance, run the exploration script:

```bash
python scripts/test_financial_data.py --host localhost:50051
```

This will print all field names and sample values for each table, and highlight valuation-related fields.

## Key Pershareindex Fields

| Field | Description | Sample Value |
|-------|-------------|-------------|
| `s_fa_eps_basic` | Basic EPS | 1.28 |
| `s_fa_eps_diluted` | Diluted EPS | 1.18 |
| `s_fa_bps` | Book value per share | 22.4 |
| `s_fa_ocfps` | Operating cash flow per share | 5.28 |
| `s_fa_undistributedps` | Undistributed profit per share | 7.75 |
| `s_fa_surpluscapitalps` | Surplus capital per share | 3.48 |
| `net_roe` | Net ROE (%) | 4.66 |
| `equity_roe` | Equity ROE (%) | 5.67 |
| `gear_ratio` | Leverage ratio (%) | 91.50 |
| `inc_revenue_rate` | Revenue growth rate (%) | 1.88 |
| `inc_net_profit_rate` | Net profit growth rate (%) | 10.21 |
| `adjusted_earnings_per_share` | Adjusted EPS | 1.29 |

## Key Capital Fields

| Field | Description | Sample Value |
|-------|-------------|-------------|
| `total_capital` | Total shares outstanding | 33,305,838,300 |
| `circulating_capital` | Circulating A-shares | 33,305,838,300 |
| `freeFloatCapital` | Free float shares | 18,249,498,964 |
| `restrict_circulating_capital` | Restricted shares | 0 |

## Notes

1. **Download first** — `GetFinancialData` and `GetValuationMetrics` query local data. Always call `DownloadFinancialData` first.
2. **Data freshness** — Financial data updates quarterly. Re-download periodically to get the latest reports.
3. **PE / PB are computed** — xtdata does NOT store PE or PB directly. `GetValuationMetrics` computes them as `price / s_fa_eps_basic` and `price / s_fa_bps`.
4. **Market cap** — `GetValuationMetrics` computes market cap from the latest tick price. Outside trading hours, this uses the last closing price.
5. **report_type** — Use `"report_time"` to filter by the report's accounting period end date; use `"announce_time"` to filter by when the report was publicly disclosed.
6. **Field discovery** — Run `python scripts/test_financial_data.py --host HOST:PORT` to see all available fields on your xtquant version.
