from misra_platform_rules.rule_result import RuleResult


def score_confidence(result: RuleResult) -> float:
    factors = result.confidence_factors
    weights = {
        "ast_match_specificity": 0.30,
        "type_information_complete": 0.25,
        "macro_clarity": 0.15,
        "historical_false_positive_rate": 0.15,
        "fix_generator_certainty": 0.15,
    }
    total = 0.0
    weight_sum = 0.0
    for key, weight in weights.items():
        if key in factors:
            total += factors[key] * weight
            weight_sum += weight
    if weight_sum == 0:
        return result.confidence_score
    return min(1.0, max(0.0, total / weight_sum))
