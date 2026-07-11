import pytest

from misra_platform_rules.fingerprint import generate_fingerprint
from misra_platform_rules.registry import create_default_registry
from misra_platform_rules.rule_context import RuleContext
from misra_platform_rules.engine import RuleExecutionEngine


@pytest.fixture
def sample_artifact() -> dict:
    return {
        "file_path": "/project/src/demo.c",
        "nodes": [
            {
                "node_id": "n1",
                "node_kind": "FunctionDecl",
                "parent_id": "",
                "children_ids": ["n2"],
                "source_range": {
                    "file_path": "/project/src/demo.c",
                    "line_start": 10,
                    "line_end": 20,
                    "column_start": 1,
                    "column_end": 2,
                },
                "type_information": {"spelling": "void (void)"},
                "qualifiers": [],
                "essential_type": "unknown",
                "macro_origin": {"from_macro": False},
                "semantic_properties": {"name": "demo_fn"},
            },
            {
                "node_id": "n2",
                "node_kind": "CompoundStmt",
                "parent_id": "n1",
                "children_ids": ["n3", "n4"],
                "source_range": {
                    "file_path": "/project/src/demo.c",
                    "line_start": 11,
                    "line_end": 19,
                    "column_start": 1,
                    "column_end": 2,
                },
                "type_information": {},
                "qualifiers": [],
                "essential_type": "unknown",
                "macro_origin": {"from_macro": False},
                "semantic_properties": {},
            },
            {
                "node_id": "n3",
                "node_kind": "ReturnStmt",
                "parent_id": "n2",
                "children_ids": [],
                "source_range": {
                    "file_path": "/project/src/demo.c",
                    "line_start": 12,
                    "line_end": 12,
                    "column_start": 5,
                    "column_end": 15,
                },
                "type_information": {},
                "qualifiers": [],
                "essential_type": "unknown",
                "macro_origin": {"from_macro": False},
                "semantic_properties": {},
            },
            {
                "node_id": "n4",
                "node_kind": "ReturnStmt",
                "parent_id": "n2",
                "children_ids": [],
                "source_range": {
                    "file_path": "/project/src/demo.c",
                    "line_start": 99,
                    "line_end": 99,
                    "column_start": 5,
                    "column_end": 15,
                },
                "type_information": {},
                "qualifiers": [],
                "essential_type": "unknown",
                "macro_origin": {"from_macro": False},
                "semantic_properties": {},
            },
            {
                "node_id": "n5",
                "node_kind": "BinaryOperator",
                "parent_id": "",
                "children_ids": ["n6", "n7"],
                "source_range": {
                    "file_path": "/project/src/demo.c",
                    "line_start": 30,
                    "line_end": 30,
                    "column_start": 1,
                    "column_end": 20,
                },
                "type_information": {},
                "qualifiers": [],
                "essential_type": "unsigned_int",
                "macro_origin": {"from_macro": False},
                "semantic_properties": {"opcode": "="},
            },
            {
                "node_id": "n6",
                "node_kind": "DeclRefExpr",
                "parent_id": "n5",
                "children_ids": [],
                "source_range": {
                    "file_path": "/project/src/demo.c",
                    "line_start": 30,
                    "line_end": 30,
                    "column_start": 1,
                    "column_end": 5,
                },
                "type_information": {},
                "qualifiers": [],
                "essential_type": "unsigned_char",
                "macro_origin": {"from_macro": False},
                "semantic_properties": {"name": "narrow"},
            },
            {
                "node_id": "n7",
                "node_kind": "IntegerLiteral",
                "parent_id": "n5",
                "children_ids": [],
                "source_range": {
                    "file_path": "/project/src/demo.c",
                    "line_start": 30,
                    "line_end": 30,
                    "column_start": 9,
                    "column_end": 16,
                },
                "type_information": {},
                "qualifiers": [],
                "essential_type": "unsigned_int",
                "macro_origin": {"from_macro": False},
                "semantic_properties": {},
            },
        ],
        "diagnostics": [],
        "preprocessor": {},
    }


def test_registry_discovers_pilot_rules() -> None:
    registry = create_default_registry()
    rule_ids = registry.list_rule_ids()
    assert len(rule_ids) >= 36
    assert "misra-c2012-rule-15-5" in rule_ids


def test_fingerprint_stable_across_line_shift(sample_artifact: dict) -> None:
    context = RuleContext.from_ast_artifact(artifact=sample_artifact, translation_unit_id="tu-1")
    registry = create_default_registry()
    rule = registry.get("misra-c2012-rule-15-5")
    violations = rule.detect(context)
    assert len(violations) == 1
    original = generate_fingerprint(violations[0])

    shifted = sample_artifact.copy()
    shifted_nodes = []
    for node in sample_artifact["nodes"]:
        updated = dict(node)
        source_range = dict(node["source_range"])
        source_range["line_start"] = source_range["line_start"] + 50
        source_range["line_end"] = source_range["line_end"] + 50
        updated["source_range"] = source_range
        shifted_nodes.append(updated)
    shifted["nodes"] = shifted_nodes

    shifted_context = RuleContext.from_ast_artifact(artifact=shifted, translation_unit_id="tu-1")
    shifted_violations = rule.detect(shifted_context)
    assert generate_fingerprint(shifted_violations[0]) == original


def test_rule_execution_engine_isolates_failures(sample_artifact: dict) -> None:
    registry = create_default_registry()
    context = RuleContext.from_ast_artifact(artifact=sample_artifact, translation_unit_id="tu-1")
    engine = RuleExecutionEngine(max_workers=2)
    report = engine.execute(context, registry.select_rules())
    assert report.metrics
    assert any(metric.rule_id == "misra-c2012-rule-15-5" for metric in report.metrics)


def test_rule_10_3_detects_narrowing_assignment(sample_artifact: dict) -> None:
    registry = create_default_registry()
    context = RuleContext.from_ast_artifact(artifact=sample_artifact, translation_unit_id="tu-1")
    rule = registry.get("misra-c2012-rule-10-3")
    violations = rule.detect(context)
    assert len(violations) == 1
    assert "unsigned_char" in violations[0].explanation
