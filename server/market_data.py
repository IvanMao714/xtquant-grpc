"""Market data gRPC service — wraps xtquant.xtdata module

Exposes xtdata market-data APIs to remote gRPC clients,
supporting kline queries, tick snapshots, streaming subscriptions, etc.
"""

import json
import queue
import logging

import grpc
import pandas as pd
from xtquant import xtdata

from pb import xtquant_pb2, xtquant_pb2_grpc

logger = logging.getLogger(__name__)


# ====================== Data Conversion Helpers ======================


def _df_to_kline_bars(df: pd.DataFrame) -> list[xtquant_pb2.KlineBar]:
    """Convert an xtdata DataFrame to a list of KlineBar messages.

    The DataFrame index is timestamp (ms), columns include open/high/low/close, etc.
    """
    bars = []
    for ts, row in df.iterrows():
        bars.append(xtquant_pb2.KlineBar(
            time=int(ts),
            open=float(row.get("open", 0)),
            high=float(row.get("high", 0)),
            low=float(row.get("low", 0)),
            close=float(row.get("close", 0)),
            volume=float(row.get("volume", 0)),
            amount=float(row.get("amount", 0)),
            pre_close=float(row.get("preClose", 0)),
            suspend_flag=int(row["suspendFlag"]) if pd.notna(row.get("suspendFlag")) else 0,
            settlement_price=float(row.get("settelmentPrice", 0)),
            open_interest=float(row.get("openInterest", 0)),
        ))
    return bars


def _tick_to_snapshot(code: str, tick: dict) -> xtquant_pb2.TickSnapshot:
    """Convert an xtdata tick dict to a TickSnapshot message."""
    return xtquant_pb2.TickSnapshot(
        stock_code=code,
        time=int(tick.get("time", 0)),
        last_price=float(tick.get("lastPrice", 0)),
        open=float(tick.get("open", 0)),
        high=float(tick.get("high", 0)),
        low=float(tick.get("low", 0)),
        last_close=float(tick.get("lastClose", 0)),
        volume=float(tick.get("volume", 0)),
        amount=float(tick.get("amount", 0)),
        bid_price=[float(x) for x in tick.get("bidPrice", [])],
        bid_volume=[float(x) for x in tick.get("bidVol", [])],
        ask_price=[float(x) for x in tick.get("askPrice", [])],
        ask_volume=[float(x) for x in tick.get("askVol", [])],
    )


# ====================== Service Implementation ======================


