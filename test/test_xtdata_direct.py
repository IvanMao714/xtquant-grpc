"""Direct xtdata layer tests — verify MiniQMT data communication

These tests bypass gRPC and call xtdata APIs directly, useful for diagnosing:
  - Whether MiniQMT connectivity is working
  - Whether xtdata return structures match expectations
"""

import json
import time

import pandas as pd
import pytest
from xtquant import xtdata


class TestXtdataKline:
    """Kline data retrieval"""

    def test_get_daily_kline(self):
        """Get 600000.SH daily kline, should have OHLCV fields"""
        data = xtdata.get_market_data_ex(
            [], ["600000.SH"], period="1d", count=10
        )
        assert "600000.SH" in data
        df = data["600000.SH"]
        assert isinstance(df, pd.DataFrame)
        assert len(df) > 0, "Daily kline should not be empty"

        # Verify standard columns exist
        for col in ["open", "high", "low", "close", "volume"]:
            assert col in df.columns, f"Missing column: {col}"

        # Price should be positive
        last = df.iloc[-1]
        assert last["close"] > 0, f"Abnormal close price: {last['close']}"
        print(f"\n  600000.SH latest daily: close={last['close']}, volume={last['volume']}")

    def test_get_minute_kline(self):
        """Get 1-minute kline"""
        data = xtdata.get_market_data_ex(
            [], ["000001.SZ"], period="1m", count=5
        )
        assert "000001.SZ" in data
        df = data["000001.SZ"]
        assert len(df) >= 0  # May be empty outside trading hours
        print(f"\n  000001.SZ 1m kline count: {len(df)}")

    def test_get_multiple_stocks(self):
        """Get klines for multiple stocks at once"""
        codes = ["600000.SH", "000001.SZ", "000300.SH"]
        data = xtdata.get_market_data_ex([], codes, period="1d", count=3)
        for code in codes:
            assert code in data, f"Missing data for {code}"
        print(f"\n  Batch fetched {len(codes)} instruments")


class TestXtdataTick:
    """Tick snapshot retrieval"""

    def test_get_full_tick(self):
        """Get full tick data"""
        data = xtdata.get_full_tick(["600000.SH"])
        assert "600000.SH" in data
        tick = data["600000.SH"]
        assert isinstance(tick, dict)
        # lastPrice may be 0 outside trading hours
        assert "lastPrice" in tick
        print(f"\n  600000.SH tick: lastPrice={tick['lastPrice']}")

    def test_tick_has_bid_ask(self):
        """Tick data should contain bid/ask"""
        data = xtdata.get_full_tick(["000001.SZ"])
        tick = data["000001.SZ"]
        assert "bidPrice" in tick, "Missing bidPrice"
        assert "askPrice" in tick, "Missing askPrice"
        assert isinstance(tick["bidPrice"], (list, tuple))
        print(f"\n  000001.SZ bid={tick['bidPrice'][:3]}... ask={tick['askPrice'][:3]}...")


class TestXtdataInstrument:
    """Instrument information"""

    def test_get_instrument_detail(self):
        """Get basic instrument info"""
        detail = xtdata.get_instrument_detail("600000.SH")
        assert detail is not None
        assert detail["InstrumentName"], "Instrument name should not be empty"
        assert detail["InstrumentID"] == "600000"
        print(f"\n  {detail['InstrumentID']}: {detail['InstrumentName']}")

    def test_get_instrument_detail_complete(self):
        """Get complete instrument info"""
        detail = xtdata.get_instrument_detail("600000.SH", True)
        assert detail is not None
        # Complete mode should have more fields
        assert "ExchangeID" in detail
        print(f"\n  Total fields: {len(detail)}")

    def test_nonexistent_instrument(self):
        """Nonexistent instrument should return None"""
        detail = xtdata.get_instrument_detail("FAKE99.XX")
        assert detail is None or detail == {}


class TestXtdataSector:
    """Sector information"""

    def test_get_sector_list(self):
        """Sector list should not be empty"""
        sectors = xtdata.get_sector_list()
        assert len(sectors) > 0, "Sector list is empty"
        print(f"\n  Sector count: {len(sectors)}, first 5: {sectors[:5]}")

    def test_get_stock_list_in_sector(self):
        """Get A-share constituents"""
        stocks = xtdata.get_stock_list_in_sector("\u6caa\u6df1A\u80a1")
        assert len(stocks) > 1000, f"Abnormal A-share count: {len(stocks)}"
        # Verify code format
        assert any(s.endswith(".SH") for s in stocks)
        assert any(s.endswith(".SZ") for s in stocks)
        print(f"\n  A-share count: {len(stocks)}")


class TestXtdataCalendar:
    """Trading calendar"""

    def test_get_trading_dates(self):
        """Get SSE trading dates (returns millisecond timestamps)"""
        dates = xtdata.get_trading_dates("SH", start_time="20240101", end_time="20241231")
        assert len(dates) > 200, f"Abnormal 2024 trading day count: {len(dates)}"
        # Values are millisecond timestamps; 2024-01-01 ~ 1704067200000
        assert dates[0] > 1704000000000, f"Abnormal first date ts: {dates[0]}"
        assert dates[-1] < 1735700000000, f"Abnormal last date ts: {dates[-1]}"
        print(f"\n  2024 trading days: {len(dates)}, first_ts={dates[0]}, last_ts={dates[-1]}")

    def test_get_trading_calendar(self):
        """Get trading calendar (may not be supported in some QMT versions)"""
        import pytest
        try:
            dates = xtdata.get_trading_calendar("SH", start_time="20240101", end_time="20241231")
            assert len(dates) > 200
            print(f"\n  2024 trading days: {len(dates)}")
        except RuntimeError as e:
            pytest.skip(f"get_trading_calendar not supported in this QMT version: {e}")


class TestXtdataDownload:
    """Data download"""

    def test_download_history_data(self):
        """Download single stock history (incremental)"""
        xtdata.download_history_data(
            "600000.SH", period="1d", start_time="20250101", incrementally=True
        )
        # Should be able to fetch data after download
        data = xtdata.get_market_data_ex(
            [], ["600000.SH"], period="1d", start_time="20250101"
        )
        assert "600000.SH" in data
        assert len(data["600000.SH"]) > 0, "No data after download"
        print(f"\n  600000.SH 2025 daily kline count after download: {len(data['600000.SH'])}")


class TestXtdataFinancial:
    """Financial data

    Financial data must be downloaded first; initial download may take a while.
    Run with pytest -m slow, or skip with pytest -m "not slow".
    """

    @pytest.mark.slow
    def test_get_financial_data(self):
        """Download and get balance sheet data"""
        xtdata.download_financial_data(["600000.SH"], table_list=["Balance"])

        data = xtdata.get_financial_data(
            ["600000.SH"], table_list=["Balance"]
        )
        assert "600000.SH" in data
        tables = data["600000.SH"]
        assert "Balance" in tables, f"Missing Balance table, available: {list(tables.keys())}"
        df = tables["Balance"]
        assert len(df) > 0, "Balance sheet is empty"
        print(f"\n  600000.SH Balance record count: {len(df)}")
