"""xtquant gRPC server entry point

Usage:
    # Market data service only
    python main.py --port 50051

    # Market data + trading service
    python main.py --port 50051 --mini-qmt-path "D:\\path\\to\\userdata_mini"
"""

import argparse
import logging
import time
from concurrent import futures

import grpc
from xtquant import xtdata
from pb import xtquant_pb2_grpc
from server import MarketDataServicer, TradingServicer

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
)
logger = logging.getLogger("xtquant-grpc")


def wait_for_xtdata(timeout: int = 300, interval: int = 3):
    """Block until xtdata is connected to MiniQMT.

    Tries calling xtdata.get_trading_dates as a lightweight probe.
    Retries every `interval` seconds, up to `timeout` seconds total.
    """
    logger.info("Waiting for xtdata connection (timeout=%ds) ...", timeout)
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            dates = xtdata.get_trading_dates("SH", count=1)
            if dates:
                logger.info("xtdata connected successfully")
                return
        except Exception:
            pass
        time.sleep(interval)
    raise RuntimeError(f"xtdata failed to connect within {timeout}s — is MiniQMT running?")


def serve(port: int, mini_qmt_path: str, session_id: int):
    """Create and start the gRPC server."""
    # Ensure xtdata is ready before accepting any gRPC requests
    wait_for_xtdata()

    MAX_MSG = 1024 * 1024 * 1024  # 1 GB
    server = grpc.server(
        futures.ThreadPoolExecutor(max_workers=10),
        options=[
            ("grpc.max_send_message_length", MAX_MSG),
            ("grpc.max_receive_message_length", MAX_MSG),
        ],
    )

    # Register market data service (always available)
    xtquant_pb2_grpc.add_MarketDataServiceServicer_to_server(MarketDataServicer(), server)
    logger.info("Market data service registered")

    # Register trading service (requires MiniQMT path)
    if mini_qmt_path:
        sid = session_id or int(time.time())
        trading = TradingServicer(mini_qmt_path, sid)
        xtquant_pb2_grpc.add_TradingServiceServicer_to_server(trading, server)
        logger.info("Trading service registered (session_id=%d)", sid)
    else:
        logger.warning("--mini-qmt-path not specified, trading service disabled")

    server.add_insecure_port(f"[::]:{port}")
    server.start()
    logger.info("gRPC server started, listening on port %d", port)
    server.wait_for_termination()


def main():
    parser = argparse.ArgumentParser(description="xtquant gRPC server")
    parser.add_argument("--port", type=int, default=50051, help="gRPC listen port (default: 50051)")
    parser.add_argument("--mini-qmt-path", type=str, default="",
                        help="MiniQMT userdata_mini path; market-data only if omitted")
    parser.add_argument("--session-id", type=int, default=0,
                        help="Trading session ID (default: current timestamp)")
    args = parser.parse_args()

    serve(args.port, args.mini_qmt_path, args.session_id)


if __name__ == "__main__":
    main()
