"""Generate protobuf Python code

Usage:
    python gen_proto.py

Generated files are placed in the pb/ directory.
"""

import subprocess
import sys
from pathlib import Path


def main():
    pb_dir = Path("pb")
    pb_dir.mkdir(exist_ok=True)

    # Ensure __init__.py exists
    init_file = pb_dir / "__init__.py"
    if not init_file.exists():
        init_file.touch()

    # Run grpc_tools.protoc to generate code
    subprocess.run([
        sys.executable, "-m", "grpc_tools.protoc",
        "-I", "proto",
        "--python_out=pb",
        "--pyi_out=pb",
        "--grpc_python_out=pb",
        "proto/xtquant.proto",
    ], check=True)

    # Fix import paths in grpc file (generated code uses absolute imports;
    # relative imports are needed within the pb package)
    grpc_file = pb_dir / "xtquant_pb2_grpc.py"
    content = grpc_file.read_text(encoding="utf-8")
    content = content.replace(
        "import xtquant_pb2 as xtquant__pb2",
        "from . import xtquant_pb2 as xtquant__pb2",
    )
    grpc_file.write_text(content, encoding="utf-8")

    print("protobuf code generated -> pb/")


if __name__ == "__main__":
    main()
