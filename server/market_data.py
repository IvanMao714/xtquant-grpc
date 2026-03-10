"""Market data gRPC service — wraps xtquant.xtdata module

Exposes xtdata market-data APIs to remote gRPC clients,
supporting kline queries, tick snapshots, streaming subscriptions, etc.
"""

import gc
import json
import os
import queue
import logging
import threading
import functools
import time

import grpc
import numpy as np
import pandas as pd
from xtquant import xtdata

from pb import xtquant_pb2, xtquant_pb2_grpc

logger = logging.getLogger(__name__)


def _get_mem_gb():
    """Get current process RSS in GB."""
    try:
        import psutil
        return psutil.Process(os.getpid()).memory_info().rss / (1024 ** 3)
    except ImportError:
        pass
    try:
        import ctypes
        from ctypes import wintypes
        class PMC(ctypes.Structure):
            _fields_ = [("cb", wintypes.DWORD), ("PageFaultCount", wintypes.DWORD),
                         ("PeakWorkingSetSize", ctypes.c_size_t), ("WorkingSetSize", ctypes.c_size_t),
                         ("QuotaPeakPagedPoolUsage", ctypes.c_size_t), ("QuotaPagedPoolUsage", ctypes.c_size_t),
                         ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t), ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
                         ("PagefileUsage", ctypes.c_size_t), ("PeakPagefileUsage", ctypes.c_size_t)]
        pmc = PMC()
        pmc.cb = ctypes.sizeof(pmc)
        ctypes.windll.psapi.GetProcessMemoryInfo(ctypes.windll.kernel32.GetCurrentProcess(), ctypes.byref(pmc), pmc.cb)
        return pmc.WorkingSetSize / (1024 ** 3)
    except Exception:
        return 0.0


