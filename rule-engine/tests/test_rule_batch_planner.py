from misra_platform_rules.registry import create_default_registry
from misra_platform_rules.rule_batch_planner import batch_summary, generate_batches


def test_batches_cover_all_pending_rules():
    registry = create_default_registry()
    registered = set(registry.list_rule_ids())
    batches = generate_batches(registered)
    pending_ids = {rid for batch in batches for rid in batch.rule_ids}
    assert len(pending_ids) == 158 - len(registered)


def test_ready_now_batches_come_first():
    batches = generate_batches(set())
    tiers = [b.tier for b in batches]
    first_blocked = tiers.index("blocked_on_ast_metadata") if "blocked_on_ast_metadata" in tiers else len(tiers)
    first_process = tiers.index("blocked_on_process") if "blocked_on_process" in tiers else len(tiers)
    assert all(t == "ready_now" for t in tiers[:first_blocked])
    assert all(t in ("ready_now", "blocked_on_ast_metadata") for t in tiers[:first_process])


def test_batch_summary_counts_are_consistent():
    registry = create_default_registry()
    batches = generate_batches(set(registry.list_rule_ids()))
    summary = batch_summary(batches)
    assert summary["total_pending"] == sum(len(b.rule_ids) for b in batches)
    assert summary["batch_count"] == len(batches)
