"""Trading gRPC service — wraps xtquant.xttrader module

Exposes xttrader trading APIs to remote gRPC clients,
supporting order placement, cancellation, queries, and real-time event streaming.
"""

import queue
import logging
import threading

import grpc
from xtquant.xttrader import XtQuantTrader, XtQuantTraderCallback
from xtquant.xttype import StockAccount

from pb import xtquant_pb2, xtquant_pb2_grpc

logger = logging.getLogger(__name__)


# ====================== Data Conversion Helpers ======================


def _make_account(account_id: str, account_type: str = "STOCK") -> StockAccount:
    """Create a StockAccount object."""
    return StockAccount(account_id, account_type or "STOCK")


def _order_to_pb(order) -> xtquant_pb2.OrderInfo:
    """XtOrder -> protobuf OrderInfo"""
    return xtquant_pb2.OrderInfo(
        account_id=order.account_id,
        stock_code=order.stock_code,
        order_id=order.order_id,
        order_sysid=order.order_sysid or "",
        order_time=order.order_time,
        order_type=order.order_type,
        order_volume=order.order_volume,
        price=order.price,
        traded_volume=order.traded_volume,
        traded_price=order.traded_price,
        order_status=order.order_status,
        status_msg=order.status_msg or "",
        strategy_name=order.strategy_name or "",
        order_remark=order.order_remark or "",
    )


def _trade_to_pb(trade) -> xtquant_pb2.TradeInfo:
    """XtTrade -> protobuf TradeInfo"""
    return xtquant_pb2.TradeInfo(
        account_id=trade.account_id,
        stock_code=trade.stock_code,
        traded_id=trade.traded_id or "",
        traded_time=trade.traded_time,
        traded_price=trade.traded_price,
        traded_volume=trade.traded_volume,
        traded_amount=trade.traded_amount,
        order_id=trade.order_id,
        order_sysid=trade.order_sysid or "",
        strategy_name=trade.strategy_name or "",
        order_remark=trade.order_remark or "",
    )


def _position_to_pb(pos) -> xtquant_pb2.PositionInfo:
    """XtPosition -> protobuf PositionInfo"""
    return xtquant_pb2.PositionInfo(
        account_id=pos.account_id,
        stock_code=pos.stock_code,
        volume=pos.volume,
        can_use_volume=pos.can_use_volume,
        open_price=pos.open_price,
        market_value=pos.market_value,
        frozen_volume=pos.frozen_volume,
        avg_price=pos.avg_price,
    )


# ====================== Trading Callback ======================


class _TradingCallback(XtQuantTraderCallback):
    """Trading callback that forwards xttrader events to gRPC stream subscribers.

    Manages subscribers as (account_id, queue) pairs, filtering events by account.
    """

    def __init__(self):
        self._lock = threading.Lock()
        self._subscribers: list[tuple[str, queue.Queue]] = []

    def add_subscriber(self, account_id: str, q: queue.Queue):
        with self._lock:
            self._subscribers.append((account_id, q))

    def remove_subscriber(self, q: queue.Queue):
        with self._lock:
            self._subscribers = [(a, sq) for a, sq in self._subscribers if sq is not q]

    def _broadcast(self, event: xtquant_pb2.TradingEvent, account_id: str = ""):
        """Broadcast event to matching subscribers."""
        with self._lock:
            for sub_acc, sub_q in self._subscribers:
                if not account_id or sub_acc == account_id:
                    sub_q.put(event)

    def on_disconnected(self):
        logger.warning("Trading connection lost")
        self._broadcast(xtquant_pb2.TradingEvent(disconnected="disconnected"))

    def on_stock_order(self, order):
        self._broadcast(
            xtquant_pb2.TradingEvent(order_update=_order_to_pb(order)),
            order.account_id,
        )

    def on_stock_trade(self, trade):
        self._broadcast(
            xtquant_pb2.TradingEvent(trade_update=_trade_to_pb(trade)),
            trade.account_id,
        )

    def on_order_error(self, order_error):
        self._broadcast(xtquant_pb2.TradingEvent(
            order_error=xtquant_pb2.OrderErrorInfo(
                order_id=order_error.order_id,
                error_id=order_error.error_id,
                error_msg=order_error.error_msg,
            ),
        ))

    def on_cancel_error(self, cancel_error):
        self._broadcast(xtquant_pb2.TradingEvent(
            cancel_error=xtquant_pb2.CancelErrorInfo(
                order_id=cancel_error.order_id,
                error_id=cancel_error.error_id,
                error_msg=cancel_error.error_msg,
            ),
        ))


# ====================== Service Implementation ======================


