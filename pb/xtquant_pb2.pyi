from google.protobuf.internal import containers as _containers
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from collections.abc import Iterable as _Iterable, Mapping as _Mapping
from typing import ClassVar as _ClassVar, Optional as _Optional, Union as _Union

DESCRIPTOR: _descriptor.FileDescriptor

class Empty(_message.Message):
    __slots__ = ()
    def __init__(self) -> None: ...

class KlineBar(_message.Message):
    __slots__ = ("stock_code", "time", "open", "high", "low", "close", "volume", "amount", "pre_close", "suspend_flag", "settlement_price", "open_interest")
    STOCK_CODE_FIELD_NUMBER: _ClassVar[int]
    TIME_FIELD_NUMBER: _ClassVar[int]
    OPEN_FIELD_NUMBER: _ClassVar[int]
    HIGH_FIELD_NUMBER: _ClassVar[int]
    LOW_FIELD_NUMBER: _ClassVar[int]
    CLOSE_FIELD_NUMBER: _ClassVar[int]
    VOLUME_FIELD_NUMBER: _ClassVar[int]
    AMOUNT_FIELD_NUMBER: _ClassVar[int]
    PRE_CLOSE_FIELD_NUMBER: _ClassVar[int]
    SUSPEND_FLAG_FIELD_NUMBER: _ClassVar[int]
    SETTLEMENT_PRICE_FIELD_NUMBER: _ClassVar[int]
    OPEN_INTEREST_FIELD_NUMBER: _ClassVar[int]
    stock_code: str
    time: int
    open: float
    high: float
    low: float
    close: float
    volume: float
    amount: float
    pre_close: float
    suspend_flag: int
    settlement_price: float
    open_interest: float
    def __init__(self, stock_code: _Optional[str] = ..., time: _Optional[int] = ..., open: _Optional[float] = ..., high: _Optional[float] = ..., low: _Optional[float] = ..., close: _Optional[float] = ..., volume: _Optional[float] = ..., amount: _Optional[float] = ..., pre_close: _Optional[float] = ..., suspend_flag: _Optional[int] = ..., settlement_price: _Optional[float] = ..., open_interest: _Optional[float] = ...) -> None: ...

class TickSnapshot(_message.Message):
    __slots__ = ("stock_code", "time", "last_price", "open", "high", "low", "last_close", "volume", "amount", "bid_price", "bid_volume", "ask_price", "ask_volume")
    STOCK_CODE_FIELD_NUMBER: _ClassVar[int]
    TIME_FIELD_NUMBER: _ClassVar[int]
    LAST_PRICE_FIELD_NUMBER: _ClassVar[int]
    OPEN_FIELD_NUMBER: _ClassVar[int]
    HIGH_FIELD_NUMBER: _ClassVar[int]
    LOW_FIELD_NUMBER: _ClassVar[int]
    LAST_CLOSE_FIELD_NUMBER: _ClassVar[int]
    VOLUME_FIELD_NUMBER: _ClassVar[int]
    AMOUNT_FIELD_NUMBER: _ClassVar[int]
    BID_PRICE_FIELD_NUMBER: _ClassVar[int]
    BID_VOLUME_FIELD_NUMBER: _ClassVar[int]
    ASK_PRICE_FIELD_NUMBER: _ClassVar[int]
    ASK_VOLUME_FIELD_NUMBER: _ClassVar[int]
    stock_code: str
    time: int
    last_price: float
    open: float
    high: float
    low: float
    last_close: float
    volume: float
    amount: float
    bid_price: _containers.RepeatedScalarFieldContainer[float]
    bid_volume: _containers.RepeatedScalarFieldContainer[float]
    ask_price: _containers.RepeatedScalarFieldContainer[float]
    ask_volume: _containers.RepeatedScalarFieldContainer[float]
    def __init__(self, stock_code: _Optional[str] = ..., time: _Optional[int] = ..., last_price: _Optional[float] = ..., open: _Optional[float] = ..., high: _Optional[float] = ..., low: _Optional[float] = ..., last_close: _Optional[float] = ..., volume: _Optional[float] = ..., amount: _Optional[float] = ..., bid_price: _Optional[_Iterable[float]] = ..., bid_volume: _Optional[_Iterable[float]] = ..., ask_price: _Optional[_Iterable[float]] = ..., ask_volume: _Optional[_Iterable[float]] = ...) -> None: ...

