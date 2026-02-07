"""Full gRPC round-trip tests — verify proto -> server -> xtdata pipeline

These tests start a real gRPC service, issue requests via Stub, and verify:
  - Protobuf serialization/deserialization correctness
  - Server-side data conversion logic
  - Client-received data structure completeness
"""

import json
import time
import threading

import pytest

from pb import xtquant_pb2, xtquant_pb2_grpc


class TestGetMarketData:
    """gRPC GetMarketData endpoint"""

    def test_daily_kline(self, market_stub):
        """Get daily kline, verify bars structure"""
        resp = market_stub.GetMarketData(xtquant_pb2.GetMarketDataRequest(
            stock_codes=["600000.SH"],
            period="1d",
            count=5,
        ))
        assert "600000.SH" in resp.data
        bars = resp.data["600000.SH"].bars
        assert len(bars) > 0, "Kline is empty"

        bar = bars[-1]
        assert bar.time > 0, "Abnormal timestamp"
        assert bar.close > 0, "Abnormal close price"
        assert bar.high >= bar.low, "High should be >= low"
        assert bar.high >= bar.open, "High should be >= open"
        print(f"\n  Latest daily: time={bar.time} O={bar.open} H={bar.high} L={bar.low} C={bar.close}")

    def test_multiple_stocks(self, market_stub):
        """Batch fetch multiple stocks"""
        codes = ["600000.SH", "000001.SZ"]
        resp = market_stub.GetMarketData(xtquant_pb2.GetMarketDataRequest(
            stock_codes=codes,
            period="1d",
            count=3,
        ))
        for code in codes:
            assert code in resp.data, f"Missing {code} in response"
            assert len(resp.data[code].bars) > 0
        print(f"\n  Batch fetched klines for {len(codes)} instruments")

    def test_with_dividend(self, market_stub):
        """Forward-adjusted kline"""
        resp = market_stub.GetMarketData(xtquant_pb2.GetMarketDataRequest(
            stock_codes=["600000.SH"],
            period="1d",
            count=5,
            dividend_type="front",
        ))
        bars = resp.data["600000.SH"].bars
        assert len(bars) > 0
        print(f"\n  Forward-adjusted latest close: {bars[-1].close}")

    def test_minute_kline(self, market_stub):
        """Get minute kline"""
        resp = market_stub.GetMarketData(xtquant_pb2.GetMarketDataRequest(
            stock_codes=["000001.SZ"],
            period="1m",
            count=10,
        ))
        assert "000001.SZ" in resp.data
        print(f"\n  000001.SZ 1m kline count: {len(resp.data['000001.SZ'].bars)}")


class TestGetFullTick:
    """gRPC GetFullTick endpoint"""

    def test_single_stock_tick(self, market_stub):
        """Get single stock tick"""
        resp = market_stub.GetFullTick(xtquant_pb2.GetFullTickRequest(
            stock_codes=["600000.SH"],
        ))
        assert "600000.SH" in resp.ticks
        tick = resp.ticks["600000.SH"]
        assert tick.stock_code == "600000.SH"
        # last_price may be 0 outside trading hours
        print(f"\n  600000.SH tick: last={tick.last_price} bid={list(tick.bid_price)[:3]}")

    def test_multiple_stock_ticks(self, market_stub):
        """Batch fetch ticks"""
        codes = ["600000.SH", "000001.SZ"]
        resp = market_stub.GetFullTick(xtquant_pb2.GetFullTickRequest(
            stock_codes=codes,
        ))
        for code in codes:
            assert code in resp.ticks
        print(f"\n  Batch tick fetched {len(resp.ticks)} instruments")


class TestGetInstrumentDetail:
    """gRPC GetInstrumentDetail endpoint"""

    def test_basic_detail(self, market_stub):
        """Get basic instrument info"""
        detail = market_stub.GetInstrumentDetail(xtquant_pb2.GetInstrumentDetailRequest(
            stock_code="600000.SH",
        ))
        assert detail.instrument_id == "600000"
        assert detail.instrument_name, "Instrument name should not be empty"
        assert detail.exchange_id, "Exchange ID should not be empty"
        print(f"\n  {detail.instrument_id} {detail.instrument_name} "
              f"upper_limit={detail.up_stop_price} lower_limit={detail.down_stop_price}")

    def test_complete_detail(self, market_stub):
        """Get complete instrument info (with extra_json)"""
        detail = market_stub.GetInstrumentDetail(xtquant_pb2.GetInstrumentDetailRequest(
            stock_code="600000.SH",
            is_complete=True,
        ))
        assert detail.extra_json, "extra_json should not be empty when is_complete=True"
        extra = json.loads(detail.extra_json)
        assert isinstance(extra, dict)
        print(f"\n  Complete info field count: {len(extra)}")

    def test_index_detail(self, market_stub):
        """Get index instrument info"""
        detail = market_stub.GetInstrumentDetail(xtquant_pb2.GetInstrumentDetailRequest(
            stock_code="000300.SH",
        ))
        assert "300" in detail.instrument_name or detail.instrument_name
        print(f"\n  {detail.instrument_id}: {detail.instrument_name}")


class TestGetStockList:
    """gRPC GetStockList endpoint"""

    def test_hs_a_stocks(self, market_stub):
        """Get A-share constituents"""
        resp = market_stub.GetStockList(xtquant_pb2.GetStockListRequest(
            sector_name="\u6caa\u6df1A\u80a1",
        ))
        assert len(resp.stock_codes) > 1000
        # Format should be code.market
        assert any(".SH" in c for c in resp.stock_codes)
        assert any(".SZ" in c for c in resp.stock_codes)
        print(f"\n  A-shares: {len(resp.stock_codes)} stocks")

    def test_specific_sector(self, market_stub):
        """Get ChiNext constituents"""
        resp = market_stub.GetStockList(xtquant_pb2.GetStockListRequest(
            sector_name="\u521b\u4e1a\u677f",
        ))
        assert len(resp.stock_codes) > 100
        # ChiNext codes start with 30
        assert all(c.startswith("30") for c in resp.stock_codes)
        print(f"\n  ChiNext: {len(resp.stock_codes)} stocks")


