from enum import StrEnum


class AnalysisStatus(StrEnum):
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class AnalysisRunType(StrEnum):
    FULL = "full"
    INCREMENTAL = "incremental"


class TranslationUnitStatus(StrEnum):
    PENDING = "pending"
    PARSING = "parsing"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"