class InstrumentDetail(_message.Message):
    __slots__ = ("exchange_id", "instrument_id", "instrument_name", "product_id", "up_stop_price", "down_stop_price", "pre_close", "open_date", "price_tick", "volume_multiple", "total_volume", "float_volume", "extra_json")
    EXCHANGE_ID_FIELD_NUMBER: _ClassVar[int]
    INSTRUMENT_ID_FIELD_NUMBER: _ClassVar[int]
    INSTRUMENT_NAME_FIELD_NUMBER: _ClassVar[int]
    PRODUCT_ID_FIELD_NUMBER: _ClassVar[int]
    UP_STOP_PRICE_FIELD_NUMBER: _ClassVar[int]
    DOWN_STOP_PRICE_FIELD_NUMBER: _ClassVar[int]
    PRE_CLOSE_FIELD_NUMBER: _ClassVar[int]
    OPEN_DATE_FIELD_NUMBER: _ClassVar[int]
    PRICE_TICK_FIELD_NUMBER: _ClassVar[int]
    VOLUME_MULTIPLE_FIELD_NUMBER: _ClassVar[int]
    TOTAL_VOLUME_FIELD_NUMBER: _ClassVar[int]
    FLOAT_VOLUME_FIELD_NUMBER: _ClassVar[int]
    EXTRA_JSON_FIELD_NUMBER: _ClassVar[int]
    exchange_id: str
    instrument_id: str
    instrument_name: str
    product_id: str
    up_stop_price: float
    down_stop_price: float
    pre_close: float
    open_date: str
    price_tick: float
    volume_multiple: int
    total_volume: int
    float_volume: int
    extra_json: str
    def __init__(self, exchange_id: _Optional[str] = ..., instrument_id: _Optional[str] = ..., instrument_name: _Optional[str] = ..., product_id: _Optional[str] = ..., up_stop_price: _Optional[float] = ..., down_stop_price: _Optional[float] = ..., pre_close: _Optional[float] = ..., open_date: _Optional[str] = ..., price_tick: _Optional[float] = ..., volume_multiple: _Optional[int] = ..., total_volume: _Optional[int] = ..., float_volume: _Optional[int] = ..., extra_json: _Optional[str] = ...) -> None: ...

class GetMarketDataRequest(_message.Message):
    __slots__ = ("stock_codes", "period", "start_time", "end_time", "count", "dividend_type", "fill_data")
    STOCK_CODES_FIELD_NUMBER: _ClassVar[int]
    PERIOD_FIELD_NUMBER: _ClassVar[int]
    START_TIME_FIELD_NUMBER: _ClassVar[int]
    END_TIME_FIELD_NUMBER: _ClassVar[int]
    COUNT_FIELD_NUMBER: _ClassVar[int]
    DIVIDEND_TYPE_FIELD_NUMBER: _ClassVar[int]
    FILL_DATA_FIELD_NUMBER: _ClassVar[int]
    stock_codes: _containers.RepeatedScalarFieldContainer[str]
    period: str
    start_time: str
    end_time: str
    count: int
    dividend_type: str
    fill_data: bool
    def __init__(self, stock_codes: _Optional[_Iterable[str]] = ..., period: _Optional[str] = ..., start_time: _Optional[str] = ..., end_time: _Optional[str] = ..., count: _Optional[int] = ..., dividend_type: _Optional[str] = ..., fill_data: bool = ...) -> None: ...

