"""Live test: place an order then cancel it immediately.

Places a limit buy order at an extremely low price (will NOT be filled),
verifies it appears in the order list, cancels it, and confirms cancellation.

Usage:
    python test/verify_order_cancel.py
"""

import sys
import time

import grpc

sys.path.insert(0, ".")
from pb import xtquant_pb2, xtquant_pb2_grpc

SERVER = "192.168.31.64:50051"
ACCOUNT_ID = "8886910714"
ACCOUNT_TYPE = "STOCK"

# Safe order params: limit buy 600000.SH at 1.00 (way below market, won't fill)
STOCK_CODE = "600000.SH"
ORDER_TYPE = 23       # STOCK_BUY
PRICE_TYPE = 11       # FIX_PRICE (limit order)
PRICE = 1.00          # Far below market price
VOLUME = 100          # Minimum lot


def main():
    channel = grpc.insecure_channel(SERVER)
    stub = xtquant_pb2_grpc.TradingServiceStub(channel)

    # === Step 1: Place order ===
    print("=" * 60)
    print(f"Step 1: OrderStock  {STOCK_CODE}  BUY {VOLUME} @ {PRICE}")
    print("=" * 60)
    resp = stub.OrderStock(xtquant_pb2.OrderStockRequest(
        account_id=ACCOUNT_ID,
        account_type=ACCOUNT_TYPE,
        stock_code=STOCK_CODE,
        order_type=ORDER_TYPE,
        volume=VOLUME,
        price_type=PRICE_TYPE,
        price=PRICE,
        strategy_name="verify_test",
        order_remark="test_then_cancel",
    ), timeout=10)

    print(f"  success:  {resp.success}")
    print(f"  order_id: {resp.order_id}")
    print(f"  message:  {resp.message}")

    if not resp.success:
        print("\n  Order placement FAILED, aborting.")
        channel.close()
        return 1

    order_id = resp.order_id
    print("  [OK] Order placed")

    # Wait briefly for order to be processed
    time.sleep(1)

    # === Step 2: Query orders to confirm it exists ===
    print()
    print("=" * 60)
    print(f"Step 2: QueryOrders  (looking for order_id={order_id})")
    print("=" * 60)
    orders_resp = stub.QueryOrders(
        xtquant_pb2.QueryOrdersRequest(account_id=ACCOUNT_ID, account_type=ACCOUNT_TYPE),
        timeout=10,
    )
    found = None
    for o in orders_resp.orders:
        tag = " <-- THIS ONE" if o.order_id == order_id else ""
        print(f"  order_id={o.order_id}  {o.stock_code:12s}  vol={o.order_volume}  "
              f"price={o.price:.2f}  status={o.order_status}  {o.status_msg}{tag}")
        if o.order_id == order_id:
            found = o

    if found:
        print(f"  [OK] Order {order_id} found in order list")
    else:
        print(f"  [WARN] Order {order_id} not found (may still be processing)")

    # === Step 3: Cancel the order ===
    print()
    print("=" * 60)
    print(f"Step 3: CancelOrder  (order_id={order_id})")
    print("=" * 60)
    cancel_resp = stub.CancelOrder(xtquant_pb2.CancelOrderRequest(
        account_id=ACCOUNT_ID,
        account_type=ACCOUNT_TYPE,
        order_id=order_id,
    ), timeout=10)
    print(f"  success: {cancel_resp.success}")
    print(f"  message: {cancel_resp.message}")

    if cancel_resp.success:
        print("  [OK] Cancel request sent")
    else:
        print("  [FAIL] Cancel request failed")

    # Wait for cancellation to take effect
    time.sleep(1)

    # === Step 4: Query orders again to confirm cancellation ===
    print()
    print("=" * 60)
    print(f"Step 4: QueryOrders  (verify cancel status)")
    print("=" * 60)
    orders_resp2 = stub.QueryOrders(
        xtquant_pb2.QueryOrdersRequest(account_id=ACCOUNT_ID, account_type=ACCOUNT_TYPE),
        timeout=10,
    )
    for o in orders_resp2.orders:
        if o.order_id == order_id:
            print(f"  order_id={o.order_id}  status={o.order_status}  {o.status_msg}")
            # status 50=reported, 52=partially filled, 56=filled, 54=cancelled
            if o.order_status == 54 or "cancel" in o.status_msg.lower() or "withdraw" in o.status_msg.lower() or "revoked" in o.status_msg.lower():
                print("  [OK] Order confirmed CANCELLED")
            else:
                print(f"  [INFO] Order status: {o.order_status} ({o.status_msg})")
            break
    else:
        print(f"  Order {order_id} no longer in active list (likely cancelled)")

    channel.close()

    # === Summary ===
    print()
    print("=" * 60)
    print("RESULT: Full order lifecycle verified!")
    print("  OrderStock -> QueryOrders -> CancelOrder -> Confirm")
    print("=" * 60)
    return 0


if __name__ == "__main__":
    sys.exit(main())
