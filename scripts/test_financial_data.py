"""Financial data exploration script.

Connects to the gRPC server and dumps all financial data table schemas,
instrument detail fields, and identifies available valuation metrics.

Usage:
    python scripts/test_financial_data.py [--host HOST:PORT]
"""

import json
import argparse

import grpc
from pb import xtquant_pb2, xtquant_pb2_grpc

# All available financial data tables in xtdata
ALL_TABLES = [
    "Balance",          # Balance sheet
    "Income",           # Income statement
    "CashFlow",         # Cash flow statement
    "Capital",          # Share capital
    "Holdernum",        # Shareholder count
    "Top10holder",      # Top 10 shareholders
    "Top10flowholder",  # Top 10 float shareholders
    "Pershareindex",    # Per-share metrics
]

SAMPLE_STOCK = "600000.SH"

# Known valuation-related keywords to highlight
VALUATION_KEYWORDS = [
    "pe", "pb", "ps", "eps", "roe", "roa",
    "dividend", "turnover", "capital", "share",
    "profit", "revenue", "market", "earning",
]


def download_financial_data(stub):
    """Download financial data for the sample stock before querying."""
    print("=" * 70)
    print(f"  Downloading Financial Data — {SAMPLE_STOCK}")
    print("=" * 70)

    for progress in stub.DownloadFinancialData(xtquant_pb2.DownloadFinancialDataRequest(
        stock_codes=[SAMPLE_STOCK],
        table_list=ALL_TABLES,
    )):
        if progress.stock_code:
            print(f"  [{progress.finished}/{progress.total}] {progress.stock_code}")
        else:
            print(f"  {progress.message}")

    print("  Download complete.\n")


def explore_financial_tables(stub):
    """Fetch and display all financial table schemas."""
    print("=" * 70)
    print(f"  Financial Data Exploration — {SAMPLE_STOCK}")
    print("=" * 70)

    resp = stub.GetFinancialData(xtquant_pb2.GetFinancialDataRequest(
        stock_codes=[SAMPLE_STOCK],
        table_list=ALL_TABLES,
    ))
    data = json.loads(resp.data_json)

    if SAMPLE_STOCK not in data:
        print(f"ERROR: No data returned for {SAMPLE_STOCK}")
        return

    stock_data = data[SAMPLE_STOCK]
    valuation_fields = {}  # table -> [field names]

    for table_name in ALL_TABLES:
        print(f"\n{'─' * 70}")
        print(f"  Table: {table_name}")
        print(f"{'─' * 70}")

        if table_name not in stock_data:
            print("  (no data returned)")
            continue

        records = stock_data[table_name]
        if not records:
            print("  (empty table)")
            continue

        print(f"  Records: {len(records)}")
        latest = records[-1]  # Most recent record

        print(f"  Fields ({len(latest)} total):")
        found_valuation = []
        for key, value in sorted(latest.items()):
            marker = ""
            key_lower = key.lower()
            if any(kw in key_lower for kw in VALUATION_KEYWORDS):
                marker = " <-- valuation"
                found_valuation.append(key)
            print(f"    {key:40s} = {value!r}{marker}")

        if found_valuation:
            valuation_fields[table_name] = found_valuation

    # Summary
    print(f"\n{'=' * 70}")
    print("  Valuation Fields Summary")
    print(f"{'=' * 70}")
    if valuation_fields:
        for table, fields in valuation_fields.items():
            print(f"\n  [{table}]")
            for f in fields:
                print(f"    - {f}")
    else:
        print("  No valuation-related fields found!")


def explore_instrument_detail(stub):
    """Fetch and display complete instrument detail."""
    print(f"\n{'=' * 70}")
    print(f"  Instrument Detail — {SAMPLE_STOCK} (is_complete=True)")
    print(f"{'=' * 70}")

    detail = stub.GetInstrumentDetail(xtquant_pb2.GetInstrumentDetailRequest(
        stock_code=SAMPLE_STOCK,
        is_complete=True,
    ))

    print(f"  exchange_id      = {detail.exchange_id}")
    print(f"  instrument_id    = {detail.instrument_id}")
    print(f"  instrument_name  = {detail.instrument_name}")
    print(f"  total_volume     = {detail.total_volume:,} (total shares)")
    print(f"  float_volume     = {detail.float_volume:,} (float shares)")
    print(f"  pre_close        = {detail.pre_close}")
    print(f"  up_stop_price    = {detail.up_stop_price}")
    print(f"  down_stop_price  = {detail.down_stop_price}")
    print(f"  open_date        = {detail.open_date}")
    print(f"  price_tick       = {detail.price_tick}")

    if detail.extra_json:
        extra = json.loads(detail.extra_json)
        print(f"\n  All fields ({len(extra)} total):")
        for key, value in sorted(extra.items()):
            print(f"    {key:40s} = {value!r}")


def main():
    parser = argparse.ArgumentParser(description="Explore xtquant financial data via gRPC")
    parser.add_argument("--host", default="localhost:50051", help="gRPC server address")
    args = parser.parse_args()

    MAX_MSG = 1024 * 1024 * 256  # 256 MB
    channel = grpc.insecure_channel(args.host, options=[
        ("grpc.max_receive_message_length", MAX_MSG),
        ("grpc.max_send_message_length", MAX_MSG),
    ])
    stub = xtquant_pb2_grpc.MarketDataServiceStub(channel)

    print(f"Connecting to gRPC server at {args.host} ...\n")

    # Step 1: Download data first (required before querying)
    download_financial_data(stub)

    # Step 2: Explore table schemas
    explore_financial_tables(stub)

    # Step 3: Explore instrument detail
    explore_instrument_detail(stub)

    print(f"\n{'=' * 70}")
    print("  Done!")
    print(f"{'=' * 70}")


if __name__ == "__main__":
    main()
