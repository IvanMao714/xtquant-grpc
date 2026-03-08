"""Trading service gRPC round-trip tests — verify proto -> server -> xttrader pipeline

Uses mocked xttrader to avoid requiring a real MiniQMT connection.
Tests verify:
  - Protobuf serialization/deserialization for all trading RPCs
  - Server-side data conversion logic (xttrader objects -> protobuf)
  - Callback/streaming mechanism for trade events
  - Error handling (order failure, cancel failure)
"""

import time
import threading
from types import SimpleNamespace
from unittest.mock import MagicMock, patch
from concurrent import futures

import grpc
import pytest

from pb import xtquant_pb2, xtquant_pb2_grpc


TRADING_TEST_PORT = 50198


# ====================== Mock Data Factories ======================


def make_mock_order(**kwargs):
    """Create a mock XtOrder-like object with sensible defaults."""
    defaults = dict(
        account_id="TEST_ACCOUNT",
        stock_code="600000.SH",
        order_id=12345,
        order_sysid="SYS001",
        order_time=1700000000,
        order_type=23,  # STOCK_BUY
        order_volume=100,
        price=10.5,
        traded_volume=0,
        traded_price=0.0,
        order_status=50,  # reported
        status_msg="Submitted",
        strategy_name="test_strategy",
        order_remark="test_remark",
    )
    defaults.update(kwargs)
    return SimpleNamespace(**defaults)


def make_mock_trade(**kwargs):
    """Create a mock XtTrade-like object."""
    defaults = dict(
        account_id="TEST_ACCOUNT",
        stock_code="600000.SH",
        traded_id="T001",
        traded_time=1700000100,
        traded_price=10.5,
        traded_volume=100,
        traded_amount=1050.0,
        order_id=12345,
        order_sysid="SYS001",
        strategy_name="test_strategy",
        order_remark="test_remark",
    )
    defaults.update(kwargs)
    return SimpleNamespace(**defaults)


def make_mock_position(**kwargs):
    """Create a mock XtPosition-like object."""
    defaults = dict(
        account_id="TEST_ACCOUNT",
        stock_code="600000.SH",
        volume=1000,
        can_use_volume=800,
        open_price=10.0,
        market_value=10500.0,
        frozen_volume=200,
        avg_price=10.2,
    )
    defaults.update(kwargs)
    return SimpleNamespace(**defaults)


def make_mock_asset(**kwargs):
    """Create a mock XtAsset-like object."""
    defaults = dict(
        cash=100000.0,
        frozen_cash=5000.0,
        market_value=200000.0,
        total_asset=300000.0,
    )
    defaults.update(kwargs)
    return SimpleNamespace(**defaults)


# ====================== Fixtures ======================


@pytest.fixture(scope="module")
def mock_xt_trader():
    """Create a fully mocked XtQuantTrader with default return values."""
    trader = MagicMock()
    trader.connect.return_value = 0
    trader.start.return_value = None
    trader.register_callback.return_value = None
    trader.subscribe.return_value = 0

    # Default RPC return values
    trader.order_stock.return_value = 12345
    trader.cancel_order_stock.return_value = 0
    trader.query_stock_asset.return_value = make_mock_asset()
    trader.query_stock_orders.return_value = [make_mock_order()]
    trader.query_stock_trades.return_value = [make_mock_trade()]
    trader.query_stock_positions.return_value = [make_mock_position()]

    return trader


@pytest.fixture(scope="module")
def trading_grpc_server(mock_xt_trader):
    """Start a gRPC server with mocked TradingServicer.

    Patches XtQuantTrader during TradingServicer.__init__ so it uses
    our mock instead of trying to connect to a real MiniQMT instance.
    """
    with patch("server.trading.XtQuantTrader", return_value=mock_xt_trader):
        from server.trading import TradingServicer
        servicer = TradingServicer("fake_qmt_path", 99999)

    server = grpc.server(futures.ThreadPoolExecutor(max_workers=4))
    xtquant_pb2_grpc.add_TradingServiceServicer_to_server(servicer, server)
    server.add_insecure_port(f"[::]:{TRADING_TEST_PORT}")
    server.start()
    print(f"\n[fixture] Trading gRPC server started on port {TRADING_TEST_PORT}")
    yield server, servicer
    server.stop(grace=2)
    print("\n[fixture] Trading gRPC server stopped")