class TradingServicer(xtquant_pb2_grpc.TradingServiceServicer):
    """Trading gRPC service.

    Connects to MiniQMT on initialization and registers trading callbacks.
    The service lifecycle matches the gRPC server.
    """

    def __init__(self, mini_qmt_path: str, session_id: int):
        self._callback = _TradingCallback()
        self._subscribed_accounts: set[str] = set()
        self._lock = threading.Lock()

        # Initialize trading connection
        self.xt_trader = XtQuantTrader(mini_qmt_path, session_id)
        self.xt_trader.register_callback(self._callback)
        self.xt_trader.start()

        result = self.xt_trader.connect()
        if result != 0:
            raise RuntimeError(f"Failed to connect MiniQMT (code={result}), ensure the client is running")
        logger.info("Trading service connected to MiniQMT (path=%s, session=%d)", mini_qmt_path, session_id)

    def OrderStock(self, request, context):
        """Place order -> xt_trader.order_stock"""
        acc = _make_account(request.account_id, request.account_type)
        order_id = self.xt_trader.order_stock(
            acc,
            request.stock_code,
            request.order_type,
            request.volume,
            request.price_type,
            request.price,
            request.strategy_name,
            request.order_remark,
        )
        success = order_id >= 0
        return xtquant_pb2.OrderStockResponse(
            order_id=order_id if success else 0,
            success=success,
            message="Order placed" if success else f"Order failed (code={order_id})",
        )

    def CancelOrder(self, request, context):
        """Cancel order -> xt_trader.cancel_order_stock

        Returns 0 on success, -1 on failure.
        """
        acc = _make_account(request.account_id, request.account_type)
        result = self.xt_trader.cancel_order_stock(acc, int(request.order_id))
        return xtquant_pb2.CancelOrderResponse(
            success=(result == 0),
            message="Order cancelled" if result == 0 else f"Cancel failed (code={result})",
        )

    def QueryAsset(self, request, context):
        """Query account asset -> xt_trader.query_stock_asset"""
        acc = _make_account(request.account_id, request.account_type)
        asset = self.xt_trader.query_stock_asset(acc)
        if not asset:
            context.abort(grpc.StatusCode.NOT_FOUND, "Failed to query asset")
        return xtquant_pb2.AssetInfo(
            account_id=request.account_id,
            cash=asset.cash,
            frozen_cash=asset.frozen_cash,
            market_value=asset.market_value,
            total_asset=asset.total_asset,
        )

    def QueryOrders(self, request, context):
        """Query orders -> xt_trader.query_stock_orders"""
        acc = _make_account(request.account_id, request.account_type)
        orders = self.xt_trader.query_stock_orders(acc, cancelable_only=request.cancelable_only)
        return xtquant_pb2.QueryOrdersResponse(
            orders=[_order_to_pb(o) for o in orders],
        )

    def QueryTrades(self, request, context):
        """Query trades -> xt_trader.query_stock_trades"""
        acc = _make_account(request.account_id, request.account_type)
        trades = self.xt_trader.query_stock_trades(acc)
        return xtquant_pb2.QueryTradesResponse(
            trades=[_trade_to_pb(t) for t in trades],
        )

    def QueryPositions(self, request, context):
        """Query positions -> xt_trader.query_stock_positions"""
        acc = _make_account(request.account_id, request.account_type)
        positions = self.xt_trader.query_stock_positions(acc)
        return xtquant_pb2.QueryPositionsResponse(
            positions=[_position_to_pb(p) for p in positions],
        )

    def SubscribeTrading(self, request, context):
        """Subscribe to trading events (server stream)

        Pushes xttrader callback events to clients via gRPC streaming.
        Each client connection gets its own event queue, filtered by account.
        """
        acc = _make_account(request.account_id, request.account_type)

        # Ensure account is subscribed (idempotent)
        with self._lock:
            if request.account_id not in self._subscribed_accounts:
                result = self.xt_trader.subscribe(acc)
                if result != 0:
                    context.abort(grpc.StatusCode.INTERNAL, f"Failed to subscribe account (code={result})")
                self._subscribed_accounts.add(request.account_id)

        # Create event queue for this connection
        event_queue: queue.Queue = queue.Queue()
        self._callback.add_subscriber(request.account_id, event_queue)
        logger.info("Client subscribed to trading events: %s", request.account_id)

        while context.is_active():
            try:
                event = event_queue.get(timeout=1.0)
                yield event
            except queue.Empty:
                continue

        self._callback.remove_subscriber(event_queue)
        logger.info("Client disconnected from trading events: %s", request.account_id)