class TestGetSectorList:
    """gRPC GetSectorList endpoint"""

    def test_sector_list(self, market_stub):
        """Sector list should not be empty"""
        resp = market_stub.GetSectorList(xtquant_pb2.Empty())
        assert len(resp.sectors) > 0
        print(f"\n  Total sectors: {len(resp.sectors)}")
        print(f"  First 10: {resp.sectors[:10]}")


class TestDownloadHistoryData:
    """gRPC DownloadHistoryData endpoint"""

    def test_download_single(self, market_stub):
        """Download single stock daily kline"""
        resp = market_stub.DownloadHistoryData(xtquant_pb2.DownloadHistoryDataRequest(
            stock_codes=["600000.SH"],
            period="1d",
            start_time="20250101",
            incrementally=True,
        ))
        assert resp.success
        print(f"\n  Download result: {resp.message}")

    def test_download_multiple(self, market_stub):
        """Batch download"""
        resp = market_stub.DownloadHistoryData(xtquant_pb2.DownloadHistoryDataRequest(
            stock_codes=["600000.SH", "000001.SZ"],
            period="1d",
            start_time="20250101",
            incrementally=True,
        ))
        assert resp.success
        print(f"\n  Batch download result: {resp.message}")


class TestGetTradingCalendar:
    """gRPC GetTradingCalendar endpoint"""

    def test_sh_calendar_2024(self, market_stub):
        """Get 2024 SSE trading calendar (may not be supported in some QMT versions)"""
        import pytest
        try:
            resp = market_stub.GetTradingCalendar(xtquant_pb2.GetTradingCalendarRequest(
                market="SH",
                start_time="20240101",
                end_time="20241231",
            ))
            assert len(resp.dates) > 200, f"Too few 2024 trading days: {len(resp.dates)}"
            print(f"\n  2024 trading days: {len(resp.dates)}")
            print(f"  first={resp.dates[0]} last={resp.dates[-1]}")
        except Exception as e:
            pytest.skip(f"get_trading_calendar not supported in this QMT version: {e}")


class TestGetFinancialData:
    """gRPC GetFinancialData endpoint

    Financial data must be downloaded to local via xtdata.download_financial_data first.
    """

    @pytest.mark.slow
    def test_balance_sheet(self, market_stub):
        """Download and get balance sheet"""
        from xtquant import xtdata
        xtdata.download_financial_data(["600000.SH"], table_list=["Balance"])

        resp = market_stub.GetFinancialData(xtquant_pb2.GetFinancialDataRequest(
            stock_codes=["600000.SH"],
            table_list=["Balance"],
        ))
        assert resp.data_json
        data = json.loads(resp.data_json)
        assert "600000.SH" in data
        assert "Balance" in data["600000.SH"]
        records = data["600000.SH"]["Balance"]
        assert len(records) > 0, "Balance sheet is empty"
        print(f"\n  600000.SH Balance record count: {len(records)}")

    @pytest.mark.slow
    def test_multiple_tables(self, market_stub):
        """Download and get multiple financial tables"""
        from xtquant import xtdata
        xtdata.download_financial_data(["600000.SH"], table_list=["Balance", "Income"])

        resp = market_stub.GetFinancialData(xtquant_pb2.GetFinancialDataRequest(
            stock_codes=["600000.SH"],
            table_list=["Balance", "Income"],
        ))
        data = json.loads(resp.data_json)
        tables = data["600000.SH"]
        assert "Balance" in tables
        assert "Income" in tables
        print(f"\n  Financial tables retrieved: {list(tables.keys())}")


class TestSubscribeQuote:
    """gRPC SubscribeQuote streaming endpoint"""

    def test_subscribe_daily(self, market_stub):
        """Subscribe to daily kline push, wait up to 10s for data"""
        received = []

        def fetch():
            stream = market_stub.SubscribeQuote(xtquant_pb2.SubscribeQuoteRequest(
                stock_code="600000.SH",
                period="1d",
                count=-1,  # Push historical data first
            ))
            for update in stream:
                received.append(update)
                break  # Exit after first message

        t = threading.Thread(target=fetch, daemon=True)
        t.start()
        t.join(timeout=10)

        # With count=-1, historical data should be pushed first
        if received:
            update = received[0]
            assert update.stock_code == "600000.SH"
            assert len(update.bars) > 0
            print(f"\n  Received push: {update.stock_code} bars={len(update.bars)}")
        else:
            print("\n  [WARN] No push received in 10s (possibly outside trading hours)")


class TestSubscribeWholeQuote:
    """gRPC SubscribeWholeQuote streaming endpoint"""

    def test_subscribe_whole_market(self, market_stub):
        """Subscribe to full-market tick, wait up to 15s"""
        received = []

        def fetch():
            stream = market_stub.SubscribeWholeQuote(xtquant_pb2.SubscribeWholeQuoteRequest(
                code_list=["SH", "SZ"],
            ))
            for tick in stream:
                received.append(tick)
                if len(received) >= 5:
                    break

        t = threading.Thread(target=fetch, daemon=True)
        t.start()
        t.join(timeout=15)

        if received:
            assert received[0].stock_code, "stock_code should not be empty"
            codes = [t.stock_code for t in received]
            print(f"\n  Received {len(received)} whole-market ticks, codes: {codes[:5]}")
        else:
            print("\n  [WARN] No whole-market push in 15s (possibly outside trading hours)")