@pytest.fixture(scope="module")
def trading_channel(trading_grpc_server):
    """gRPC channel to the test trading server."""
    channel = grpc.insecure_channel(f"localhost:{TRADING_TEST_PORT}")
    yield channel
    channel.close()


@pytest.fixture(scope="module")
def trading_stub(trading_channel):
    """TradingService gRPC stub."""
    return xtquant_pb2_grpc.TradingServiceStub(trading_channel)


# ====================== OrderStock Tests ======================


class TestOrderStock:
    """gRPC OrderStock endpoint"""

    def test_order_success(self, trading_stub, mock_xt_trader):
        """Successful order placement returns positive order_id."""
        mock_xt_trader.order_stock.return_value = 12345
        resp = trading_stub.OrderStock(xtquant_pb2.OrderStockRequest(
            account_id="TEST_ACCOUNT",
            account_type="STOCK",
            stock_code="600000.SH",
            order_type=23,  # STOCK_BUY
            volume=100,
            price_type=11,  # FIX_PRICE
            price=10.5,
            strategy_name="test",
            order_remark="remark",
        ))
        assert resp.success is True
        assert resp.order_id == 12345
        assert resp.message
        print(f"\n  Order placed: id={resp.order_id} msg={resp.message}")

    def test_order_failure(self, trading_stub, mock_xt_trader):
        """Failed order returns success=False and order_id=0."""
        mock_xt_trader.order_stock.return_value = -1
        resp = trading_stub.OrderStock(xtquant_pb2.OrderStockRequest(
            account_id="TEST_ACCOUNT",
            account_type="STOCK",
            stock_code="600000.SH",
            order_type=23,
            volume=100,
            price_type=11,
            price=10.5,
        ))
        assert resp.success is False
        assert resp.order_id == 0
        print(f"\n  Order failed (expected): msg={resp.message}")

    def test_order_params_passed_correctly(self, trading_stub, mock_xt_trader):
        """Verify all request parameters are forwarded to xt_trader.order_stock."""
        mock_xt_trader.order_stock.return_value = 99999
        trading_stub.OrderStock(xtquant_pb2.OrderStockRequest(
            account_id="ACC123",
            account_type="STOCK",
            stock_code="000001.SZ",
            order_type=24,  # STOCK_SELL
            volume=200,
            price_type=5,   # LATEST_PRICE
            price=15.0,
            strategy_name="my_strategy",
            order_remark="my_remark",
        ))
        # Verify the mock was called with correct params
        args = mock_xt_trader.order_stock.call_args
        assert args[0][1] == "000001.SZ"      # stock_code
        assert args[0][2] == 24                # order_type (STOCK_SELL)
        assert args[0][3] == 200               # volume
        assert args[0][4] == 5                 # price_type
        assert args[0][5] == 15.0              # price
        assert args[0][6] == "my_strategy"     # strategy_name
        assert args[0][7] == "my_remark"       # order_remark
        print("\n  All order params forwarded correctly")


# ====================== CancelOrder Tests ======================


class TestCancelOrder:
    """gRPC CancelOrder endpoint"""

    def test_cancel_success(self, trading_stub, mock_xt_trader):
        """Successful cancellation returns success=True."""
        mock_xt_trader.cancel_order_stock.return_value = 0
        resp = trading_stub.CancelOrder(xtquant_pb2.CancelOrderRequest(
            account_id="TEST_ACCOUNT",
            account_type="STOCK",
            order_id=12345,
        ))
        assert resp.success is True
        print(f"\n  Cancel success: msg={resp.message}")

    def test_cancel_failure(self, trading_stub, mock_xt_trader):
        """Failed cancellation returns success=False."""
        mock_xt_trader.cancel_order_stock.return_value = -1
        resp = trading_stub.CancelOrder(xtquant_pb2.CancelOrderRequest(
            account_id="TEST_ACCOUNT",
            account_type="STOCK",
            order_id=99999,
        ))
        assert resp.success is False
        print(f"\n  Cancel failed (expected): msg={resp.message}")


# ====================== QueryAsset Tests ======================


