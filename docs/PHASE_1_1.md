# Phase 1.1 — Real Clang AST Extraction Pipeline

## Architecture Updates

### clang-worker (LibTooling)
- LLVM 18 + Clang LibTooling linked via CMake
- `TranslationUnitLoader` uses `clang::tooling::ClangTool` with `FixedCompilationDatabase`
- `PreprocessorTracker` implements `PPCallbacks` for macros, includes, and conditionals
- `AstSerializer` walks the AST and emits schema v2 nodes with essential type mapping
- Toolchain profiles loaded from JSON (`shared/toolchain_profiles/`)

### backend
- `compile_db_parser.py` ingests CMake/Bear compile_commands with `@rsp` expansion
- `incremental_index.py` computes file hashes and affected TU closure
- `AnalysisOrchestrator` coordinates TU parsing, artifact storage, Redis SSE events
- SQLAlchemy models: `projects`, `analysis_runs`, `translation_units`, `file_index`, `incremental_manifests`
- Local artifact storage under `/app/data/artifacts`

### frontend
- Projects import UI
- Analysis progress with SSE stream
- Translation unit explorer
- AST node browser with macro/include/conditional panels

## API Contracts

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/v1/projects` | Register project |
| GET | `/api/v1/projects` | List projects |
| POST | `/api/v1/projects/{id}/analysis/runs` | Start analysis (202) |
| GET | `/api/v1/analysis/runs/{id}` | Run status |
| GET | `/api/v1/analysis/runs/{id}/translation-units` | TU list |
| GET | `/api/v1/analysis/runs/{id}/translation-units/{tu_id}/ast` | AST artifact |
| GET | `/api/v1/analysis/runs/{id}/stream` | SSE progress |

## AST Schema Example (v2)

```json
{
  "node_id": "node-12",
  "node_kind": "FunctionDecl",
  "parent_id": "node-4",
  "children_ids": ["node-13"],
  "source_range": {
    "file_path": "/workspace/samples/bare-metal-stm32/src/rpm.c",
    "line_start": 5,
    "line_end": 10,
    "column_start": 1,
    "column_end": 2
  },
  "type_information": {
    "spelling": "uint16_t (unsigned short)",
    "canonical_spelling": "unsigned short",
    "typedef_chain": "uint16_t -> unsigned short",
    "is_integer": true,
    "bit_width": 16
  },
  "qualifiers": [],
  "essential_type": "unsigned_short",
  "macro_origin": { "from_macro": false },
  "semantic_properties": { "name": "calculate_rpm" }
}
```

## Supported Toolchains

| Profile ID | Family | Status |
|------------|--------|--------|
| `gcc-host` | GCC | Active |
| `clang-host` | Clang | Active |
| `arm-none-eabi-gcc` | GCC Embedded | Active |
| `iar-arm` | IAR | Future-ready profile |
| `keil-arm` | Keil | Future-ready profile |

## Benchmarks

Run with clang-worker available:

```bash
python tools/benchmark-harness/benchmark_ast_pipeline.py
```

Reference STM32 sample (2 translation units):
- Expected total elapsed: < 2s in dev container
- Expected nodes per TU: 20-80 depending on traversal depth

## User Workflow

1. Open `/projects` and import STM32 sample paths
2. Start analysis from `/projects/{id}/analysis`
3. Watch SSE progress and TU parsing
4. Select a TU and inspect AST nodes, macros, and includes
