from enum import StrEnum


class RuleCategory(StrEnum):
    MANDATORY = "mandatory"
    REQUIRED = "required"
    ADVISORY = "advisory"


class RuleSeverity(StrEnum):
    CRITICAL = "critical"
    MAJOR = "major"
    MINOR = "minor"
    INFO = "info"


class RuleStandard(StrEnum):
    MISRA_C_2012 = "misra_c_2012"
    MISRA_C_2023 = "misra_c_2023"