class TestQueryAsset:
    """gRPC QueryAsset endpoint"""

    def test_query_asset(self, trading_stub, mock_xt_trader):
        """Query asset returns correct financial data."""
        mock_xt_trader.query_stock_asset.return_value = make_mock_asset(
            cash=100000.0,
            frozen_cash=5000.0,
            market_value=200000.0,
            total_asset=300000.0,
        )
        resp = trading_stub.QueryAsset(xtquant_pb2.AccountRequest(
            account_id="TEST_ACCOUNT",
            account_type="STOCK",
        ))
        assert resp.account_id == "TEST_ACCOUNT"
        assert resp.cash == 100000.0
        assert resp.frozen_cash == 5000.0
        assert resp.market_value == 200000.0
        assert resp.total_asset == 300000.0
        print(f"\n  Asset: cash={resp.cash} frozen={resp.frozen_cash} "
              f"market_value={resp.market_value} total={resp.total_asset}")


# ====================== QueryOrders Tests ======================


class TestQueryOrders:
    """gRPC QueryOrders endpoint"""

    def test_query_orders(self, trading_stub, mock_xt_trader):
        """Query multiple orders with correct field mapping."""
        mock_xt_trader.query_stock_orders.return_value = [
            make_mock_order(order_id=1, stock_code="600000.SH", order_volume=100),
            make_mock_order(order_id=2, stock_code="000001.SZ", order_volume=200),
        ]
        resp = trading_stub.QueryOrders(xtquant_pb2.QueryOrdersRequest(
            account_id="TEST_ACCOUNT",
            account_type="STOCK",
        ))
        assert len(resp.orders) == 2
        assert resp.orders[0].order_id == 1
        assert resp.orders[0].stock_code == "600000.SH"
        assert resp.orders[0].order_volume == 100
        assert resp.orders[1].order_id == 2
        assert resp.orders[1].stock_code == "000001.SZ"
        print(f"\n  Orders: {len(resp.orders)} returned")

    def test_query_orders_empty(self, trading_stub, mock_xt_trader):
        """Empty order list returns empty response."""
        mock_xt_trader.query_stock_orders.return_value = []
        resp = trading_stub.QueryOrders(xtquant_pb2.QueryOrdersRequest(
            account_id="TEST_ACCOUNT",
            account_type="STOCK",
        ))
        assert len(resp.orders) == 0
        print("\n  Empty orders: OK")

    def test_order_field_completeness(self, trading_stub, mock_xt_trader):
        """All order fields are correctly mapped from xttrader to protobuf."""
        mock_xt_trader.query_stock_orders.return_value = [
            make_mock_order(
                account_id="ACC1",
                stock_code="600000.SH",
                order_id=100,
                order_sysid="SYSID_001",
                order_time=1700000000,
                order_type=23,
                order_volume=500,
                price=12.5,
                traded_volume=300,
                traded_price=12.3,
                order_status=56,   # 已成
                status_msg="All filled",
                strategy_name="algo1",
                order_remark="remark1",
            ),
        ]
        resp = trading_stub.QueryOrders(xtquant_pb2.QueryOrdersRequest(
            account_id="ACC1",
            account_type="STOCK",
        ))
        o = resp.orders[0]
        assert o.account_id == "ACC1"
        assert o.stock_code == "600000.SH"
        assert o.order_id == 100
        assert o.order_sysid == "SYSID_001"
        assert o.order_time == 1700000000
        assert o.order_type == 23
        assert o.order_volume == 500
        assert o.price == 12.5
        assert o.traded_volume == 300
        assert o.traded_price == 12.3
        assert o.order_status == 56
        assert o.status_msg == "All filled"
        assert o.strategy_name == "algo1"
        assert o.order_remark == "remark1"
        print(f"\n  Order field completeness: all 14 fields verified")


# ====================== QueryTrades Tests ======================


