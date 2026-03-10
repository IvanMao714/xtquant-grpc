"""xtquant gRPC server entry point

Usage:
    # Market data service only
    python main.py --port 50051

    # Market data + trading service
    python main.py --port 50051 --mini-qmt-path "D:\\path\\to\\userdata_mini"

    # With memory limit (auto-restart when exceeded)
    python main.py --port 50051 --mem-limit-gb 8
"""

import os
import sys
import argparse
import logging
import threading
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


def _get_process_memory_gb():
    """Get current process memory usage (RSS) in GB."""
    try:
        import psutil
        return psutil.Process(os.getpid()).memory_info().rss / (1024 ** 3)
    except ImportError:
        pass
    # Fallback for Windows without psutil
    try:
        import ctypes
        from ctypes import wintypes
        kernel32 = ctypes.windll.kernel32
        class PROCESS_MEMORY_COUNTERS(ctypes.Structure):
            _fields_ = [
                ("cb", wintypes.DWORD),
                ("PageFaultCount", wintypes.DWORD),
                ("PeakWorkingSetSize", ctypes.c_size_t),
                ("WorkingSetSize", ctypes.c_size_t),
                ("QuotaPeakPagedPoolUsage", ctypes.c_size_t),
                ("QuotaPagedPoolUsage", ctypes.c_size_t),
                ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t),
                ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
                ("PagefileUsage", ctypes.c_size_t),
                ("PeakPagefileUsage", ctypes.c_size_t),
            ]
        pmc = PROCESS_MEMORY_COUNTERS()
        pmc.cb = ctypes.sizeof(pmc)
        handle = kernel32.GetCurrentProcess()
        ctypes.windll.psapi.GetProcessMemoryInfo(handle, ctypes.byref(pmc), pmc.cb)
        return pmc.WorkingSetSize / (1024 ** 3)
    except Exception:
        return 0.0


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


def serve(port: int, mini_qmt_path: str, session_id: int, mem_limit_gb: float):
    """Create and start the gRPC server.

    Returns:
        'memory_limit' if shut down due to memory limit, None otherwise.
    """
    wait_for_xtdata()

    MAX_MSG = 1024 * 1024 * 1024  # 1 GB
    server = grpc.server(
        futures.ThreadPoolExecutor(max_workers=10),
        options=[
            ("grpc.max_send_message_length", MAX_MSG),
            ("grpc.max_receive_message_length", MAX_MSG),
        ],
    )

    xtquant_pb2_grpc.add_MarketDataServiceServicer_to_server(MarketDataServicer(), server)
    logger.info("Market data service registered")

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

    if mem_limit_gb > 0:
        logger.info("Memory limit: %.1f GB (auto-restart when exceeded)", mem_limit_gb)
        shutdown_reason = [None]

        def memory_watchdog():
            while shutdown_reason[0] is None:
                time.sleep(10)
                mem_gb = _get_process_memory_gb()
                if mem_gb > 1.0:
                    logger.info("Memory usage: %.2f GB / %.1f GB limit", mem_gb, mem_limit_gb)
                if mem_gb > mem_limit_gb:
                    logger.warning(
                        "Memory usage %.2f GB exceeds limit %.1f GB, initiating graceful restart...",
                        mem_gb, mem_limit_gb,
                    )
                    shutdown_reason[0] = "memory_limit"
                    server.stop(grace=5)
                    return

        watchdog = threading.Thread(target=memory_watchdog, daemon=True)
        watchdog.start()
        server.wait_for_termination()
        return shutdown_reason[0]
    else:
        server.wait_for_termination()
        return None


def main():
    parser = argparse.ArgumentParser(description="xtquant gRPC server")
    parser.add_argument("--port", type=int, default=50051, help="gRPC listen port (default: 50051)")
    parser.add_argument("--mini-qmt-path", type=str, default="",
                        help="MiniQMT userdata_mini path; market-data only if omitted")
    parser.add_argument("--session-id", type=int, default=0,
                        help="Trading session ID (default: current timestamp)")
    parser.add_argument("--mem-limit-gb", type=float, default=8.0,
                        help="Memory limit in GB; server auto-restarts when exceeded (default: 8, 0=disable)")
    args = parser.parse_args()

    restart_count = 0
    while True:
        if restart_count > 0:
            logger.info("=== Server restarting (restart #%d) ===", restart_count)

        try:
            reason = serve(args.port, args.mini_qmt_path, args.session_id, args.mem_limit_gb)
        except KeyboardInterrupt:
            logger.info("Server stopped by user")
            break
        except Exception as e:
            logger.error("Server crashed: %s", e, exc_info=True)
            reason = "crash"

        if reason == "memory_limit":
            restart_count += 1
            logger.info("Restarting in 3 seconds to release memory...")
            time.sleep(3)
            # Re-exec the process to fully release all xtdata cached memory
            logger.info("Re-executing process to release xtdata cache...")
            os.execv(sys.executable, [sys.executable] + sys.argv)
        elif reason == "crash":
            restart_count += 1
            logger.info("Restarting in 5 seconds after crash...")
            time.sleep(5)
            os.execv(sys.executable, [sys.executable] + sys.argv)
        else:
            logger.info("Server stopped normally")
            break


if __name__ == "__main__":
    main()
