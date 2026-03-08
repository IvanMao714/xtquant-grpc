"""Live verification of TradingService against a running gRPC server.

Read-only queries only — no orders will be placed.

Usage:
    python test/verify_trading_live.py
"""

import sys
import grpc

sys.path.insert(0, ".")
from pb import xtquant_pb2, xtquant_pb2_grpc

SERVER = "192.168.31.64:50051"
ACCOUNT_ID = "8886910714"
ACCOUNT_TYPE = "STOCK"


def main():
    channel = grpc.insecure_channel(SERVER)
    stub = xtquant_pb2_grpc.TradingServiceStub(channel)
    account = xtquant_pb2.AccountRequest(account_id=ACCOUNT_ID, account_type=ACCOUNT_TYPE)

    all_ok = True

    # --- 1. QueryAsset ---
    print("=" * 60)
    print("1. QueryAsset")
    print("=" * 60)
    try:
        asset = stub.QueryAsset(account, timeout=10)
        print(f"  account_id:   {asset.account_id}")
        print(f"  cash:         {asset.cash:,.2f}")
        print(f"  frozen_cash:  {asset.frozen_cash:,.2f}")
        print(f"  market_value: {asset.market_value:,.2f}")
        print(f"  total_asset:  {asset.total_asset:,.2f}")
        print("  [OK]")
    except Exception as e:
        print(f"  [FAIL] {e}")
        all_ok = False

    # --- 2. QueryPositions ---
    print()
    print("=" * 60)
    print("2. QueryPositions")
    print("=" * 60)
    try:
        pos_resp = stub.QueryPositions(account, timeout=10)
        if pos_resp.positions:
            for p in pos_resp.positions:
                print(f"  {p.stock_code:12s}  vol={p.volume:>6d}  avail={p.can_use_volume:>6d}  "
                      f"mkt_val={p.market_value:>12,.2f}  avg_price={p.avg_price:.3f}")
        else:
            print("  (no positions)")
        print(f"  [OK] {len(pos_resp.positions)} position(s)")
    except Exception as e:
        print(f"  [FAIL] {e}")
        all_ok = False

    # --- 3. QueryOrders ---
    print()
    print("=" * 60)
    print("3. QueryOrders")
    print("=" * 60)
    try:
        orders_resp = stub.QueryOrders(
            xtquant_pb2.QueryOrdersRequest(account_id=ACCOUNT_ID, account_type=ACCOUNT_TYPE),
            timeout=10,
        )
        if orders_resp.orders:
            for o in orders_resp.orders:
                print(f"  order_id={o.order_id}  {o.stock_code:12s}  type={o.order_type}  "
                      f"vol={o.order_volume}  price={o.price:.3f}  traded={o.traded_volume}  "
                      f"status={o.order_status}  {o.status_msg}")
        else:
            print("  (no orders today)")
        print(f"  [OK] {len(orders_resp.orders)} order(s)")
    except Exception as e:
        print(f"  [FAIL] {e}")
        all_ok = False

    # --- 4. QueryTrades ---
    print()
    print("=" * 60)
    print("4. QueryTrades")
    print("=" * 60)
    try:
        trades_resp = stub.QueryTrades(account, timeout=10)
        if trades_resp.trades:
            for t in trades_resp.trades:
                print(f"  traded_id={t.traded_id}  {t.stock_code:12s}  "
                      f"price={t.traded_price:.3f}  vol={t.traded_volume}  "
                      f"amount={t.traded_amount:,.2f}")
        else:
            print("  (no trades today)")
        print(f"  [OK] {len(trades_resp.trades)} trade(s)")
    except Exception as e:
        print(f"  [FAIL] {e}")
        all_ok = False

    channel.close()

    # --- Summary ---
    print()
    print("=" * 60)
    if all_ok:
        print("RESULT: ALL PASSED - Trading service is fully operational!")
    else:
        print("RESULT: SOME QUERIES FAILED - check errors above")
    print("=" * 60)

    return 0 if all_ok else 1


if __name__ == "__main__":
    sys.exit(main())