class TestQueryTrades:
    """gRPC QueryTrades endpoint"""

    def test_query_trades(self, trading_stub, mock_xt_trader):
        """Query trades returns correct data."""
        mock_xt_trader.query_stock_trades.return_value = [
            make_mock_trade(traded_volume=100, traded_price=10.5, traded_amount=1050.0),
        ]
        resp = trading_stub.QueryTrades(xtquant_pb2.AccountRequest(
            account_id="TEST_ACCOUNT",
            account_type="STOCK",
        ))
        assert len(resp.trades) == 1
        t = resp.trades[0]
        assert t.traded_volume == 100
        assert t.traded_price == 10.5
        assert t.traded_amount == 1050.0
        print(f"\n  Trade: vol={t.traded_volume} price={t.traded_price} amount={t.traded_amount}")

    def test_trade_field_completeness(self, trading_stub, mock_xt_trader):
        """All trade fields are correctly mapped."""
        mock_xt_trader.query_stock_trades.return_value = [
            make_mock_trade(
                account_id="ACC1",
                stock_code="000001.SZ",
                traded_id="TRADE_001",
                traded_time=1700000200,
                traded_price=15.0,
                traded_volume=500,
                traded_amount=7500.0,
                order_id=88888,
                order_sysid="SYSID_002",
                strategy_name="algo2",
                order_remark="remark2",
            ),
        ]
        resp = trading_stub.QueryTrades(xtquant_pb2.AccountRequest(
            account_id="ACC1",
            account_type="STOCK",
        ))
        t = resp.trades[0]
        assert t.account_id == "ACC1"
        assert t.stock_code == "000001.SZ"
        assert t.traded_id == "TRADE_001"
        assert t.traded_time == 1700000200
        assert t.traded_price == 15.0
        assert t.traded_volume == 500
        assert t.traded_amount == 7500.0
        assert t.order_id == 88888
        assert t.order_sysid == "SYSID_002"
        assert t.strategy_name == "algo2"
        assert t.order_remark == "remark2"
        print(f"\n  Trade field completeness: all 11 fields verified")


# ====================== QueryPositions Tests ======================


class TestQueryPositions:
    """gRPC QueryPositions endpoint"""

    def test_query_positions(self, trading_stub, mock_xt_trader):
        """Query multiple positions."""
        mock_xt_trader.query_stock_positions.return_value = [
            make_mock_position(stock_code="600000.SH", volume=1000),
            make_mock_position(stock_code="000001.SZ", volume=500),
        ]
        resp = trading_stub.QueryPositions(xtquant_pb2.AccountRequest(
            account_id="TEST_ACCOUNT",
            account_type="STOCK",
        ))
        assert len(resp.positions) == 2
        assert resp.positions[0].stock_code == "600000.SH"
        assert resp.positions[0].volume == 1000
        assert resp.positions[1].stock_code == "000001.SZ"
        assert resp.positions[1].volume == 500
        print(f"\n  Positions: {len(resp.positions)} stocks")

    def test_position_field_completeness(self, trading_stub, mock_xt_trader):
        """All position fields are correctly mapped."""
        mock_xt_trader.query_stock_positions.return_value = [
            make_mock_position(
                account_id="ACC1",
                stock_code="600000.SH",
                volume=1000,
                can_use_volume=800,
                open_price=10.0,
                market_value=10500.0,
                frozen_volume=200,
                avg_price=10.2,
            ),
        ]
        resp = trading_stub.QueryPositions(xtquant_pb2.AccountRequest(
            account_id="ACC1",
            account_type="STOCK",
        ))
        p = resp.positions[0]
        assert p.account_id == "ACC1"
        assert p.stock_code == "600000.SH"
        assert p.volume == 1000
        assert p.can_use_volume == 800
        assert p.open_price == 10.0
        assert p.market_value == 10500.0
        assert p.frozen_volume == 200
        assert p.avg_price == 10.2
        print(f"\n  Position field completeness: all 8 fields verified")


# ====================== SubscribeTrading Tests ======================