class GetMarketDataResponse(_message.Message):
    __slots__ = ("stock_code", "time", "open", "high", "low", "close", "volume", "amount", "pre_close", "suspend_flag", "settlement_price", "open_interest")
    STOCK_CODE_FIELD_NUMBER: _ClassVar[int]
    TIME_FIELD_NUMBER: _ClassVar[int]
    OPEN_FIELD_NUMBER: _ClassVar[int]
    HIGH_FIELD_NUMBER: _ClassVar[int]
    LOW_FIELD_NUMBER: _ClassVar[int]
    CLOSE_FIELD_NUMBER: _ClassVar[int]
    VOLUME_FIELD_NUMBER: _ClassVar[int]
    AMOUNT_FIELD_NUMBER: _ClassVar[int]
    PRE_CLOSE_FIELD_NUMBER: _ClassVar[int]
    SUSPEND_FLAG_FIELD_NUMBER: _ClassVar[int]
    SETTLEMENT_PRICE_FIELD_NUMBER: _ClassVar[int]
    OPEN_INTEREST_FIELD_NUMBER: _ClassVar[int]
    stock_code: _containers.RepeatedScalarFieldContainer[str]
    time: _containers.RepeatedScalarFieldContainer[int]
    open: _containers.RepeatedScalarFieldContainer[float]
    high: _containers.RepeatedScalarFieldContainer[float]
    low: _containers.RepeatedScalarFieldContainer[float]
    close: _containers.RepeatedScalarFieldContainer[float]
    volume: _containers.RepeatedScalarFieldContainer[float]
    amount: _containers.RepeatedScalarFieldContainer[float]
    pre_close: _containers.RepeatedScalarFieldContainer[float]
    suspend_flag: _containers.RepeatedScalarFieldContainer[int]
    settlement_price: _containers.RepeatedScalarFieldContainer[float]
    open_interest: _containers.RepeatedScalarFieldContainer[float]
    def __init__(self, stock_code: _Optional[_Iterable[str]] = ..., time: _Optional[_Iterable[int]] = ..., open: _Optional[_Iterable[float]] = ..., high: _Optional[_Iterable[float]] = ..., low: _Optional[_Iterable[float]] = ..., close: _Optional[_Iterable[float]] = ..., volume: _Optional[_Iterable[float]] = ..., amount: _Optional[_Iterable[float]] = ..., pre_close: _Optional[_Iterable[float]] = ..., suspend_flag: _Optional[_Iterable[int]] = ..., settlement_price: _Optional[_Iterable[float]] = ..., open_interest: _Optional[_Iterable[float]] = ...) -> None: ...

class GetFullTickRequest(_message.Message):
    __slots__ = ("stock_codes",)
    STOCK_CODES_FIELD_NUMBER: _ClassVar[int]
    stock_codes: _containers.RepeatedScalarFieldContainer[str]
    def __init__(self, stock_codes: _Optional[_Iterable[str]] = ...) -> None: ...

class GetFullTickResponse(_message.Message):
    __slots__ = ("ticks",)
    class TicksEntry(_message.Message):
        __slots__ = ("key", "value")
        KEY_FIELD_NUMBER: _ClassVar[int]
        VALUE_FIELD_NUMBER: _ClassVar[int]
        key: str
        value: TickSnapshot
        def __init__(self, key: _Optional[str] = ..., value: _Optional[_Union[TickSnapshot, _Mapping]] = ...) -> None: ...
    TICKS_FIELD_NUMBER: _ClassVar[int]
    ticks: _containers.MessageMap[str, TickSnapshot]
    def __init__(self, ticks: _Optional[_Mapping[str, TickSnapshot]] = ...) -> None: ...

class GetInstrumentDetailRequest(_message.Message):
    __slots__ = ("stock_code", "is_complete")
    STOCK_CODE_FIELD_NUMBER: _ClassVar[int]
    IS_COMPLETE_FIELD_NUMBER: _ClassVar[int]
    stock_code: str
    is_complete: bool
    def __init__(self, stock_code: _Optional[str] = ..., is_complete: bool = ...) -> None: ...

class GetStockListRequest(_message.Message):
    __slots__ = ("sector_name",)
    SECTOR_NAME_FIELD_NUMBER: _ClassVar[int]
    sector_name: str
    def __init__(self, sector_name: _Optional[str] = ...) -> None: ...

class StockListResponse(_message.Message):
    __slots__ = ("stock_codes",)
    STOCK_CODES_FIELD_NUMBER: _ClassVar[int]
    stock_codes: _containers.RepeatedScalarFieldContainer[str]
    def __init__(self, stock_codes: _Optional[_Iterable[str]] = ...) -> None: ...

class GetSectorListResponse(_message.Message):
    __slots__ = ("sectors",)
    SECTORS_FIELD_NUMBER: _ClassVar[int]
    sectors: _containers.RepeatedScalarFieldContainer[str]
    def __init__(self, sectors: _Optional[_Iterable[str]] = ...) -> None: ...