def _xtdata_retry(max_retries=2, retry_delay=3):
    """Decorator that catches xtdata connection errors and retries.

    On RuntimeError with 'isNetError', attempts reconnection before retry.
    After exhausting retries, aborts the gRPC call with UNAVAILABLE.
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapper(self, request, context, *args, **kwargs):
            last_err = None
            for attempt in range(max_retries + 1):
                try:
                    return func(self, request, context, *args, **kwargs)
                except RuntimeError as e:
                    err_str = str(e)
                    if "isNetError" not in err_str and "forcibly closed" not in err_str:
                        raise
                    last_err = e
                    if attempt < max_retries:
                        logger.warning(
                            "xtdata connection lost (attempt %d/%d), reconnecting in %ds... error: %s",
                            attempt + 1, max_retries, retry_delay, err_str,
                        )
                        try:
                            xtdata.reconnect()
                            time.sleep(retry_delay)
                            logger.info("xtdata reconnected, retrying request...")
                        except Exception as re_err:
                            logger.error("xtdata reconnect failed: %s", re_err)
                            time.sleep(retry_delay)
            logger.error("xtdata connection failed after %d retries: %s", max_retries, last_err)
            context.abort(
                grpc.StatusCode.UNAVAILABLE,
                f"xtdata connection lost: {last_err}",
            )
        return wrapper
    return decorator


# ====================== Data Conversion Helpers ======================


def _append_df_columns(code: str, df: pd.DataFrame, cols: dict):
    """Append one stock's DataFrame rows into the columnar response dict.

    Uses vectorized pandas operations instead of row-by-row iteration.
    """
    n = len(df)
    if n == 0:
        return

    cols["stock_code"].extend([code] * n)
    # Pass raw millisecond timestamps from the 'time' column directly.
    # DO NOT use df.index — it contains UTC dates which are off by 1 day
    # for Chinese stocks.  Let the client convert to local time.
    cols["time"].extend(df["time"].astype(int).tolist())
    cols["open"].extend(df["open"].astype(float).tolist())
    cols["high"].extend(df["high"].astype(float).tolist())
    cols["low"].extend(df["low"].astype(float).tolist())
    cols["close"].extend(df["close"].astype(float).tolist())
    cols["volume"].extend(df["volume"].astype(float).tolist())
    cols["amount"].extend(df["amount"].astype(float).tolist())
    cols["pre_close"].extend(df["preClose"].astype(float).fillna(0).tolist())
    cols["suspend_flag"].extend(df["suspendFlag"].fillna(0).astype(int).tolist())
    cols["settlement_price"].extend(
        df["settelmentPrice"].astype(float).fillna(0).tolist() if "settelmentPrice" in df.columns else [0.0] * n
    )
    cols["open_interest"].extend(
        df["openInterest"].astype(float).fillna(0).tolist() if "openInterest" in df.columns else [0.0] * n
    )


_LOCAL_FIELD_MAP = [
    ("open", "open"),
    ("high", "high"),
    ("low", "low"),
    ("close", "close"),
    ("volume", "volume"),
    ("amount", "amount"),
    ("pre_close", "preClose"),
    ("suspend_flag", "suspendFlag"),
    ("settlement_price", "settelmentPrice"),
    ("open_interest", "openInterest"),
]


def _convert_local_data(data: dict, cols: dict):
    """Convert get_local_data {field: DataFrame(stocks x times)} to columnar format.

    get_local_data returns {field_name: DataFrame} where each DataFrame has
    index=stock_codes and columns=timestamps (int ms).  This avoids MiniQMT's
    in-process cache that causes the 30 GB memory leak.
    """
    ref_df = None
    for v in data.values():
        if isinstance(v, pd.DataFrame) and not v.empty:
            ref_df = v
            break
    if ref_df is None:
        return

    stocks = ref_df.index.tolist()
    times = ref_df.columns.tolist()
    n_times = len(times)
    if n_times == 0:
        return

    int_times = [int(t) for t in times]
    for stock in stocks:
        cols["stock_code"].extend([stock] * n_times)
        cols["time"].extend(int_times)

    total = len(stocks) * n_times
    for proto_field, xt_field in _LOCAL_FIELD_MAP:
        if xt_field in data and isinstance(data[xt_field], pd.DataFrame) and data[xt_field].size > 0:
            flat = np.nan_to_num(
                data[xt_field].reindex(stocks).values.flatten(), nan=0.0
            )
            if proto_field == "suspend_flag":
                cols[proto_field].extend(flat.astype(int).tolist())
            else:
                cols[proto_field].extend(flat.astype(float).tolist())
        else:
            default = 0 if proto_field == "suspend_flag" else 0.0
            cols[proto_field].extend([default] * total)


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

    @_xtdata_retry()
    def GetMarketData(self, request, context):
        """Get kline data -> xtdata.get_local_data (bypasses MiniQMT cache)"""
        count = request.count if request.count != 0 else -1
        stock_list = list(request.stock_codes)
        period = request.period or "1d"
        mem_before = _get_mem_gb()

        data = xtdata.get_local_data(
            [],
            stock_list,
            period=period,
            start_time=request.start_time,
            end_time=request.end_time,
            count=count,
            dividend_type=request.dividend_type or "none",
            fill_data=request.fill_data,
        )

        cols = {k: [] for k in [
            "stock_code", "time", "open", "high", "low", "close",
            "volume", "amount", "pre_close", "suspend_flag",
            "settlement_price", "open_interest",
        ]}
        _convert_local_data(data, cols)
        resp = xtquant_pb2.GetMarketDataResponse(**cols)
        del data, cols
        gc.collect()
        mem_after = _get_mem_gb()
        logger.info(
            "GetMarketData: %d stocks, period=%s, range=[%s,%s] | mem: %.2f -> %.2f GB (delta: %+.2f GB)",
            len(stock_list), period, request.start_time, request.end_time,
            mem_before, mem_after, mem_after - mem_before,
        )
        return resp

    @_xtdata_retry()
    def GetFullTick(self, request, context):
        """Get real-time tick snapshot -> xtdata.get_full_tick"""
        data = xtdata.get_full_tick(list(request.stock_codes))
        ticks = {code: _tick_to_snapshot(code, tick) for code, tick in data.items()}
        return xtquant_pb2.GetFullTickResponse(ticks=ticks)

    @_xtdata_retry()
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

    @_xtdata_retry()
    def GetStockList(self, request, context):
        """Get sector constituents -> xtdata.get_stock_list_in_sector"""
        stocks = xtdata.get_stock_list_in_sector(request.sector_name)
        return xtquant_pb2.StockListResponse(stock_codes=stocks)

    @_xtdata_retry()
    def GetSectorList(self, request, context):
        """Get all sector names -> xtdata.get_sector_list"""
        sectors = xtdata.get_sector_list()
        return xtquant_pb2.GetSectorListResponse(sectors=sectors)

    def DownloadHistoryData(self, request, context):
        """Download historical data (server stream) -> xtdata.download_history_data2

        Runs download in a background thread so we can stream progress via gRPC.
        Uses our own counter instead of xtdata's global 'finished' field.
        """
        codes = list(request.stock_codes)
        period = request.period or "1d"
        total_stocks = len(codes)
        incrementally = True if request.incrementally else None

        logger.info(
            "DownloadHistoryData request: %d stocks, period=%s, range=[%s, %s], incrementally=%s",
            total_stocks, period, request.start_time, request.end_time, incrementally,
        )

        if total_stocks == 0:
            yield xtquant_pb2.DownloadProgress(
                total=0, finished=0, stock_code="", message="No instruments to download",
            )
            return

        progress_queue: queue.Queue = queue.Queue()
        download_done = threading.Event()
        download_error = [None]

        def do_download():
            try:
                kwargs = dict(
                    period=period,
                    start_time=request.start_time,
                    end_time=request.end_time,
                    callback=lambda data: progress_queue.put(data),
                )
                if incrementally is not None:
                    kwargs["incrementally"] = incrementally
                xtdata.download_history_data2(codes, **kwargs)
            except Exception as e:
                logger.error("Download error: %s", e)
                download_error[0] = e
            finally:
                download_done.set()

        threading.Thread(target=do_download, daemon=True).start()

        yield xtquant_pb2.DownloadProgress(
            total=total_stocks, finished=0, stock_code="",
            message=f"Starting download: {total_stocks} instruments",
        )

        finished_count = 0
        wait_ticks = 0
        while not download_done.is_set() or not progress_queue.empty():
            try:
                data = progress_queue.get(timeout=0.5)
            except queue.Empty:
                wait_ticks += 1
                if wait_ticks % 20 == 0:
                    logger.info(
                        "Download in progress... (%.0fs, finished: %d/%d)",
                        wait_ticks * 0.5, finished_count, total_stocks,
                    )
                continue

            wait_ticks = 0
            finished_count += 1
            stock_code = data.get("stockcode", "")
            if finished_count % 100 == 0 or finished_count <= 3 or finished_count == total_stocks:
                logger.info("Download progress: [%d/%d] %s", finished_count, total_stocks, stock_code)
            yield xtquant_pb2.DownloadProgress(
                total=total_stocks,
                finished=finished_count,
                stock_code=stock_code,
                message=data.get("message", ""),
            )

        if download_error[0]:
            msg = f"Download failed: {download_error[0]}"
            logger.error(msg)
            yield xtquant_pb2.DownloadProgress(
                total=total_stocks, finished=finished_count, stock_code="", message=msg,
            )
        elif finished_count == 0 and total_stocks > 0:
            logger.info("Download complete: no new data to download (data already up-to-date)")
            yield xtquant_pb2.DownloadProgress(
                total=total_stocks, finished=total_stocks, stock_code="",
                message="Complete - data already up-to-date",
            )
        else:
            logger.info("Download complete: %d/%d instruments", finished_count, total_stocks)

    @_xtdata_retry()
    def GetTradingDates(self, request, context):
        """Get trading dates -> xtdata.get_trading_dates"""
        count = request.count if request.count != 0 else -1
        dates = xtdata.get_trading_dates(
            request.market or "SH",
            start_time=request.start_time,
            end_time=request.end_time,
            count=count,
        )
        return xtquant_pb2.GetTradingDatesResponse(dates=[int(d) for d in dates])

    @_xtdata_retry()
    def GetFinancialData(self, request, context):
        """Get financial data (JSON response) -> xtdata.get_financial_data

        Financial data has complex schemas (balance sheet / income / cash flow, etc.),
        serialized as JSON for flexibility.

        Available tables: Balance, Income, CashFlow, Capital, Holdernum,
        Top10holder, Top10flowholder, Pershareindex.
        """
        data = xtdata.get_financial_data(
            list(request.stock_codes),
            table_list=list(request.table_list) or [],
            start_time=request.start_time,
            end_time=request.end_time,
            report_type=request.report_type or "report_time",
        )
        result = {}
        for code, tables in data.items():
            result[code] = {}
            for name, df in tables.items():
                result[code][name] = df.to_dict(orient="records") if hasattr(df, "to_dict") else str(df)
        return xtquant_pb2.GetFinancialDataResponse(
            data_json=json.dumps(result, ensure_ascii=False, default=str),
        )

    def DownloadFinancialData(self, request, context):
        """Download financial data (server stream) -> xtdata.download_financial_data2

        Same pattern as DownloadHistoryData: background thread + queue.
        """
        codes = list(request.stock_codes)
        tables = list(request.table_list) or []
        total_stocks = len(codes)

        logger.info(
            "DownloadFinancialData request: %d stocks, tables=%s, range=[%s, %s]",
            total_stocks, tables, request.start_time, request.end_time,
        )

        if total_stocks == 0:
            yield xtquant_pb2.DownloadProgress(
                total=0, finished=0, stock_code="", message="No stocks to download",
            )
            return

        progress_queue: queue.Queue = queue.Queue()
        download_done = threading.Event()
        download_error = [None]

        def do_download():
            try:
                xtdata.download_financial_data2(
                    codes,
                    table_list=tables,
                    start_time=request.start_time,
                    end_time=request.end_time,
                    callback=lambda data: progress_queue.put(data),
                )
            except Exception as e:
                logger.error("Financial download error: %s", e)
                download_error[0] = e
            finally:
                download_done.set()

        threading.Thread(target=do_download, daemon=True).start()

        yield xtquant_pb2.DownloadProgress(
            total=total_stocks, finished=0, stock_code="",
            message=f"Starting financial download: {total_stocks} stocks, tables={tables}",
        )

        finished_count = 0
        wait_ticks = 0
        while not download_done.is_set() or not progress_queue.empty():
            try:
                data = progress_queue.get(timeout=0.5)
            except queue.Empty:
                wait_ticks += 1
                if wait_ticks % 20 == 0:
                    logger.info(
                        "Financial download in progress... (%.0fs, finished: %d/%d)",
                        wait_ticks * 0.5, finished_count, total_stocks,
                    )
                continue

            wait_ticks = 0
            finished_count += 1
            stock_code = data.get("stockcode", "")
            if finished_count % 100 == 0 or finished_count <= 3 or finished_count == total_stocks:
                logger.info("Financial progress: [%d/%d] %s", finished_count, total_stocks, stock_code)
            yield xtquant_pb2.DownloadProgress(
                total=total_stocks,
                finished=finished_count,
                stock_code=stock_code,
                message=data.get("message", ""),
            )

        if download_error[0]:
            msg = f"Financial download failed: {download_error[0]}"
            logger.error(msg)
            yield xtquant_pb2.DownloadProgress(
                total=total_stocks, finished=finished_count, stock_code="", message=msg,
            )
        elif finished_count == 0 and total_stocks > 0:
            logger.info("Financial download complete: data already up-to-date")
            yield xtquant_pb2.DownloadProgress(
                total=total_stocks, finished=total_stocks, stock_code="",
                message="Complete - data already up-to-date",
            )
        else:
            logger.info("Financial download complete: %d/%d stocks", finished_count, total_stocks)

    @_xtdata_retry()
    def GetValuationMetrics(self, request, context):
        """Get valuation metrics for a list of stocks.

        Combines data from multiple sources:
        - Pershareindex table: EPS (s_fa_eps_basic), BPS (s_fa_bps), ROE (net_roe), etc.
        - Capital table: total_capital, circulating_capital, freeFloatCapital
        - get_full_tick: latest price for PE, PB, market cap, turnover rate computation

        PE and PB are NOT stored in xtdata financial tables — they are computed
        from latest price / EPS and latest price / BPS respectively.
        """
        codes = list(request.stock_codes)
        if not codes:
            return xtquant_pb2.GetValuationMetricsResponse(valuations=[])

        # Fetch Pershareindex + Capital tables for latest metrics
        fin_data = xtdata.get_financial_data(codes, table_list=["Pershareindex", "Capital"])

        # Fetch latest tick for price-based calculations
        tick_data = xtdata.get_full_tick(codes)

        valuations = []
        for code in codes:
            v = xtquant_pb2.StockValuation(stock_code=code)
            price = 0.0

            # Latest price from tick data
            if code in tick_data:
                price = float(tick_data[code].get("lastPrice", 0) or 0)

            # Extract per-share index (latest record)
            eps = 0.0
            bps = 0.0
            if code in fin_data:
                psi = fin_data[code].get("Pershareindex")
                if psi is not None and hasattr(psi, "iloc") and len(psi) > 0:
                    row = psi.iloc[-1]
                    eps = float(row.get("s_fa_eps_basic", 0) or 0)
                    bps = float(row.get("s_fa_bps", 0) or 0)
                    v.eps = eps

                # Capital table: share counts
                cap = fin_data[code].get("Capital")
                if cap is not None and hasattr(cap, "iloc") and len(cap) > 0:
                    row = cap.iloc[-1]
                    v.total_shares = int(row.get("total_capital", 0) or 0)
                    v.float_shares = int(row.get("circulating_capital", 0) or 0)

            # Compute PE = price / EPS (avoid division by zero)
            if price > 0 and eps != 0:
                v.pe_ttm = price / eps

            # Compute PB = price / BPS
            if price > 0 and bps > 0:
                v.pb = price / bps

            # Market cap = price * shares
            if price > 0:
                if v.total_shares > 0:
                    v.total_market_cap = price * v.total_shares
                if v.float_shares > 0:
                    v.float_market_cap = price * v.float_shares

            # Turnover rate = volume / float_shares * 100 (%)
            if code in tick_data:
                volume = float(tick_data[code].get("volume", 0) or 0)
                if v.float_shares > 0 and volume > 0:
                    v.turnover_rate = volume / v.float_shares * 100

            valuations.append(v)

        return xtquant_pb2.GetValuationMetricsResponse(valuations=valuations)

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
                    stock_code=code,
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