class MarketDataServicer(xtquant_pb2_grpc.MarketDataServiceServicer):
    """Market data gRPC service, maps 1-to-1 to xtdata module functions."""

    def GetMarketData(self, request, context):
        """Get kline data -> xtdata.get_market_data_ex"""
        # proto3 int32 defaults to 0; treat 0 as "fetch all"
        count = request.count if request.count != 0 else -1
        data = xtdata.get_market_data_ex(
            [],
            list(request.stock_codes),
            period=request.period or "1d",
            start_time=request.start_time,
            end_time=request.end_time,
            count=count,
            dividend_type=request.dividend_type or "none",
            fill_data=request.fill_data,
        )
        result = {code: xtquant_pb2.StockKlines(bars=_df_to_kline_bars(df))
                  for code, df in data.items()}
        return xtquant_pb2.GetMarketDataResponse(data=result)

    def GetFullTick(self, request, context):
        """Get real-time tick snapshot -> xtdata.get_full_tick"""
        data = xtdata.get_full_tick(list(request.stock_codes))
        ticks = {code: _tick_to_snapshot(code, tick) for code, tick in data.items()}
        return xtquant_pb2.GetFullTickResponse(ticks=ticks)

    def GetInstrumentDetail(self, request, context):
        """Get instrument info -> xtdata.get_instrument_detail"""
        detail = xtdata.get_instrument_detail(request.stock_code, request.is_complete)
        if not detail:
            context.abort(grpc.StatusCode.NOT_FOUND, f"Instrument {request.stock_code} not found")

        extra = json.dumps(detail, ensure_ascii=False, default=str) if request.is_complete else ""
        return xtquant_pb2.InstrumentDetail(
            exchange_id=str(detail.get("ExchangeID", "")),
            instrument_id=str(detail.get("InstrumentID", "")),
            instrument_name=str(detail.get("InstrumentName", "")),
            product_id=str(detail.get("ProductID", "")),
            up_stop_price=float(detail.get("UpStopPrice", 0)),
            down_stop_price=float(detail.get("DownStopPrice", 0)),
            pre_close=float(detail.get("PreClose", 0)),
            open_date=str(detail.get("OpenDate", "")),
            price_tick=float(detail.get("PriceTick", 0)),
            volume_multiple=int(detail.get("VolumeMultiple", 0)),
            total_volume=int(detail.get("TotalVolume", 0)),
            float_volume=int(detail.get("FloatVolume", 0)),
            extra_json=extra,
        )

    def GetStockList(self, request, context):
        """Get sector constituents -> xtdata.get_stock_list_in_sector"""
        stocks = xtdata.get_stock_list_in_sector(request.sector_name)
        return xtquant_pb2.StockListResponse(stock_codes=stocks)

    def GetSectorList(self, request, context):
        """Get all sector names -> xtdata.get_sector_list"""
        sectors = xtdata.get_sector_list()
        return xtquant_pb2.GetSectorListResponse(sectors=sectors)

    def DownloadHistoryData(self, request, context):
        """Download historical data to local -> xtdata.download_history_data"""
        for code in request.stock_codes:
            xtdata.download_history_data(
                code,
                period=request.period or "1d",
                start_time=request.start_time,
                end_time=request.end_time,
                incrementally=True if request.incrementally else None,
            )
        return xtquant_pb2.DownloadHistoryDataResponse(
            success=True,
            message=f"Download completed: {len(request.stock_codes)} instruments",
        )

    def GetTradingCalendar(self, request, context):
        """Get trading calendar -> xtdata.get_trading_calendar"""
        dates = xtdata.get_trading_calendar(
            request.market or "SH",
            start_time=request.start_time,
            end_time=request.end_time,
        )
        return xtquant_pb2.TradingCalendarResponse(dates=[str(d) for d in dates])

    def GetFinancialData(self, request, context):
        """Get financial data (JSON response) -> xtdata.get_financial_data

        Financial data has complex schemas (balance sheet / income / cash flow, etc.),
        serialized as JSON for flexibility.
        """
        data = xtdata.get_financial_data(
            list(request.stock_codes),
            table_list=list(request.table_list) or [],
            start_time=request.start_time,
            end_time=request.end_time,
        )
        result = {}
        for code, tables in data.items():
            result[code] = {}
            for name, df in tables.items():
                result[code][name] = df.to_dict(orient="records") if hasattr(df, "to_dict") else str(df)
        return xtquant_pb2.GetFinancialDataResponse(
            data_json=json.dumps(result, ensure_ascii=False, default=str),
        )

    def SubscribeQuote(self, request, context):
        """Subscribe to single-stock quotes (server stream) -> xtdata.subscribe_quote

        Bridges xtdata's callback model with gRPC streaming via queue.
        Automatically unsubscribes when the client disconnects.
        """
        data_queue: queue.Queue = queue.Queue()

        seq = xtdata.subscribe_quote(
            request.stock_code,
            period=request.period or "1d",
            count=request.count,
            callback=lambda datas: data_queue.put(datas),
        )
        if seq < 0:
            context.abort(grpc.StatusCode.INTERNAL, "Failed to subscribe quote")

        logger.info("Subscribe quote: %s %s (seq=%d)", request.stock_code, request.period, seq)

        while context.is_active():
            # Poll queue every second, also allowing client disconnect detection
            try:
                datas = data_queue.get(timeout=1.0)
            except queue.Empty:
                continue

            for code, items in datas.items():
                item_list = items if isinstance(items, list) else [items]
                bars = [xtquant_pb2.KlineBar(
                    time=int(it.get("time", 0)),
                    open=float(it.get("open", 0)),
                    high=float(it.get("high", 0)),
                    low=float(it.get("low", 0)),
                    close=float(it.get("close", 0)),
                    volume=float(it.get("volume", 0)),
                    amount=float(it.get("amount", 0)),
                ) for it in item_list]
                yield xtquant_pb2.QuoteUpdate(stock_code=code, period=request.period, bars=bars)

        xtdata.unsubscribe_quote(seq)
        logger.info("Unsubscribed: %s (seq=%d)", request.stock_code, seq)

    def SubscribeWholeQuote(self, request, context):
        """Subscribe to full-market tick stream -> xtdata.subscribe_whole_quote

        Pushes tick snapshots for the entire market; suitable for scenarios
        requiring real-time data for a large number of instruments.
        """
        data_queue: queue.Queue = queue.Queue()

        seq = xtdata.subscribe_whole_quote(
            list(request.code_list),
            callback=lambda datas: data_queue.put(datas),
        )
        if seq < 0:
            context.abort(grpc.StatusCode.INTERNAL, "Failed to subscribe whole quote")

        logger.info("Subscribe whole quote: %s (seq=%d)", list(request.code_list), seq)

        while context.is_active():
            try:
                datas = data_queue.get(timeout=1.0)
            except queue.Empty:
                continue

            for code, tick in datas.items():
                # Compatible with both list and dict callback formats
                if isinstance(tick, (list, tuple)):
                    tick = tick[0] if tick else {}
                yield _tick_to_snapshot(code, tick)

        xtdata.unsubscribe_quote(seq)
        logger.info("Unsubscribed whole quote (seq=%d)", seq)