class DownloadHistoryDataRequest(_message.Message):
    __slots__ = ("stock_codes", "period", "start_time", "end_time", "incrementally")
    STOCK_CODES_FIELD_NUMBER: _ClassVar[int]
    PERIOD_FIELD_NUMBER: _ClassVar[int]
    START_TIME_FIELD_NUMBER: _ClassVar[int]
    END_TIME_FIELD_NUMBER: _ClassVar[int]
    INCREMENTALLY_FIELD_NUMBER: _ClassVar[int]
    stock_codes: _containers.RepeatedScalarFieldContainer[str]
    period: str
    start_time: str
    end_time: str
    incrementally: bool
    def __init__(self, stock_codes: _Optional[_Iterable[str]] = ..., period: _Optional[str] = ..., start_time: _Optional[str] = ..., end_time: _Optional[str] = ..., incrementally: bool = ...) -> None: ...

class DownloadProgress(_message.Message):
    __slots__ = ("total", "finished", "stock_code", "message")
    TOTAL_FIELD_NUMBER: _ClassVar[int]
    FINISHED_FIELD_NUMBER: _ClassVar[int]
    STOCK_CODE_FIELD_NUMBER: _ClassVar[int]
    MESSAGE_FIELD_NUMBER: _ClassVar[int]
    total: int
    finished: int
    stock_code: str
    message: str
    def __init__(self, total: _Optional[int] = ..., finished: _Optional[int] = ..., stock_code: _Optional[str] = ..., message: _Optional[str] = ...) -> None: ...

class GetTradingDatesRequest(_message.Message):
    __slots__ = ("market", "start_time", "end_time", "count")
    MARKET_FIELD_NUMBER: _ClassVar[int]
    START_TIME_FIELD_NUMBER: _ClassVar[int]
    END_TIME_FIELD_NUMBER: _ClassVar[int]
    COUNT_FIELD_NUMBER: _ClassVar[int]
    market: str
    start_time: str
    end_time: str
    count: int
    def __init__(self, market: _Optional[str] = ..., start_time: _Optional[str] = ..., end_time: _Optional[str] = ..., count: _Optional[int] = ...) -> None: ...

class GetTradingDatesResponse(_message.Message):
    __slots__ = ("dates",)
    DATES_FIELD_NUMBER: _ClassVar[int]
    dates: _containers.RepeatedScalarFieldContainer[int]
    def __init__(self, dates: _Optional[_Iterable[int]] = ...) -> None: ...

class GetFinancialDataRequest(_message.Message):
    __slots__ = ("stock_codes", "table_list", "start_time", "end_time", "report_type")
    STOCK_CODES_FIELD_NUMBER: _ClassVar[int]
    TABLE_LIST_FIELD_NUMBER: _ClassVar[int]
    START_TIME_FIELD_NUMBER: _ClassVar[int]
    END_TIME_FIELD_NUMBER: _ClassVar[int]
    REPORT_TYPE_FIELD_NUMBER: _ClassVar[int]
    stock_codes: _containers.RepeatedScalarFieldContainer[str]
    table_list: _containers.RepeatedScalarFieldContainer[str]
    start_time: str
    end_time: str
    report_type: str
    def __init__(self, stock_codes: _Optional[_Iterable[str]] = ..., table_list: _Optional[_Iterable[str]] = ..., start_time: _Optional[str] = ..., end_time: _Optional[str] = ..., report_type: _Optional[str] = ...) -> None: ...

class GetFinancialDataResponse(_message.Message):
    __slots__ = ("data_json",)
    DATA_JSON_FIELD_NUMBER: _ClassVar[int]
    data_json: str
    def __init__(self, data_json: _Optional[str] = ...) -> None: ...

class DownloadFinancialDataRequest(_message.Message):
    __slots__ = ("stock_codes", "table_list", "start_time", "end_time")
    STOCK_CODES_FIELD_NUMBER: _ClassVar[int]
    TABLE_LIST_FIELD_NUMBER: _ClassVar[int]
    START_TIME_FIELD_NUMBER: _ClassVar[int]
    END_TIME_FIELD_NUMBER: _ClassVar[int]
    stock_codes: _containers.RepeatedScalarFieldContainer[str]
    table_list: _containers.RepeatedScalarFieldContainer[str]
    start_time: str
    end_time: str
    def __init__(self, stock_codes: _Optional[_Iterable[str]] = ..., table_list: _Optional[_Iterable[str]] = ..., start_time: _Optional[str] = ..., end_time: _Optional[str] = ...) -> None: ...

