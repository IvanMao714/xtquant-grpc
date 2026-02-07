"""Shared test fixtures

Starts a real gRPC service (connected to local MiniQMT) for all tests to share.
Make sure the MiniQMT client is running before executing tests.
"""

import threading
import time
from concurrent import futures

import grpc
import pytest
from xtquant import xtdata

from pb import xtquant_pb2_grpc
from server.market_data import MarketDataServicer

# gRPC test server port
TEST_PORT = 50199


@pytest.fixture(scope="session", autouse=True)
def ensure_xtdata_connected():
    """Verify xtdata is connected to MiniQMT — prerequisite for all tests."""
    # get_instrument_detail is the lightest API; use it to verify connectivity
    detail = xtdata.get_instrument_detail("000001.SZ")
    assert detail is not None, (
        "xtdata cannot fetch data; make sure MiniQMT client is running"
    )
    print(f"\n[fixture] xtdata connected, verified: {detail.get('InstrumentName')}")


@pytest.fixture(scope="session")
def grpc_server():
    """Start a real gRPC market-data service, shared across the test session."""
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=4))
    xtquant_pb2_grpc.add_MarketDataServiceServicer_to_server(MarketDataServicer(), server)
    server.add_insecure_port(f"[::]:{TEST_PORT}")
    server.start()
    print(f"\n[fixture] gRPC server started on port {TEST_PORT}")
    yield server
    server.stop(grace=2)
    print("\n[fixture] gRPC server stopped")


@pytest.fixture(scope="session")
def grpc_channel(grpc_server):
    """Create a channel to the test gRPC server."""
    channel = grpc.insecure_channel(f"localhost:{TEST_PORT}")
    yield channel
    channel.close()


@pytest.fixture(scope="session")
def market_stub(grpc_channel):
    """MarketDataService gRPC stub."""
    return xtquant_pb2_grpc.MarketDataServiceStub(grpc_channel)
