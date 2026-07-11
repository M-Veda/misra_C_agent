import json
from pathlib import Path

import pytest

from misra_platform.integrations.clang_bridge.compile_db_parser import load_compile_commands


@pytest.fixture()
def sample_compile_commands(tmp_path: Path) -> Path:
    source_dir = tmp_path / "src"
    source_dir.mkdir()
    source_file = source_dir / "main.c"
    source_file.write_text("int main(void) { return 0; }\n", encoding="utf-8")

    response_file = tmp_path / "args.rsp"
    response_file.write_text("-std=c11 -Iinclude\n", encoding="utf-8")

    payload = [
        {
            "directory": str(tmp_path),
            "command": f"clang @args.rsp -c {source_file.name}",
            "file": str(source_file),
        }
    ]
    compile_commands = tmp_path / "compile_commands.json"
    compile_commands.write_text(json.dumps(payload), encoding="utf-8")
    return compile_commands


def test_load_compile_commands_expands_response_files(sample_compile_commands: Path) -> None:
    validation = load_compile_commands(sample_compile_commands)
    assert validation.is_valid
    assert len(validation.entries) == 1
    assert "-std=c11" in validation.entries[0].arguments
    assert validation.entries[0].absolute_file.endswith("main.c")


def test_duplicate_translation_units_are_removed(tmp_path: Path) -> None:
    source_file = tmp_path / "dup.c"
    source_file.write_text("int value;\n", encoding="utf-8")
    payload = [
        {
            "directory": str(tmp_path),
            "command": "clang -std=c11 -c dup.c",
            "file": "dup.c",
        },
        {
            "directory": str(tmp_path),
            "command": "clang -std=c11 -c dup.c",
            "file": "dup.c",
        },
    ]
    compile_commands = tmp_path / "compile_commands.json"
    compile_commands.write_text(json.dumps(payload), encoding="utf-8")

    validation = load_compile_commands(compile_commands)
    assert validation.is_valid
    assert len(validation.entries) == 1
    assert validation.duplicate_count == 1