class GetValuationMetricsRequest(_message.Message):
    __slots__ = ("stock_codes",)
    STOCK_CODES_FIELD_NUMBER: _ClassVar[int]
    stock_codes: _containers.RepeatedScalarFieldContainer[str]
    def __init__(self, stock_codes: _Optional[_Iterable[str]] = ...) -> None: ...

class StockValuation(_message.Message):
    __slots__ = ("stock_code", "pe_ttm", "pb", "turnover_rate", "eps", "total_shares", "float_shares", "total_market_cap", "float_market_cap")
    STOCK_CODE_FIELD_NUMBER: _ClassVar[int]
    PE_TTM_FIELD_NUMBER: _ClassVar[int]
    PB_FIELD_NUMBER: _ClassVar[int]
    TURNOVER_RATE_FIELD_NUMBER: _ClassVar[int]
    EPS_FIELD_NUMBER: _ClassVar[int]
    TOTAL_SHARES_FIELD_NUMBER: _ClassVar[int]
    FLOAT_SHARES_FIELD_NUMBER: _ClassVar[int]
    TOTAL_MARKET_CAP_FIELD_NUMBER: _ClassVar[int]
    FLOAT_MARKET_CAP_FIELD_NUMBER: _ClassVar[int]
    stock_code: str
    pe_ttm: float
    pb: float
    turnover_rate: float
    eps: float
    total_shares: int
    float_shares: int
    total_market_cap: float
    float_market_cap: float
    def __init__(self, stock_code: _Optional[str] = ..., pe_ttm: _Optional[float] = ..., pb: _Optional[float] = ..., turnover_rate: _Optional[float] = ..., eps: _Optional[float] = ..., total_shares: _Optional[int] = ..., float_shares: _Optional[int] = ..., total_market_cap: _Optional[float] = ..., float_market_cap: _Optional[float] = ...) -> None: ...

class GetValuationMetricsResponse(_message.Message):
    __slots__ = ("valuations",)
    VALUATIONS_FIELD_NUMBER: _ClassVar[int]
    valuations: _containers.RepeatedCompositeFieldContainer[StockValuation]
    def __init__(self, valuations: _Optional[_Iterable[_Union[StockValuation, _Mapping]]] = ...) -> None: ...

class SubscribeQuoteRequest(_message.Message):
    __slots__ = ("stock_code", "period", "count")
    STOCK_CODE_FIELD_NUMBER: _ClassVar[int]
    PERIOD_FIELD_NUMBER: _ClassVar[int]
    COUNT_FIELD_NUMBER: _ClassVar[int]
    stock_code: str
    period: str
    count: int
    def __init__(self, stock_code: _Optional[str] = ..., period: _Optional[str] = ..., count: _Optional[int] = ...) -> None: ...

class QuoteUpdate(_message.Message):
    __slots__ = ("stock_code", "period", "bars")
    STOCK_CODE_FIELD_NUMBER: _ClassVar[int]
    PERIOD_FIELD_NUMBER: _ClassVar[int]
    BARS_FIELD_NUMBER: _ClassVar[int]
    stock_code: str
    period: str
    bars: _containers.RepeatedCompositeFieldContainer[KlineBar]
    def __init__(self, stock_code: _Optional[str] = ..., period: _Optional[str] = ..., bars: _Optional[_Iterable[_Union[KlineBar, _Mapping]]] = ...) -> None: ...

class SubscribeWholeQuoteRequest(_message.Message):
    __slots__ = ("code_list",)
    CODE_LIST_FIELD_NUMBER: _ClassVar[int]
    code_list: _containers.RepeatedScalarFieldContainer[str]
    def __init__(self, code_list: _Optional[_Iterable[str]] = ...) -> None: ...

class AccountRequest(_message.Message):
    __slots__ = ("account_id", "account_type")
    ACCOUNT_ID_FIELD_NUMBER: _ClassVar[int]
    ACCOUNT_TYPE_FIELD_NUMBER: _ClassVar[int]
    account_id: str
    account_type: str
    def __init__(self, account_id: _Optional[str] = ..., account_type: _Optional[str] = ...) -> None: ...

