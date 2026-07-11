"""Benchmark AST parsing throughput for a compile_commands.json project."""

import asyncio
import json
import time
from pathlib import Path

from misra_platform.core.config import get_settings
from misra_platform.integrations.clang_bridge.ast_client import ClangAstClient
from misra_platform.integrations.clang_bridge.compile_db_parser import load_compile_commands


async def main() -> None:
    settings = get_settings()
    sample_path = Path("samples/bare-metal-stm32/compile_commands.json")
    validation = load_compile_commands(sample_path)
    if not validation.is_valid:
        raise SystemExit(json.dumps(validation.diagnostics, indent=2))

    client = ClangAstClient(settings)
    durations: list[int] = []
    node_counts: list[int] = []

    started = time.perf_counter()
    for entry in validation.entries:
        result = await client.parse_translation_unit(
            file_path=entry.absolute_file,
            working_directory=entry.directory,
            compile_flags=entry.arguments,
            toolchain_profile_id="clang-host",
        )
        durations.append(result.parse_duration_ms)
        node_counts.append(len(result.nodes))

    await client.close()
    elapsed_ms = int((time.perf_counter() - started) * 1000)

    report = {
        "translation_units": len(validation.entries),
        "total_elapsed_ms": elapsed_ms,
        "avg_parse_duration_ms": round(sum(durations) / len(durations), 2) if durations else 0,
        "total_nodes": sum(node_counts),
        "avg_nodes_per_tu": round(sum(node_counts) / len(node_counts), 2) if node_counts else 0,
    }
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
