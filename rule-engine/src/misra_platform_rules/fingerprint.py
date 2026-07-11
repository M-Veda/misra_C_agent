import hashlib
import json

from misra_platform_rules.rule_result import RuleResult


def build_ast_node_path(ast_node_path: list[str]) -> str:
    return "/".join(ast_node_path)


def build_semantic_context(result: RuleResult) -> dict[str, str | float | list[str]]:
    return {
        "ast_node_id": result.ast_node_id,
        "ast_node_path": result.ast_node_path,
        "offending_expression": result.offending_expression,
        "macro_chain": result.macro_expansion_chain,
    }


def generate_fingerprint(result: RuleResult) -> str:
    payload = {
        "rule_id": result.rule_id,
        "file_path": result.file_path,
        "ast_node_path": result.ast_node_path,
        "offending_expression": result.offending_expression,
        "semantic_context": build_semantic_context(result),
    }
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()