class AssetInfo(_message.Message):
    __slots__ = ("account_id", "cash", "frozen_cash", "market_value", "total_asset")
    ACCOUNT_ID_FIELD_NUMBER: _ClassVar[int]
    CASH_FIELD_NUMBER: _ClassVar[int]
    FROZEN_CASH_FIELD_NUMBER: _ClassVar[int]
    MARKET_VALUE_FIELD_NUMBER: _ClassVar[int]
    TOTAL_ASSET_FIELD_NUMBER: _ClassVar[int]
    account_id: str
    cash: float
    frozen_cash: float
    market_value: float
    total_asset: float
    def __init__(self, account_id: _Optional[str] = ..., cash: _Optional[float] = ..., frozen_cash: _Optional[float] = ..., market_value: _Optional[float] = ..., total_asset: _Optional[float] = ...) -> None: ...

class OrderInfo(_message.Message):
    __slots__ = ("account_id", "stock_code", "order_id", "order_sysid", "order_time", "order_type", "order_volume", "price", "traded_volume", "traded_price", "order_status", "status_msg", "strategy_name", "order_remark")
    ACCOUNT_ID_FIELD_NUMBER: _ClassVar[int]
    STOCK_CODE_FIELD_NUMBER: _ClassVar[int]
    ORDER_ID_FIELD_NUMBER: _ClassVar[int]
    ORDER_SYSID_FIELD_NUMBER: _ClassVar[int]
    ORDER_TIME_FIELD_NUMBER: _ClassVar[int]
    ORDER_TYPE_FIELD_NUMBER: _ClassVar[int]
    ORDER_VOLUME_FIELD_NUMBER: _ClassVar[int]
    PRICE_FIELD_NUMBER: _ClassVar[int]
    TRADED_VOLUME_FIELD_NUMBER: _ClassVar[int]
    TRADED_PRICE_FIELD_NUMBER: _ClassVar[int]
    ORDER_STATUS_FIELD_NUMBER: _ClassVar[int]
    STATUS_MSG_FIELD_NUMBER: _ClassVar[int]
    STRATEGY_NAME_FIELD_NUMBER: _ClassVar[int]
    ORDER_REMARK_FIELD_NUMBER: _ClassVar[int]
    account_id: str
    stock_code: str
    order_id: int
    order_sysid: str
    order_time: int
    order_type: int
    order_volume: int
    price: float
    traded_volume: int
    traded_price: float
    order_status: int
    status_msg: str
    strategy_name: str
    order_remark: str
    def __init__(self, account_id: _Optional[str] = ..., stock_code: _Optional[str] = ..., order_id: _Optional[int] = ..., order_sysid: _Optional[str] = ..., order_time: _Optional[int] = ..., order_type: _Optional[int] = ..., order_volume: _Optional[int] = ..., price: _Optional[float] = ..., traded_volume: _Optional[int] = ..., traded_price: _Optional[float] = ..., order_status: _Optional[int] = ..., status_msg: _Optional[str] = ..., strategy_name: _Optional[str] = ..., order_remark: _Optional[str] = ...) -> None: ...

class TradeInfo(_message.Message):
    __slots__ = ("account_id", "stock_code", "traded_id", "traded_time", "traded_price", "traded_volume", "traded_amount", "order_id", "order_sysid", "strategy_name", "order_remark")
    ACCOUNT_ID_FIELD_NUMBER: _ClassVar[int]
    STOCK_CODE_FIELD_NUMBER: _ClassVar[int]
    TRADED_ID_FIELD_NUMBER: _ClassVar[int]
    TRADED_TIME_FIELD_NUMBER: _ClassVar[int]
    TRADED_PRICE_FIELD_NUMBER: _ClassVar[int]
    TRADED_VOLUME_FIELD_NUMBER: _ClassVar[int]
    TRADED_AMOUNT_FIELD_NUMBER: _ClassVar[int]
    ORDER_ID_FIELD_NUMBER: _ClassVar[int]
    ORDER_SYSID_FIELD_NUMBER: _ClassVar[int]
    STRATEGY_NAME_FIELD_NUMBER: _ClassVar[int]
    ORDER_REMARK_FIELD_NUMBER: _ClassVar[int]
    account_id: str
    stock_code: str
    traded_id: str
    traded_time: int
    traded_price: float
    traded_volume: int
    traded_amount: float
    order_id: int
    order_sysid: str
    strategy_name: str
    order_remark: str
    def __init__(self, account_id: _Optional[str] = ..., stock_code: _Optional[str] = ..., traded_id: _Optional[str] = ..., traded_time: _Optional[int] = ..., traded_price: _Optional[float] = ..., traded_volume: _Optional[int] = ..., traded_amount: _Optional[float] = ..., order_id: _Optional[int] = ..., order_sysid: _Optional[str] = ..., strategy_name: _Optional[str] = ..., order_remark: _Optional[str] = ...) -> None: ...