class TestSubscribeTrading:
    """gRPC SubscribeTrading streaming endpoint"""

    def test_receive_order_and_trade_events(self, trading_stub, trading_grpc_server):
        """Order and trade events are pushed to streaming subscribers."""
        _, servicer = trading_grpc_server
        received = []

        def fetch():
            stream = trading_stub.SubscribeTrading(xtquant_pb2.AccountRequest(
                account_id="TEST_ACCOUNT",
                account_type="STOCK",
            ))
            for event in stream:
                received.append(event)
                if len(received) >= 2:
                    break

        t = threading.Thread(target=fetch, daemon=True)
        t.start()
        time.sleep(0.5)  # Wait for subscription to be established

        # Simulate order event via callback
        servicer._callback.on_stock_order(make_mock_order(
            account_id="TEST_ACCOUNT",
            order_id=111,
            stock_code="600000.SH",
        ))
        # Simulate trade event via callback
        servicer._callback.on_stock_trade(make_mock_trade(
            account_id="TEST_ACCOUNT",
            traded_volume=50,
        ))

        t.join(timeout=5)

        assert len(received) >= 2, f"Expected >=2 events, got {len(received)}"
        # First event: order update
        assert received[0].HasField("order_update")
        assert received[0].order_update.order_id == 111
        assert received[0].order_update.stock_code == "600000.SH"
        # Second event: trade update
        assert received[1].HasField("trade_update")
        assert received[1].trade_update.traded_volume == 50
        print(f"\n  Received {len(received)} events: order + trade")

    def test_receive_error_events(self, trading_stub, trading_grpc_server):
        """Order error and cancel error events are pushed correctly."""
        _, servicer = trading_grpc_server
        received = []

        def fetch():
            stream = trading_stub.SubscribeTrading(xtquant_pb2.AccountRequest(
                account_id="ERR_ACCOUNT",
                account_type="STOCK",
            ))
            for event in stream:
                received.append(event)
                if len(received) >= 2:
                    break

        t = threading.Thread(target=fetch, daemon=True)
        t.start()
        time.sleep(0.5)

        # Simulate order error (broadcast to all since no account_id on error)
        servicer._callback.on_order_error(SimpleNamespace(
            order_id=222,
            error_id=1001,
            error_msg="Insufficient funds",
        ))
        # Simulate cancel error
        servicer._callback.on_cancel_error(SimpleNamespace(
            order_id=333,
            error_id=1002,
            error_msg="Order not found",
        ))

        t.join(timeout=5)

        assert len(received) >= 2, f"Expected >=2 events, got {len(received)}"
        assert received[0].HasField("order_error")
        assert received[0].order_error.order_id == 222
        assert received[0].order_error.error_id == 1001
        assert received[0].order_error.error_msg == "Insufficient funds"
        assert received[1].HasField("cancel_error")
        assert received[1].cancel_error.order_id == 333
        assert received[1].cancel_error.error_msg == "Order not found"
        print(f"\n  Received error events: order_error + cancel_error")

    def test_disconnect_event(self, trading_stub, trading_grpc_server):
        """Disconnect event is broadcast to all subscribers."""
        _, servicer = trading_grpc_server
        received = []

        def fetch():
            stream = trading_stub.SubscribeTrading(xtquant_pb2.AccountRequest(
                account_id="DC_ACCOUNT",
                account_type="STOCK",
            ))
            for event in stream:
                received.append(event)
                break

        t = threading.Thread(target=fetch, daemon=True)
        t.start()
        time.sleep(0.5)

        servicer._callback.on_disconnected()

        t.join(timeout=5)

        assert len(received) >= 1, "Expected disconnect event"
        assert received[0].HasField("disconnected")
        assert received[0].disconnected == "disconnected"
        print(f"\n  Received disconnect event")

    def test_event_filtering_by_account(self, trading_stub, trading_grpc_server):
        """Events are filtered by account_id — subscriber only gets their own events."""
        _, servicer = trading_grpc_server
        received_a = []
        received_b = []

        def fetch_a():
            stream = trading_stub.SubscribeTrading(xtquant_pb2.AccountRequest(
                account_id="ACCOUNT_A",
                account_type="STOCK",
            ))
            for event in stream:
                received_a.append(event)
                break

        def fetch_b():
            stream = trading_stub.SubscribeTrading(xtquant_pb2.AccountRequest(
                account_id="ACCOUNT_B",
                account_type="STOCK",
            ))
            for event in stream:
                received_b.append(event)
                break

        ta = threading.Thread(target=fetch_a, daemon=True)
        tb = threading.Thread(target=fetch_b, daemon=True)
        ta.start()
        tb.start()
        time.sleep(0.5)

        # Send event only for ACCOUNT_A
        servicer._callback.on_stock_order(make_mock_order(
            account_id="ACCOUNT_A",
            order_id=777,
        ))
        # Send event only for ACCOUNT_B
        servicer._callback.on_stock_order(make_mock_order(
            account_id="ACCOUNT_B",
            order_id=888,
        ))

        ta.join(timeout=5)
        tb.join(timeout=5)

        assert len(received_a) >= 1
        assert received_a[0].order_update.order_id == 777
        assert len(received_b) >= 1
        assert received_b[0].order_update.order_id == 888
        print(f"\n  Event filtering: A got order 777, B got order 888")
