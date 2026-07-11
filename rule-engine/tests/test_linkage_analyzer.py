from misra_platform_rules.analyzers.linkage_analyzer import (
    VISIBILITY_EXTERNAL,
    VISIBILITY_INTERNAL,
    VISIBILITY_MIXED,
    LinkageAnalyzer,
)
from misra_platform_rules.analyzers.linkage_index import LinkageIndex
from misra_platform_rules.ast_graph import AstGraph


def node(node_id, kind, parent="", children=None, **kwargs):
    payload = {
        "node_id": node_id,
        "node_kind": kind,
        "parent_id": parent,
        "children_ids": children or [],
        "source_range": kwargs.pop("source_range", {"line_start": 1, "line_end": 1, "column_start": 1}),
        "type_information": kwargs.pop("type_information", {}),
        "semantic_properties": kwargs.pop("semantic_properties", {}),
    }
    payload.update(kwargs)
    return payload


def _build_index(units: list[tuple[str, str, list[dict]]]) -> LinkageIndex:
    graphs = [(tu_id, path, AstGraph(nodes)) for tu_id, path, nodes in units]
    return LinkageIndex(LinkageIndex.build(graphs))


def test_visibility_external_when_all_occurrences_non_static():
    fn = node("a1", "FunctionDecl", semantic_properties={"name": "f", "storage_class": "external"})
    index = _build_index([("tu1", "a.c", [fn])])
    analyzer = LinkageAnalyzer(index)
    assert analyzer.visibility("f") == VISIBILITY_EXTERNAL


def test_visibility_internal_when_all_occurrences_static():
    fn = node("a1", "FunctionDecl", semantic_properties={"name": "f", "storage_class": "static"})
    index = _build_index([("tu1", "a.c", [fn])])
    analyzer = LinkageAnalyzer(index)
    assert analyzer.visibility("f") == VISIBILITY_INTERNAL


def test_visibility_mixed_triggers_linkage_mismatch_violation():
    fn1 = node("a1", "FunctionDecl", semantic_properties={"name": "helper", "storage_class": "static"})
    fn2 = node("b1", "FunctionDecl", semantic_properties={"name": "helper", "storage_class": "external"})
    index = _build_index([("tu1", "a.c", [fn1]), ("tu2", "b.c", [fn2])])
    analyzer = LinkageAnalyzer(index)

    assert analyzer.visibility("helper") == VISIBILITY_MIXED
    violation = analyzer.linkage_mismatch("helper")
    assert violation is not None
    assert "linkage_mismatch" in violation.reason


def test_duplicate_definitions_across_translation_units():
    body_marker = node("a2", "CompoundStmt", parent="a1")
    fn1 = node(
        "a1", "FunctionDecl", children=["a2"],
        semantic_properties={"name": "do_work", "storage_class": "external"},
    )
    body_marker2 = node("b2", "CompoundStmt", parent="b1")
    fn2 = node(
        "b1", "FunctionDecl", children=["b2"],
        semantic_properties={"name": "do_work", "storage_class": "external"},
    )
    index = _build_index([("tu1", "a.c", [fn1, body_marker]), ("tu2", "b.c", [fn2, body_marker2])])
    analyzer = LinkageAnalyzer(index)

    violation = analyzer.duplicate_definitions("do_work")
    assert violation is not None
    assert "duplicate_definition" in violation.reason


def test_incompatible_declarations_detected():
    fn1 = node(
        "a1", "FunctionDecl",
        semantic_properties={"name": "shared_fn", "storage_class": "external"},
        type_information={"spelling": "int (void)"},
    )
    fn2 = node(
        "b1", "FunctionDecl",
        semantic_properties={"name": "shared_fn", "storage_class": "external"},
        type_information={"spelling": "void (void)"},
    )
    index = _build_index([("tu1", "a.c", [fn1]), ("tu2", "b.c", [fn2])])
    analyzer = LinkageAnalyzer(index)

    violation = analyzer.incompatible_declarations("shared_fn")
    assert violation is not None
    assert "incompatible_declaration" in violation.reason


def test_odr_violations_aggregates_all_categories():
    mismatched1 = node("a1", "FunctionDecl", semantic_properties={"name": "mismatched", "storage_class": "static"})
    mismatched2 = node("b1", "FunctionDecl", semantic_properties={"name": "mismatched", "storage_class": "external"})
    clean_fn = node("c1", "FunctionDecl", semantic_properties={"name": "clean", "storage_class": "external"})
    index = _build_index([("tu1", "a.c", [mismatched1, clean_fn]), ("tu2", "b.c", [mismatched2])])
    analyzer = LinkageAnalyzer(index)

    violations = analyzer.odr_violations()
    names_with_violations = {v.name for v in violations}
    assert "mismatched" in names_with_violations
    assert "clean" not in names_with_violations


def test_storage_duration_is_static_for_file_scope_symbols():
    fn = node("a1", "FunctionDecl", semantic_properties={"name": "f", "storage_class": "external"})
    index = _build_index([("tu1", "a.c", [fn])])
    analyzer = LinkageAnalyzer(index)
    assert analyzer.storage_duration("f") == "static"
    assert analyzer.storage_duration("does_not_exist") == "unknown"


def test_undefined_external_reference_reported_informationally():
    decl_only = node("a1", "FunctionDecl", semantic_properties={"name": "external_lib_fn", "storage_class": "external"})
    index = _build_index([("tu1", "a.c", [decl_only])])
    analyzer = LinkageAnalyzer(index)
    assert "external_lib_fn" in analyzer.undefined_external_references()