class PositionInfo(_message.Message):
    __slots__ = ("account_id", "stock_code", "volume", "can_use_volume", "open_price", "market_value", "frozen_volume", "avg_price")
    ACCOUNT_ID_FIELD_NUMBER: _ClassVar[int]
    STOCK_CODE_FIELD_NUMBER: _ClassVar[int]
    VOLUME_FIELD_NUMBER: _ClassVar[int]
    CAN_USE_VOLUME_FIELD_NUMBER: _ClassVar[int]
    OPEN_PRICE_FIELD_NUMBER: _ClassVar[int]
    MARKET_VALUE_FIELD_NUMBER: _ClassVar[int]
    FROZEN_VOLUME_FIELD_NUMBER: _ClassVar[int]
    AVG_PRICE_FIELD_NUMBER: _ClassVar[int]
    account_id: str
    stock_code: str
    volume: int
    can_use_volume: int
    open_price: float
    market_value: float
    frozen_volume: int
    avg_price: float
    def __init__(self, account_id: _Optional[str] = ..., stock_code: _Optional[str] = ..., volume: _Optional[int] = ..., can_use_volume: _Optional[int] = ..., open_price: _Optional[float] = ..., market_value: _Optional[float] = ..., frozen_volume: _Optional[int] = ..., avg_price: _Optional[float] = ...) -> None: ...

class OrderStockRequest(_message.Message):
    __slots__ = ("account_id", "account_type", "stock_code", "order_type", "volume", "price_type", "price", "strategy_name", "order_remark")
    ACCOUNT_ID_FIELD_NUMBER: _ClassVar[int]
    ACCOUNT_TYPE_FIELD_NUMBER: _ClassVar[int]
    STOCK_CODE_FIELD_NUMBER: _ClassVar[int]
    ORDER_TYPE_FIELD_NUMBER: _ClassVar[int]
    VOLUME_FIELD_NUMBER: _ClassVar[int]
    PRICE_TYPE_FIELD_NUMBER: _ClassVar[int]
    PRICE_FIELD_NUMBER: _ClassVar[int]
    STRATEGY_NAME_FIELD_NUMBER: _ClassVar[int]
    ORDER_REMARK_FIELD_NUMBER: _ClassVar[int]
    account_id: str
    account_type: str
    stock_code: str
    order_type: int
    volume: int
    price_type: int
    price: float
    strategy_name: str
    order_remark: str
    def __init__(self, account_id: _Optional[str] = ..., account_type: _Optional[str] = ..., stock_code: _Optional[str] = ..., order_type: _Optional[int] = ..., volume: _Optional[int] = ..., price_type: _Optional[int] = ..., price: _Optional[float] = ..., strategy_name: _Optional[str] = ..., order_remark: _Optional[str] = ...) -> None: ...

class OrderStockResponse(_message.Message):
    __slots__ = ("order_id", "success", "message")
    ORDER_ID_FIELD_NUMBER: _ClassVar[int]
    SUCCESS_FIELD_NUMBER: _ClassVar[int]
    MESSAGE_FIELD_NUMBER: _ClassVar[int]
    order_id: int
    success: bool
    message: str
    def __init__(self, order_id: _Optional[int] = ..., success: bool = ..., message: _Optional[str] = ...) -> None: ...

class CancelOrderRequest(_message.Message):
    __slots__ = ("account_id", "account_type", "order_id")
    ACCOUNT_ID_FIELD_NUMBER: _ClassVar[int]
    ACCOUNT_TYPE_FIELD_NUMBER: _ClassVar[int]
    ORDER_ID_FIELD_NUMBER: _ClassVar[int]
    account_id: str
    account_type: str
    order_id: int
    def __init__(self, account_id: _Optional[str] = ..., account_type: _Optional[str] = ..., order_id: _Optional[int] = ...) -> None: ...

