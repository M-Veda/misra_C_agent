"""Generate Python gRPC bindings from shared contracts."""

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PROTO_DIR = ROOT / "shared" / "contracts"
OUTPUT_DIR = ROOT / "backend" / "src" / "misra_platform" / "integrations" / "clang_bridge" / "generated"
PROTO_FILE = PROTO_DIR / "clang_analysis.proto"


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    init_file = OUTPUT_DIR / "__init__.py"
    if not init_file.exists():
        init_file.write_text('"""Generated gRPC/protobuf modules."""\n', encoding="utf-8")

    command = [
        sys.executable,
        "-m",
        "grpc_tools.protoc",
        f"-I{PROTO_DIR}",
        f"--python_out={OUTPUT_DIR}",
        f"--grpc_python_out={OUTPUT_DIR}",
        str(PROTO_FILE),
    ]
    subprocess.run(command, check=True)

    grpc_file = OUTPUT_DIR / "clang_analysis_pb2_grpc.py"
    content = grpc_file.read_text(encoding="utf-8")
    content = content.replace(
        "import clang_analysis_pb2 as clang__analysis__pb2",
        "from misra_platform.integrations.clang_bridge.generated import clang_analysis_pb2 as clang__analysis__pb2",
    )
    grpc_file.write_text(content, encoding="utf-8")
    print(f"Generated gRPC stubs in {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