class CancelOrderResponse(_message.Message):
    __slots__ = ("success", "message")
    SUCCESS_FIELD_NUMBER: _ClassVar[int]
    MESSAGE_FIELD_NUMBER: _ClassVar[int]
    success: bool
    message: str
    def __init__(self, success: bool = ..., message: _Optional[str] = ...) -> None: ...

class QueryOrdersRequest(_message.Message):
    __slots__ = ("account_id", "account_type", "cancelable_only")
    ACCOUNT_ID_FIELD_NUMBER: _ClassVar[int]
    ACCOUNT_TYPE_FIELD_NUMBER: _ClassVar[int]
    CANCELABLE_ONLY_FIELD_NUMBER: _ClassVar[int]
    account_id: str
    account_type: str
    cancelable_only: bool
    def __init__(self, account_id: _Optional[str] = ..., account_type: _Optional[str] = ..., cancelable_only: bool = ...) -> None: ...

class QueryOrdersResponse(_message.Message):
    __slots__ = ("orders",)
    ORDERS_FIELD_NUMBER: _ClassVar[int]
    orders: _containers.RepeatedCompositeFieldContainer[OrderInfo]
    def __init__(self, orders: _Optional[_Iterable[_Union[OrderInfo, _Mapping]]] = ...) -> None: ...

class QueryTradesResponse(_message.Message):
    __slots__ = ("trades",)
    TRADES_FIELD_NUMBER: _ClassVar[int]
    trades: _containers.RepeatedCompositeFieldContainer[TradeInfo]
    def __init__(self, trades: _Optional[_Iterable[_Union[TradeInfo, _Mapping]]] = ...) -> None: ...

class QueryPositionsResponse(_message.Message):
    __slots__ = ("positions",)
    POSITIONS_FIELD_NUMBER: _ClassVar[int]
    positions: _containers.RepeatedCompositeFieldContainer[PositionInfo]
    def __init__(self, positions: _Optional[_Iterable[_Union[PositionInfo, _Mapping]]] = ...) -> None: ...

class TradingEvent(_message.Message):
    __slots__ = ("order_update", "trade_update", "order_error", "cancel_error", "disconnected")
    ORDER_UPDATE_FIELD_NUMBER: _ClassVar[int]
    TRADE_UPDATE_FIELD_NUMBER: _ClassVar[int]
    ORDER_ERROR_FIELD_NUMBER: _ClassVar[int]
    CANCEL_ERROR_FIELD_NUMBER: _ClassVar[int]
    DISCONNECTED_FIELD_NUMBER: _ClassVar[int]
    order_update: OrderInfo
    trade_update: TradeInfo
    order_error: OrderErrorInfo
    cancel_error: CancelErrorInfo
    disconnected: str
    def __init__(self, order_update: _Optional[_Union[OrderInfo, _Mapping]] = ..., trade_update: _Optional[_Union[TradeInfo, _Mapping]] = ..., order_error: _Optional[_Union[OrderErrorInfo, _Mapping]] = ..., cancel_error: _Optional[_Union[CancelErrorInfo, _Mapping]] = ..., disconnected: _Optional[str] = ...) -> None: ...

class OrderErrorInfo(_message.Message):
    __slots__ = ("order_id", "error_id", "error_msg")
    ORDER_ID_FIELD_NUMBER: _ClassVar[int]
    ERROR_ID_FIELD_NUMBER: _ClassVar[int]
    ERROR_MSG_FIELD_NUMBER: _ClassVar[int]
    order_id: int
    error_id: int
    error_msg: str
    def __init__(self, order_id: _Optional[int] = ..., error_id: _Optional[int] = ..., error_msg: _Optional[str] = ...) -> None: ...

class CancelErrorInfo(_message.Message):
    __slots__ = ("order_id", "error_id", "error_msg")
    ORDER_ID_FIELD_NUMBER: _ClassVar[int]
    ERROR_ID_FIELD_NUMBER: _ClassVar[int]
    ERROR_MSG_FIELD_NUMBER: _ClassVar[int]
    order_id: int
    error_id: int
    error_msg: str
    def __init__(self, order_id: _Optional[int] = ..., error_id: _Optional[int] = ..., error_msg: _Optional[str] = ...) -> None: ...
